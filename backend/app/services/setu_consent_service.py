import json
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..db import get_db
from ..models import SetuConsent, User
from ..schemas import SetuConsentInitiateRequest


router = APIRouter(tags=["setu"])


def _setu_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.setu_client_id:
        headers["x-client-id"] = settings.setu_client_id
    if settings.setu_client_secret:
        headers["x-client-secret"] = settings.setu_client_secret
    if settings.setu_product_instance_id:
        headers["x-product-instance-id"] = settings.setu_product_instance_id
    return headers


def _setu_is_configured() -> bool:
    return bool(settings.setu_client_id and settings.setu_client_secret and settings.setu_product_instance_id)


def initiate_setu_consent(db: Session, user: User, payload: SetuConsentInitiateRequest) -> SetuConsent:
    redirect_url = payload.redirect_url or settings.setu_redirect_url
    if settings.setu_mock_enabled and not _setu_is_configured():
        consent = SetuConsent(
            user_id=user.id,
            consent_id=f"mock-consent-{uuid4().hex[:12]}",
            status="PENDING",
            approval_url=f"{redirect_url}?consent_id=mock-{uuid4().hex[:8]}&status=PENDING",
            redirect_url=redirect_url,
            consent_payload=json.dumps({"mode": "mock", "mobile": payload.mobile_number}),
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        return consent

    body = {
        "redirectUrl": redirect_url,
        "consentMode": "STORE",
        "purpose": payload.purpose,
        "vua": payload.vua,
        "dataRange": {"from": payload.data_from.isoformat(), "to": payload.data_to.isoformat()},
        "mobile": payload.mobile_number,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(f"{settings.setu_base_url}/v2/consents", headers=_setu_headers(), json=body)
        response.raise_for_status()
        response_data = response.json()

    consent = SetuConsent(
        user_id=user.id,
        consent_id=str(response_data.get("id") or response_data.get("consentId") or uuid4().hex),
        status=str(response_data.get("status") or "PENDING"),
        approval_url=str(response_data.get("url") or response_data.get("approvalUrl") or redirect_url),
        redirect_url=redirect_url,
        consent_payload=json.dumps(response_data),
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


@router.post("/setu/consent/initiate", status_code=status.HTTP_303_SEE_OTHER)
def initiate_setu_consent_endpoint(
    payload: SetuConsentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        consent = initiate_setu_consent(db, current_user, payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Setu consent initiation failed: {exc}") from exc

    return RedirectResponse(url=consent.approval_url or (payload.redirect_url or settings.setu_redirect_url), status_code=status.HTTP_303_SEE_OTHER)
