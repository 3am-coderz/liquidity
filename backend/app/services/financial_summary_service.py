import json
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Account, BankTransaction, Company, FinancialSummary, PendingPaymentEvent, User
from ..schemas import FinancialSummaryResponse, ManualTransactionCreateRequest, ManualTransactionResponse


router = APIRouter(tags=["financial-summary"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def calculate_financial_summary(
    current_balance: float,
    transactions: list[BankTransaction],
    minimum_cash_floor: float,
) -> dict[str, float]:
    cutoff = _utc_now() - timedelta(days=30)
    monthly_income = round(
        sum(item.amount for item in transactions if item.transaction_type == "CREDIT" and item.posted_at >= cutoff),
        2,
    )
    monthly_expense = round(
        sum(abs(item.amount) for item in transactions if item.transaction_type == "DEBIT" and item.posted_at >= cutoff),
        2,
    )
    emi_payments = round(
        sum(
            abs(item.amount)
            for item in transactions
            if item.transaction_type == "DEBIT"
            and item.posted_at >= cutoff
            and any(keyword in (item.description or "").lower() for keyword in ["emi", "loan", "installment"])
        ),
        2,
    )
    burn_rate = round(monthly_expense - monthly_income, 2)
    daily_expense = round(monthly_expense / 30, 2) if monthly_expense > 0 else 0.0
    runway_days = round(current_balance / daily_expense, 1) if daily_expense > 0 else 999.0
    cash_reserve_ratio = round(current_balance / minimum_cash_floor, 2) if minimum_cash_floor > 0 else 999.0
    return {
        "current_balance": round(current_balance, 2),
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "burn_rate": burn_rate,
        "daily_expense": daily_expense,
        "runway_days": runway_days,
        "cash_reserve_ratio": cash_reserve_ratio,
        "emi_payments": emi_payments,
    }


def get_pending_payment_total(db: Session, user_id: int) -> float:
    pending_events = (
        db.query(PendingPaymentEvent)
        .filter(PendingPaymentEvent.user_id == user_id, PendingPaymentEvent.status == "PENDING")
        .all()
    )
    return round(sum(item.amount for item in pending_events), 2)


def get_reconciled_balance(db: Session, user_id: int, bank_balance: float) -> float:
    return round(max(bank_balance - get_pending_payment_total(db, user_id), 0.0), 2)


def reconcile_pending_payments(db: Session, user_id: int) -> None:
    pending_events = (
        db.query(PendingPaymentEvent)
        .filter(PendingPaymentEvent.user_id == user_id, PendingPaymentEvent.status == "PENDING")
        .order_by(PendingPaymentEvent.created_at.asc())
        .all()
    )
    if not pending_events:
        return

    debit_transactions = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.user_id == user_id,
            BankTransaction.transaction_type == "DEBIT",
            BankTransaction.matched_pending_payment_id.is_(None),
        )
        .order_by(BankTransaction.posted_at.asc())
        .all()
    )

    for event in pending_events:
        for transaction in debit_transactions:
            if transaction.matched_pending_payment_id is not None:
                continue
            if abs(transaction.amount - event.amount) > 0.01:
                continue
            description = (transaction.description or "").lower()
            vendor_name = event.vendor_name.lower()
            if vendor_name and vendor_name not in description and description:
                continue
            if transaction.posted_at < event.created_at - timedelta(days=2):
                continue
            event.status = "SETTLED"
            event.matched_transaction_id = transaction.transaction_id
            event.settled_at = _utc_now()
            transaction.matched_pending_payment_id = event.id
            db.add_all([event, transaction])
            break

    db.commit()


def sync_financial_summary_to_company(db: Session, user_id: int, summary: FinancialSummary) -> None:
    company = db.query(Company).filter(Company.user_id == user_id).first()
    account = db.query(Account).filter(Account.user_id == user_id).first()
    reconciled_balance = get_reconciled_balance(db, user_id, summary.current_balance)
    if company:
        company.cash_balance = reconciled_balance
        company.monthly_income = summary.monthly_income
        company.monthly_expenses = summary.monthly_expense
        company.cash_flow = round(summary.monthly_income - summary.monthly_expense, 2)
        db.add(company)
    if account:
        account.current_balance = reconciled_balance
        db.add(account)
    db.commit()


def upsert_financial_summary(
    db: Session,
    user_id: int,
    current_balance: float,
    transactions: list[BankTransaction],
    minimum_cash_floor: float,
    source: str,
    session_id: str | None = None,
) -> FinancialSummary:
    metrics = calculate_financial_summary(current_balance, transactions, minimum_cash_floor)
    summary = db.query(FinancialSummary).filter(FinancialSummary.user_id == user_id).first()
    if not summary:
        summary = FinancialSummary(user_id=user_id)
    summary.current_balance = metrics["current_balance"]
    summary.monthly_income = metrics["monthly_income"]
    summary.monthly_expense = metrics["monthly_expense"]
    summary.burn_rate = metrics["burn_rate"]
    summary.daily_expense = metrics["daily_expense"]
    summary.runway_days = metrics["runway_days"]
    summary.cash_reserve_ratio = metrics["cash_reserve_ratio"]
    summary.emi_payments = metrics["emi_payments"]
    summary.source = source
    summary.last_session_id = session_id
    summary.updated_at = _utc_now()
    db.add(summary)
    db.commit()
    db.refresh(summary)
    reconcile_pending_payments(db, user_id)
    sync_financial_summary_to_company(db, user_id, summary)
    return summary


def create_manual_transaction(
    db: Session,
    user_id: int,
    payload: ManualTransactionCreateRequest,
    minimum_cash_floor: float,
) -> tuple[BankTransaction, FinancialSummary]:
    summary = bootstrap_financial_summary_from_legacy(db, user_id, minimum_cash_floor)
    transaction_type = "CREDIT" if payload.direction == "money_in" else "DEBIT"
    delta = payload.amount if payload.direction == "money_in" else -payload.amount
    new_bank_balance = round(summary.current_balance + delta, 2)
    posted_at = datetime.combine(payload.transaction_date, time(hour=12))
    transaction = BankTransaction(
        user_id=user_id,
        session_id=None,
        transaction_id=f"manual-{uuid4().hex[:12]}",
        amount=payload.amount,
        transaction_type=transaction_type,
        description=payload.description or payload.counterparty_name,
        posted_at=posted_at,
        balance_after=new_bank_balance,
        raw_payload=json.dumps(
            {
                "source": "manual-entry",
                "direction": payload.direction,
                "counterparty_name": payload.counterparty_name,
                "description": payload.description,
                "transaction_date": payload.transaction_date.isoformat(),
            }
        ),
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    transactions = db.query(BankTransaction).filter(BankTransaction.user_id == user_id).all()
    refreshed_summary = upsert_financial_summary(
        db,
        user_id=user_id,
        current_balance=new_bank_balance,
        transactions=transactions,
        minimum_cash_floor=minimum_cash_floor,
        source="manual-financial-entry",
        session_id=summary.last_session_id,
    )
    return transaction, refreshed_summary


def bootstrap_financial_summary_from_legacy(
    db: Session,
    user_id: int,
    minimum_cash_floor: float,
) -> FinancialSummary:
    existing = db.query(FinancialSummary).filter(FinancialSummary.user_id == user_id).first()
    if existing:
        return existing

    account = db.query(Account).filter(Account.user_id == user_id).first()
    company = db.query(Company).filter(Company.user_id == user_id).first()
    current_balance = 0.0
    monthly_income = 0.0
    monthly_expense = 0.0
    if account:
        current_balance = account.current_balance
    elif company:
        current_balance = company.cash_balance

    if company:
        monthly_income = company.monthly_income
        monthly_expense = company.monthly_expenses

    summary = FinancialSummary(
        user_id=user_id,
        current_balance=round(current_balance, 2),
        monthly_income=round(monthly_income, 2),
        monthly_expense=round(monthly_expense, 2),
        burn_rate=round(monthly_expense - monthly_income, 2),
        daily_expense=round(monthly_expense / 30, 2) if monthly_expense > 0 else 0.0,
        runway_days=round(current_balance / (monthly_expense / 30), 1) if monthly_expense > 0 else 999.0,
        cash_reserve_ratio=round(current_balance / minimum_cash_floor, 2) if minimum_cash_floor > 0 else 999.0,
        emi_payments=0.0,
        source="legacy-bootstrap",
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    reconcile_pending_payments(db, user_id)
    sync_financial_summary_to_company(db, user_id, summary)
    return summary


@router.get("/financial-summary/{user_id}", response_model=FinancialSummaryResponse)
def get_financial_summary(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialSummaryResponse:
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own financial summary.")

    summary = bootstrap_financial_summary_from_legacy(db, user_id, minimum_cash_floor=2000)
    balance = get_reconciled_balance(db, user_id, summary.current_balance)
    return FinancialSummaryResponse(
        balance=balance,
        monthly_income=summary.monthly_income,
        monthly_expense=summary.monthly_expense,
        burn_rate=summary.burn_rate,
        runway_days=summary.runway_days,
        cash_reserve_ratio=summary.cash_reserve_ratio,
    )


@router.post("/financial-transactions/manual", response_model=ManualTransactionResponse)
def create_manual_transaction_endpoint(
    payload: ManualTransactionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManualTransactionResponse:
    transaction, summary = create_manual_transaction(db, current_user.id, payload, minimum_cash_floor=2000)
    return ManualTransactionResponse(
        transaction_id=transaction.transaction_id,
        direction=payload.direction,
        amount=transaction.amount,
        balance=get_reconciled_balance(db, current_user.id, summary.current_balance),
        monthly_income=summary.monthly_income,
        monthly_expense=summary.monthly_expense,
    )
