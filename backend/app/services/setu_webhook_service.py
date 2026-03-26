from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SetuConsent, SetuDataSession
from ..schemas import SetuWebhookPayload, SetuWebhookResponse
from .setu_data_service import create_fi_data_session, fetch_and_store_fi_data


router = APIRouter(tags=["setu"])


def _extract_consent_id(payload: SetuWebhookPayload) -> str | None:
    return payload.consent_id or payload.payload.get("consentId") or payload.payload.get("id")


def _extract_session_id(payload: SetuWebhookPayload) -> str | None:
    return payload.session_id or payload.payload.get("sessionId") or payload.payload.get("id")


@router.post("/setu/webhook", response_model=SetuWebhookResponse)
def receive_setu_webhook(payload: SetuWebhookPayload, db: Session = Depends(get_db)) -> SetuWebhookResponse:
    event_type = (payload.event_type or payload.payload.get("eventType") or payload.payload.get("type") or "").upper()
    status = (payload.status or payload.payload.get("status") or "").upper()

    if "CONSENT" in event_type or payload.consent_id or payload.payload.get("consentId"):
        consent_id = _extract_consent_id(payload)
        if not consent_id:
            raise HTTPException(status_code=400, detail="Webhook payload did not contain a consent_id.")

        consent = db.query(SetuConsent).filter(SetuConsent.consent_id == consent_id).first()
        if not consent:
            raise HTTPException(status_code=404, detail="Consent not found for webhook payload.")

        consent.status = status or consent.status
        db.add(consent)
        db.commit()

        if consent.status == "APPROVED":
            session = create_fi_data_session(db, consent)
            if session.status in {"READY", "COMPLETED"}:
                fetch_and_store_fi_data(db, session)
            return SetuWebhookResponse(ok=True, message="Consent approved and data session triggered.", consent_id=consent_id, session_id=session.session_id)

        return SetuWebhookResponse(ok=True, message="Consent status recorded.", consent_id=consent_id)

    if "SESSION" in event_type or payload.session_id or payload.payload.get("sessionId"):
        session_id = _extract_session_id(payload)
        if not session_id:
            raise HTTPException(status_code=400, detail="Webhook payload did not contain a session_id.")

        session = db.query(SetuDataSession).filter(SetuDataSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for webhook payload.")

        session.status = status or session.status
        db.add(session)
        db.commit()

        if session.status in {"READY", "COMPLETED", "SUCCESS"}:
            fetch_and_store_fi_data(db, session)
            return SetuWebhookResponse(ok=True, message="Session data fetched and stored.", session_id=session_id)

        return SetuWebhookResponse(ok=True, message="Session status recorded.", session_id=session_id)

    return SetuWebhookResponse(ok=True, message="Webhook accepted with no action taken.")
