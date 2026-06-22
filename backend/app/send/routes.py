from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.db import get_db
from app.send import service
from app.send.schemas import (
    ClaimRequest,
    SendExecuteRequest,
    SendExecuteResponse,
    SendQuoteRequest,
    SendQuoteResponse,
    SendRecordOut,
)

router = APIRouter(prefix="/send", tags=["send"])


@router.post("/quote", response_model=SendQuoteResponse)
def quote(
    body: SendQuoteRequest, _claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    is_bound, fee, receiver_gets = service.quote(db, body.platform, body.handle, body.amount)
    return SendQuoteResponse(is_bound=is_bound, fee=fee, receiver_gets=receiver_gets)


@router.post("/execute", response_model=SendExecuteResponse)
def execute(
    body: SendExecuteRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = service.execute(
        db, claims["sui_address"], body.platform, body.handle, body.amount, body.pin
    )
    return SendExecuteResponse(
        status=record.status,
        receiver_gets=record.receiver_gets,
        claim_token=record.claim_token,
        tx_ref=record.tx_ref,
        tee_provider=record.tee_provider,
        tee_attestation=record.tee_attestation,
    )


@router.post("/claim")
def claim(
    body: ClaimRequest, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    record = service.claim(db, body.claim_token, claims["sui_address"])
    return {"ok": True, "amount": record.receiver_gets}


@router.get("/mine", response_model=list[SendRecordOut])
def list_mine(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return [
        SendRecordOut(
            recipient_platform=r.recipient_platform,
            recipient_handle=r.recipient_handle,
            amount=r.amount,
            fee=r.fee,
            receiver_gets=r.receiver_gets,
            status=r.status,
            created_at=r.created_at,
        )
        for r in service.list_sent(db, claims["sui_address"])
    ]
