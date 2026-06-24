from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent import service
from app.agent.schemas import (
    AgentKeyCreateRequest,
    AgentKeyCreateResponse,
    AgentKeyOut,
    AgentKeyRevokeRequest,
    AgentSendRequest,
    AgentSendResponse,
)
from app.auth.service import require_session
from app.db import get_db
from app.pin import service as pin_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/keys", response_model=AgentKeyCreateResponse)
def create_key(
    body: AgentKeyCreateRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    # Issuing a money-moving credential is at least as sensitive as a send —
    # gated by the transaction PIN even though brief §6 doesn't enumerate
    # this specifically.
    pin_service.verify_pin(db, claims["sui_address"], body.pin)
    key, raw_key = service.create_key(
        db, claims["sui_address"], body.label, body.max_tx_usdc, body.daily_volume_cap_usdc
    )
    return AgentKeyCreateResponse(
        id=key.id,
        key=raw_key,
        key_prefix=key.key_prefix,
        max_tx_usdc=key.max_tx_usdc,
        daily_volume_cap_usdc=key.daily_volume_cap_usdc,
    )


@router.get("/keys", response_model=list[AgentKeyOut])
def list_keys(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return [
        AgentKeyOut(
            id=k.id,
            label=k.label,
            key_prefix=k.key_prefix,
            max_tx_usdc=k.max_tx_usdc,
            daily_volume_cap_usdc=k.daily_volume_cap_usdc,
            revoked=k.revoked,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in service.list_keys(db, claims["sui_address"])
    ]


@router.post("/keys/{key_id}/revoke")
def revoke_key(
    key_id: int,
    body: AgentKeyRevokeRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    pin_service.verify_pin(db, claims["sui_address"], body.pin)
    service.revoke_key(db, claims["sui_address"], key_id)
    return {"ok": True}


@router.post("/send", response_model=AgentSendResponse)
def send(
    body: AgentSendRequest,
    key=Depends(service.require_agent_key),
    db: Session = Depends(get_db),
):
    record = service.send(db, key, body.platform, body.handle, body.amount, body.token)
    return AgentSendResponse(
        status=record.status,
        receiver_gets=record.receiver_gets,
        claim_token=record.claim_token,
        tx_ref=record.tx_ref,
    )
