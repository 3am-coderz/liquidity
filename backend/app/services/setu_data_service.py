import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import BankTransaction, FinancialSummary, SetuConsent, SetuDataSession
from .financial_summary_service import upsert_financial_summary


def setu_is_configured() -> bool:
    return bool(settings.setu_client_id and settings.setu_client_secret and settings.setu_product_instance_id)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _setu_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.setu_client_id:
        headers["x-client-id"] = settings.setu_client_id
    if settings.setu_client_secret:
        headers["x-client-secret"] = settings.setu_client_secret
    if settings.setu_product_instance_id:
        headers["x-product-instance-id"] = settings.setu_product_instance_id
    return headers


def _extract_balance(payload: object) -> float:
    if isinstance(payload, dict):
        for key in ["currentBalance", "current_balance", "balance", "availableBalance"]:
            value = payload.get(key)
            parsed = _parse_amount(value)
            if parsed is not None:
                return parsed
        for value in payload.values():
            parsed = _extract_balance(value)
            if parsed is not None:
                return parsed
    if isinstance(payload, list):
        for item in payload:
            parsed = _extract_balance(item)
            if parsed is not None:
                return parsed
    return 0.0


def _parse_amount(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ["amount", "value"]:
            if key in value:
                return _parse_amount(value[key])
    return None


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned).replace(tzinfo=None)
        except ValueError:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
    return _utc_now()


def _infer_transaction_type(amount: float, item: dict[str, object]) -> str:
    explicit_type = str(item.get("type") or item.get("transactionType") or item.get("txnType") or "").upper()
    if explicit_type in {"CREDIT", "DEBIT"}:
        return explicit_type
    return "CREDIT" if amount >= 0 else "DEBIT"


def parse_fi_data_payload(payload: dict[str, object]) -> tuple[float, list[dict[str, object]]]:
    current_balance = _extract_balance(payload)
    transactions: list[dict[str, object]] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            maybe_transactions = node.get("transactions")
            if isinstance(maybe_transactions, list):
                for item in maybe_transactions:
                    if not isinstance(item, dict):
                        continue
                    raw_amount = _parse_amount(item.get("amount"))
                    if raw_amount is None:
                        continue
                    tx_type = _infer_transaction_type(raw_amount, item)
                    amount = abs(raw_amount)
                    transactions.append(
                        {
                            "transaction_id": str(
                                item.get("id")
                                or item.get("transactionId")
                                or item.get("txnId")
                                or uuid4().hex
                            ),
                            "amount": amount,
                            "transaction_type": tx_type,
                            "description": str(item.get("description") or item.get("narration") or item.get("remarks") or ""),
                            "posted_at": _parse_datetime(
                                item.get("valueDate")
                                or item.get("transactionTimestamp")
                                or item.get("date")
                                or item.get("postedAt")
                            ),
                            "balance_after": _parse_amount(item.get("currentBalance") or item.get("balanceAfter")),
                            "raw_payload": json.dumps(item),
                        }
                    )
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return round(current_balance, 2), transactions


def _mock_fi_data() -> dict[str, object]:
    now = _utc_now()
    return {
        "account": {"currentBalance": 86500.0},
        "transactions": [
            {"transactionId": uuid4().hex, "amount": 125000.0, "type": "CREDIT", "description": "Client settlement", "date": (now - timedelta(days=4)).isoformat()},
            {"transactionId": uuid4().hex, "amount": 18000.0, "type": "DEBIT", "description": "EMI loan auto debit", "date": (now - timedelta(days=6)).isoformat()},
            {"transactionId": uuid4().hex, "amount": 26000.0, "type": "DEBIT", "description": "Payroll transfer", "date": (now - timedelta(days=10)).isoformat()},
            {"transactionId": uuid4().hex, "amount": 9500.0, "type": "DEBIT", "description": "Rent payment", "date": (now - timedelta(days=14)).isoformat()},
            {"transactionId": uuid4().hex, "amount": 42000.0, "type": "CREDIT", "description": "UPI collections", "date": (now - timedelta(days=20)).isoformat()},
            {"transactionId": uuid4().hex, "amount": 13750.0, "type": "DEBIT", "description": "Utility and internet", "date": (now - timedelta(days=22)).isoformat()},
        ],
    }


def create_fi_data_session(db: Session, consent: SetuConsent) -> SetuDataSession:
    if settings.setu_mock_enabled and not setu_is_configured():
        session = SetuDataSession(
            user_id=consent.user_id,
            consent_id=consent.consent_id,
            session_id=f"mock-session-{uuid4().hex[:12]}",
            status="READY",
            session_payload=json.dumps({"mode": "mock", "consent_id": consent.consent_id}),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        fetch_and_store_fi_data(db, session)
        return session

    payload = {
        "consentId": consent.consent_id,
        "dataRange": {
            "from": (_utc_now() - timedelta(days=180)).date().isoformat(),
            "to": _utc_now().date().isoformat(),
        },
        "format": "json",
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(f"{settings.setu_base_url}/v2/sessions", headers=_setu_headers(), json=payload)
        response.raise_for_status()
        response_data = response.json()

    session = SetuDataSession(
        user_id=consent.user_id,
        consent_id=consent.consent_id,
        session_id=str(response_data.get("id") or response_data.get("sessionId") or uuid4().hex),
        status=str(response_data.get("status") or "PENDING"),
        session_payload=json.dumps(response_data),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def fetch_and_store_fi_data(db: Session, session: SetuDataSession) -> FinancialSummary:
    if settings.setu_mock_enabled and (session.session_id.startswith("mock-session-") or not setu_is_configured()):
        fi_payload = _mock_fi_data()
        session.status = "COMPLETED"
        session.raw_fi_payload = json.dumps(fi_payload)
        db.add(session)
        db.commit()
    else:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(f"{settings.setu_base_url}/v2/sessions/{session.session_id}", headers=_setu_headers())
            response.raise_for_status()
            fi_payload = response.json()
        session.status = str(fi_payload.get("status") or "COMPLETED")
        session.raw_fi_payload = json.dumps(fi_payload)
        db.add(session)
        db.commit()

    current_balance, parsed_transactions = parse_fi_data_payload(json.loads(session.raw_fi_payload or "{}"))

    db.query(BankTransaction).filter(BankTransaction.user_id == session.user_id).delete()
    for item in parsed_transactions:
        db.add(
            BankTransaction(
                user_id=session.user_id,
                session_id=session.session_id,
                transaction_id=str(item["transaction_id"]),
                amount=float(item["amount"]),
                transaction_type=str(item["transaction_type"]),
                description=str(item["description"]),
                posted_at=item["posted_at"],
                balance_after=item["balance_after"],
                raw_payload=str(item["raw_payload"]),
            )
        )
    db.commit()

    stored_transactions = db.query(BankTransaction).filter(BankTransaction.user_id == session.user_id).all()
    return upsert_financial_summary(
        db,
        user_id=session.user_id,
        current_balance=current_balance,
        transactions=stored_transactions,
        minimum_cash_floor=2000,
        source="setu-mock" if session.session_id.startswith("mock-session-") else "setu",
        session_id=session.session_id,
    )
