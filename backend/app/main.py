from datetime import datetime

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .config import settings
from .db import Base, engine, get_db, run_startup_migrations
from .models import Account, BankTransaction, Company, Decision, FinancialSummary, Payable, PendingPaymentEvent, SetuConsent, SetuDataSession, ThemePreference, User
from .schemas import (
    AuthResponse,
    ClassifyCompanyRequest,
    ConfirmPaymentsRequest,
    ConfirmPaymentsResponse,
    CompanyMetricsResponse,
    ConnectBankResponse,
    DashboardStateResponse,
    DecisionOut,
    EmailGenerationRequest,
    EmailGenerationResponse,
    InvoiceUploadResponse,
    OCRParseSummary,
    OptimizerDecisionResponse,
    PayableOut,
    ResetUserDataRequest,
    ResetUserDataResponse,
    ManualTransactionCreateRequest,
    ManualTransactionResponse,
    SetuConsentInitiateRequest,
    Token,
    TrustScoreUpdateRequest,
    UserCreate,
    UserLogin,
    UserOut,
)
from .services.cse import classify_company
from .services.financial_summary_service import (
    bootstrap_financial_summary_from_legacy,
    create_manual_transaction,
    get_reconciled_balance,
    router as financial_summary_router,
)
from .services.ocr import extract_invoice_data
from .services.priorities import infer_priority, priority_weights
from .services.optimizer import ScoredBill, solve_payment_strategy
from .services.setu_consent_service import initiate_setu_consent, router as setu_consent_router
from .services.setu_data_service import create_fi_data_session, fetch_and_store_fi_data
from .services.setu_webhook_service import router as setu_webhook_router


app = FastAPI(title=settings.app_name)
MIN_CASH_FLOOR = 2000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(financial_summary_router)
app.include_router(setu_consent_router)
app.include_router(setu_webhook_router)


def _serialize_company(company: Company) -> CompanyMetricsResponse:
    return CompanyMetricsResponse(
        company_name=company.company_name,
        cash_balance=company.cash_balance,
        monthly_income=company.monthly_income,
        monthly_expenses=company.monthly_expenses,
        upcoming_bills_total=company.upcoming_bills_total,
        runway_days=company.runway_days,
        coverage_ratio=company.coverage_ratio,
        cash_flow=company.cash_flow,
        risk_category=company.risk_category,
    )


def _serialize_payable(payable: Payable) -> PayableOut:
    priority_label, priority_reason = infer_priority(payable.category, payable.due_date, payable.amount)
    invoice_url = f"/payables/{payable.id}/invoice" if payable.invoice_data else payable.invoice_url
    return PayableOut(
        id=payable.id,
        vendor_name=payable.vendor_name,
        amount=payable.amount,
        due_date=payable.due_date,
        category=payable.category,
        invoice_url=invoice_url,
        is_critical=payable.is_critical,
        payroll_date=payable.payroll_date,
        days_overdue=payable.days_overdue,
        priority_label=priority_label,
        priority_reason=priority_reason,
        trust_score=payable.trust_score,
        score=None,
        is_hard_constraint=None,
        survival_impact=None,
        affordability_warning=None,
    )


def _serialize_scored_bill(scored_bill: ScoredBill) -> PayableOut:
    base = _serialize_payable(scored_bill.bill)
    return PayableOut(
        id=base.id,
        vendor_name=base.vendor_name,
        amount=base.amount,
        due_date=base.due_date,
        category=base.category,
        invoice_url=base.invoice_url,
        is_critical=base.is_critical,
        payroll_date=base.payroll_date,
        days_overdue=base.days_overdue,
        priority_label=base.priority_label,
        priority_reason=base.priority_reason,
        trust_score=base.trust_score,
        score=scored_bill.score,
        is_hard_constraint=scored_bill.is_hard_constraint,
        survival_impact=scored_bill.survival_impact,
        affordability_warning=scored_bill.affordability_warning,
    )


def _infer_vendor_aggression(category: str, priority_label: str, extracted_text: str | None) -> str:
    lowered = (extracted_text or "").lower()
    normalized_category = (category or "Operations").lower()
    if any(token in lowered for token in ["final notice", "legal notice", "disconnect", "termination", "suspension"]):
        return "ADVERSARIAL"
    if normalized_category in {"legal", "tax", "utilities"} or priority_label == "HIGH":
        return "ADVERSARIAL"
    if any(token in lowered for token in ["thank you", "please contact us", "grace period", "friendly reminder"]):
        return "COOPERATIVE"
    return "NEUTRAL"


def _infer_blocks_revenue(category: str, extracted_text: str | None) -> bool:
    lowered = (extracted_text or "").lower()
    normalized_category = (category or "Operations").lower()
    revenue_blocking_categories = {"inventory", "utilities", "payroll"}
    if normalized_category in revenue_blocking_categories:
        return True
    return any(token in lowered for token in ["stockout", "supply stop", "disconnect", "production halt", "service suspension"])


def _decision_out(decision: Decision) -> DecisionOut:
    return DecisionOut(
        id=decision.id,
        cycle_date=decision.cycle_date,
        selected_bill_ids=[int(item) for item in decision.selected_bill_ids.split(",") if item],
        total_paid=decision.total_paid,
        cse_category_used=decision.cse_category_used,
    )


def _refresh_company(company: Company, db: Session) -> Company:
    summary = db.query(FinancialSummary).filter(FinancialSummary.user_id == company.user_id).first()
    if summary:
        company.cash_balance = get_reconciled_balance(db, company.user_id, summary.current_balance)
        company.monthly_income = summary.monthly_income
        company.monthly_expenses = summary.monthly_expense
        company.cash_flow = round(summary.monthly_income - summary.monthly_expense, 2)
    payables = db.query(Payable).filter(Payable.user_id == company.user_id).all()
    company.upcoming_bills_total = round(sum(item.amount for item in payables), 2)
    metrics = classify_company(
        company.cash_balance,
        company.monthly_income,
        company.monthly_expenses,
        company.upcoming_bills_total,
    )
    company.runway_days = metrics.runway_days
    company.coverage_ratio = metrics.coverage_ratio
    company.cash_flow = metrics.cash_flow
    company.risk_category = metrics.risk_category
    company.last_updated = datetime.utcnow()
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _ensure_sqlite_schema_compatibility() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    expected_columns: dict[str, dict[str, str]] = {
        "users": {
            "theme_preference": "ALTER TABLE users ADD COLUMN theme_preference VARCHAR(5) DEFAULT 'dark'",
        },
        "accounts": {
            "bank_name": "ALTER TABLE accounts ADD COLUMN bank_name VARCHAR(255) DEFAULT 'Primary Account'",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, column_ddls in expected_columns.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in column_ddls.items():
                if column_name not in existing_columns:
                    connection.execute(text(ddl))


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema_compatibility()
    run_startup_migrations()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    metrics = classify_company(payload.opening_cash_balance, 0, 0, 0)
    db.add(
        Company(
            user_id=user.id,
            company_name=payload.company_name,
            cash_balance=payload.opening_cash_balance,
            monthly_income=0,
            monthly_expenses=0,
            upcoming_bills_total=0,
            runway_days=metrics.runway_days,
            coverage_ratio=metrics.coverage_ratio,
            cash_flow=metrics.cash_flow,
            risk_category=metrics.risk_category,
            last_updated=datetime.utcnow(),
        )
    )
    db.add(Account(user_id=user.id, current_balance=payload.opening_cash_balance, bank_name="Primary Account"))
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    return AuthResponse(user=UserOut.model_validate(user), token=Token(access_token=token))


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.email)
    return AuthResponse(user=UserOut.model_validate(user), token=Token(access_token=token))


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@app.post("/auth/theme", response_model=UserOut)
def update_theme(
    theme: ThemePreference = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    current_user.theme_preference = theme
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)


@app.delete("/user-data", response_model=ResetUserDataResponse)
def reset_user_data(
    payload: ResetUserDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResetUserDataResponse:
    db.query(Decision).filter(Decision.user_id == current_user.id).delete()
    db.query(PendingPaymentEvent).filter(PendingPaymentEvent.user_id == current_user.id).delete()
    db.query(BankTransaction).filter(BankTransaction.user_id == current_user.id).delete()
    db.query(SetuDataSession).filter(SetuDataSession.user_id == current_user.id).delete()
    db.query(SetuConsent).filter(SetuConsent.user_id == current_user.id).delete()
    db.query(Payable).filter(Payable.user_id == current_user.id).delete()
    db.query(Account).filter(Account.user_id == current_user.id).delete()
    db.query(Company).filter(Company.user_id == current_user.id).delete()
    db.query(FinancialSummary).filter(FinancialSummary.user_id == current_user.id).delete()
    db.add(Account(user_id=current_user.id, current_balance=payload.opening_cash_balance, bank_name="Primary Account"))
    metrics = classify_company(payload.opening_cash_balance, 0, 0, 0)
    db.add(
        Company(
            user_id=current_user.id,
            company_name="My Company",
            cash_balance=payload.opening_cash_balance,
            monthly_income=0,
            monthly_expenses=0,
            upcoming_bills_total=0,
            runway_days=metrics.runway_days,
            coverage_ratio=metrics.coverage_ratio,
            cash_flow=metrics.cash_flow,
            risk_category=metrics.risk_category,
            last_updated=datetime.utcnow(),
        )
    )
    db.commit()
    return ResetUserDataResponse(message="All financial data for this user has been cleared and reset with your current cash balance.")


@app.post("/classify-company", response_model=CompanyMetricsResponse)
def classify_company_endpoint(payload: ClassifyCompanyRequest) -> CompanyMetricsResponse:
    metrics = classify_company(
        payload.cash_balance,
        payload.monthly_income,
        payload.monthly_expenses,
        payload.upcoming_bills_total,
    )
    return CompanyMetricsResponse(
        company_name="Ad Hoc Company",
        cash_balance=payload.cash_balance,
        monthly_income=payload.monthly_income,
        monthly_expenses=payload.monthly_expenses,
        upcoming_bills_total=payload.upcoming_bills_total,
        runway_days=metrics.runway_days,
        coverage_ratio=metrics.coverage_ratio,
        cash_flow=metrics.cash_flow,
        risk_category=metrics.risk_category,
    )


@app.get("/company-status", response_model=CompanyMetricsResponse)
def company_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CompanyMetricsResponse:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company = _refresh_company(company, db)
    return _serialize_company(company)


@app.post("/upload-invoice", response_model=InvoiceUploadResponse)
def upload_invoice(
    file: UploadFile | None = File(default=None),
    vendor_name: str | None = Form(default=None),
    amount: float | None = Form(default=None),
    due_date: str | None = Form(default=None),
    category: str | None = Form(default=None),
    trust_score: float | None = Form(default=None),
    cash_flow_direction: str = Form(default="money_out"),
    debug_fill: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceUploadResponse:
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date).date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="due_date must be in YYYY-MM-DD format") from exc

    extracted_text: str | None = None
    parsed_invoice: OCRParseSummary | None = None
    resolved_vendor_name = vendor_name
    resolved_amount = amount
    resolved_due_date = parsed_due_date
    resolved_category = category
    invoice_url = None
    invoice_file_name: str | None = None
    invoice_content_type: str | None = None
    invoice_data: bytes | None = None

    if file is not None:
        extraction = extract_invoice_data(file)
        extracted_text = extraction.text
        resolved_vendor_name = resolved_vendor_name or extraction.vendor_name
        resolved_amount = resolved_amount or extraction.amount
        resolved_due_date = resolved_due_date or extraction.due_date
        resolved_category = resolved_category or extraction.category
        invoice_file_name = extraction.source_file_name
        invoice_content_type = extraction.content_type
        invoice_data = extraction.file_bytes
        parsed_invoice = OCRParseSummary(
            vendor_name=extraction.vendor_name,
            amount=extraction.amount,
            due_date=extraction.due_date,
            category=extraction.category,
            priority_label=extraction.priority_label,
            priority_reason=extraction.priority_reason,
            confidence_notes=extraction.confidence_notes,
        )

    resolved_direction = cash_flow_direction if cash_flow_direction in {"money_in", "money_out"} else "money_out"

    priority_label, priority_reason = infer_priority(
        resolved_category or "Operations",
        resolved_due_date or datetime.utcnow().date(),
        resolved_amount or (3200 if debug_fill else 4500),
        extracted_text,
    )

    if resolved_direction == "money_in":
        transaction, summary = create_manual_transaction(
            db,
            current_user.id,
            ManualTransactionCreateRequest(
                direction="money_in",
                counterparty_name=resolved_vendor_name or ("Customer Receipt" if debug_fill else "OCR Receipt"),
                amount=resolved_amount or (3200 if debug_fill else 4500),
                transaction_date=resolved_due_date or datetime.utcnow().date(),
                description=f"OCR upload from {file.filename}" if file is not None else "OCR upload",
            ),
            minimum_cash_floor=MIN_CASH_FLOOR,
        )
        return InvoiceUploadResponse(
            payable=None,
            manual_transaction=ManualTransactionResponse(
                transaction_id=transaction.transaction_id,
                direction="money_in",
                amount=transaction.amount,
                balance=get_reconciled_balance(db, current_user.id, summary.current_balance),
                monthly_income=summary.monthly_income,
                monthly_expense=summary.monthly_expense,
            ),
            extracted_text=extracted_text,
            parsed_invoice=parsed_invoice,
            source_file_name=file.filename if file is not None else None,
            ocr_engine="tesseract" if file is not None else "debug-fill",
        )

    default_trust_score, penalty_risk, criticality, revenue_impact, implied_critical = priority_weights(priority_label)
    resolved_trust_score = default_trust_score if trust_score is None else min(max(trust_score, 0.0), 1.0)
    vendor_aggression = _infer_vendor_aggression(resolved_category or "Operations", priority_label, extracted_text)
    blocks_revenue = _infer_blocks_revenue(resolved_category or "Operations", extracted_text)
    payable = Payable(
        user_id=current_user.id,
        vendor_name=resolved_vendor_name or ("Emergency Linen Co." if debug_fill else "Debug Supplier"),
        amount=resolved_amount or (3200 if debug_fill else 4500),
        due_date=resolved_due_date or datetime.utcnow().date(),
        category=resolved_category or "Operations",
        invoice_url=invoice_url,
        invoice_file_name=invoice_file_name,
        invoice_content_type=invoice_content_type,
        invoice_data=invoice_data,
        vendor_aggression=vendor_aggression,
        blocks_revenue=blocks_revenue,
        trust_score=resolved_trust_score,
        penalty_risk=penalty_risk,
        criticality=criticality,
        revenue_impact=revenue_impact,
        is_critical=(resolved_category or "") in {"Legal", "Payroll"} or implied_critical,
        payroll_date=(resolved_category or "") == "Payroll",
        days_overdue=0,
    )
    db.add(payable)
    db.commit()
    db.refresh(payable)

    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if company:
        _refresh_company(company, db)

    return InvoiceUploadResponse(
        payable=_serialize_payable(payable),
        manual_transaction=None,
        extracted_text=extracted_text,
        parsed_invoice=parsed_invoice,
        source_file_name=file.filename if file is not None else None,
        ocr_engine="tesseract" if file is not None else "debug-fill",
    )


@app.patch("/payables/{bill_id}/trust-score", response_model=PayableOut)
def update_trust_score(
    bill_id: int,
    payload: TrustScoreUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PayableOut:
    payable = (
        db.query(Payable)
        .filter(Payable.user_id == current_user.id, Payable.id == bill_id)
        .first()
    )
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    payable.trust_score = payload.trust_score
    db.add(payable)
    db.commit()
    db.refresh(payable)
    return _serialize_payable(payable)


@app.get("/payables/{bill_id}/invoice")
def get_invoice_file(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    payable = (
        db.query(Payable)
        .filter(Payable.user_id == current_user.id, Payable.id == bill_id)
        .first()
    )
    if not payable or not payable.invoice_data:
        raise HTTPException(status_code=404, detail="Invoice file not found")

    file_name = payable.invoice_file_name or f"invoice-{payable.id}"
    content_type = payable.invoice_content_type or "application/octet-stream"
    headers = {"Content-Disposition": f'inline; filename="{file_name}"'}
    return Response(content=payable.invoice_data, media_type=content_type, headers=headers)


@app.post("/connect-bank", response_model=ConnectBankResponse)
def connect_bank(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ConnectBankResponse:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not company or not account:
        raise HTTPException(status_code=404, detail="Financial profile not found")

    consent = initiate_setu_consent(
        db,
        current_user,
        payload=SetuConsentInitiateRequest(
            mobile_number="9999999999",
            purpose="Liquidity engine bank sync",
            redirect_url=settings.setu_redirect_url,
        ),
    )

    if consent.consent_id.startswith("mock-consent-"):
        consent.status = "APPROVED"
        db.add(consent)
        db.commit()
        session = create_fi_data_session(db, consent)
        summary = fetch_and_store_fi_data(db, session)
        company = _refresh_company(company, db)
        return ConnectBankResponse(
            bank_name="Setu Sandbox",
            current_balance=company.cash_balance,
            synced_at=datetime.utcnow(),
            consent_id=consent.consent_id,
            approval_url=None,
            status="SYNCED",
            source=summary.source,
        )

    return ConnectBankResponse(
        bank_name="Setu",
        current_balance=None,
        synced_at=None,
        consent_id=consent.consent_id,
        approval_url=consent.approval_url,
        status=consent.status,
        source="setu",
    )


@app.post("/run-optimizer", response_model=OptimizerDecisionResponse)
def run_optimizer(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OptimizerDecisionResponse:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    payables = db.query(Payable).filter(Payable.user_id == current_user.id).order_by(Payable.due_date.asc()).all()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not payables:
        raise HTTPException(status_code=400, detail="Upload at least one invoice before running the engine.")

    summary = bootstrap_financial_summary_from_legacy(db, current_user.id, MIN_CASH_FLOOR)
    reconciled_balance = get_reconciled_balance(db, current_user.id, summary.current_balance)
    company.cash_balance = reconciled_balance
    company.monthly_income = summary.monthly_income
    company.monthly_expenses = summary.monthly_expense
    db.add(company)
    db.commit()
    company = _refresh_company(company, db)
    available_cash = max(reconciled_balance - MIN_CASH_FLOOR, 0)
    if available_cash <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No spendable cash is available. Current balance is Rs {reconciled_balance:.0f} "
                f"and the engine must preserve a cash floor of Rs {MIN_CASH_FLOOR}. "
                "Use Delete my data to reset your opening cash balance or sync a funded account first."
            ),
        )

    result = solve_payment_strategy(company.risk_category, payables, reconciled_balance, summary.monthly_expense)
    if not result.selected_bills:
        raise HTTPException(
            status_code=400,
            detail=(
                "The engine could not schedule any payments without breaking the cash floor or violating the current "
                "hard constraints. Add more cash, reduce required bills, or reset your opening balance before running again."
            ),
        )

    hard_constraints_consumed_cash = any(item.is_hard_constraint for item in result.selected_bills)
    if hard_constraints_consumed_cash:
        for delayed_bill in result.delayed_bills:
            if delayed_bill.is_hard_constraint:
                continue
            delayed_bill.bill.trust_score = round(max(0.0, delayed_bill.bill.trust_score - 0.1), 3)
            db.add(delayed_bill.bill)

    decision = Decision(
        user_id=current_user.id,
        selected_bill_ids=",".join(str(item.bill.id) for item in result.selected_bills),
        total_paid=result.total_selected_amount,
        cse_category_used=company.risk_category,
    )
    db.add(decision)
    db.commit()

    return OptimizerDecisionResponse(
        category=company.risk_category,
        strategy=result.strategy,
        available_cash=available_cash,
        cash_floor=MIN_CASH_FLOOR,
        total_selected_amount=result.total_selected_amount,
        projected_runway_days=result.projected_runway_days,
        selected_bills=[_serialize_scored_bill(item) for item in result.selected_bills],
        delayed_bills=[_serialize_scored_bill(item) for item in result.delayed_bills],
        explanation=result.explanation,
        critical_shortfall=result.critical_shortfall,
    )


@app.post("/confirm-payments", response_model=ConfirmPaymentsResponse)
def confirm_payments(
    payload: ConfirmPaymentsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfirmPaymentsResponse:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not company or not account:
        raise HTTPException(status_code=404, detail="Financial profile not found")
    summary = bootstrap_financial_summary_from_legacy(db, current_user.id, MIN_CASH_FLOOR)
    reconciled_balance = get_reconciled_balance(db, current_user.id, summary.current_balance)

    payables = (
        db.query(Payable)
        .filter(Payable.user_id == current_user.id, Payable.id.in_(payload.bill_ids))
        .all()
    )
    if not payables:
        raise HTTPException(status_code=404, detail="No matching bills found to confirm payment.")

    total_paid = round(sum(item.amount for item in payables), 2)
    if total_paid > reconciled_balance:
        raise HTTPException(status_code=400, detail="Not enough cash balance to confirm these payments.")
    remaining_balance = round(reconciled_balance - total_paid, 2)
    if remaining_balance < MIN_CASH_FLOOR:
        raise HTTPException(
            status_code=400,
            detail=f"You must keep at least Rs {MIN_CASH_FLOOR} in the account after confirming payments.",
        )

    paid_bill_ids = [item.id for item in payables]
    for item in payables:
        db.add(
            PendingPaymentEvent(
                user_id=current_user.id,
                payable_id=item.id,
                vendor_name=item.vendor_name,
                amount=item.amount,
                description=f"Confirmed payment for {item.vendor_name}",
            )
        )
        db.delete(item)

    company.cash_balance = remaining_balance
    account.current_balance = remaining_balance
    db.add_all([company, account])
    db.commit()
    company = _refresh_company(company, db)

    return ConfirmPaymentsResponse(
        paid_bill_ids=paid_bill_ids,
        total_paid=total_paid,
        remaining_cash_balance=remaining_balance,
        remaining_upcoming_bills_total=company.upcoming_bills_total,
        message="Selected bills have been marked as paid and removed from upcoming payables.",
    )


@app.get("/dashboard-state", response_model=DashboardStateResponse)
def dashboard_state(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardStateResponse:
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company = _refresh_company(company, db)
    payables = db.query(Payable).filter(Payable.user_id == current_user.id).order_by(Payable.due_date.asc()).all()
    decisions = (
        db.query(Decision)
        .filter(Decision.user_id == current_user.id)
        .order_by(Decision.cycle_date.desc(), Decision.id.desc())
        .limit(5)
        .all()
    )
    accounts_total = sum(account.current_balance for account in db.query(Account).filter(Account.user_id == current_user.id).all())
    return DashboardStateResponse(
        company=_serialize_company(company),
        accounts_total=accounts_total,
        payables=[_serialize_payable(item) for item in payables],
        recent_decisions=[_decision_out(item) for item in decisions],
        health_badge_color={
            "SAFE": "green",
            "STABLE": "blue",
            "RISKY": "orange",
            "CRITICAL": "red",
        }[company.risk_category.value],
        suggested_action={
            "SAFE": "Operate normally and invest in supplier trust.",
            "STABLE": "Protect the cash floor while avoiding overdue penalties.",
            "RISKY": "Focus on penalty-heavy and payroll-linked obligations first.",
            "CRITICAL": "Preserve only survival payments and negotiate delays immediately.",
        }[company.risk_category.value],
    )


@app.post("/generate-email", response_model=EmailGenerationResponse)
def generate_email(
    payload: EmailGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailGenerationResponse:
    bill = db.query(Payable).filter(Payable.user_id == current_user.id, Payable.id == payload.bill_id).first()
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not bill or not company:
        raise HTTPException(status_code=404, detail="Bill not found")

    subject = f"Payment timing update for {bill.vendor_name}"
    intro = {
        "empathetic": "I wanted to reach out proactively and share a transparent update on our cash flow timing.",
        "firm": "I am writing to confirm the timing adjustment we need on this payment.",
        "neutral": "I am reaching out regarding the payment timeline for the attached invoice.",
    }[payload.tone]
    body = (
        f"Hi {bill.vendor_name},\n\n"
        f"{intro} Our engine currently has us in {company.risk_category.value} mode, so we are prioritizing payroll and near-term operating obligations first. "
        f"We expect to clear the Rs {bill.amount:.0f} balance shortly after the next receivables cycle and would appreciate flexibility until then.\n\n"
        "Thank you for working with us,\nSarah"
    )
    return EmailGenerationResponse(subject=subject, body=body)
