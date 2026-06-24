from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.db import get_db
from app.receive import service
from app.receive.schemas import (
    ReceiveChain,
    ReceiveQuoteRequest,
    ReceiveQuoteResponse,
    ReceiveRecordOut,
    ReceiveStatusResponse,
    ReceiveSubmitRequest,
)

router = APIRouter(prefix="/receive", tags=["receive"])


@router.get("/chains", response_model=list[ReceiveChain])
def chains():
    return service.list_chains()


@router.post("/quote", response_model=ReceiveQuoteResponse)
def quote(
    body: ReceiveQuoteRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    # to_sui_address always comes from the session, never the request body —
    # a quote only ever routes funds into the caller's own Umbra account.
    record, raw = service.quote(
        db,
        claims["sui_address"],
        body.from_chain,
        body.from_token,
        body.from_amount,
        body.from_address,
    )
    estimate = raw["estimate"]
    return ReceiveQuoteResponse(
        record_id=record.id,
        tool=raw["tool"],
        to_amount=estimate["toAmount"],
        to_amount_min=estimate["toAmountMin"],
        estimated_duration_seconds=estimate["executionDuration"],
        transaction_request=raw.get("transactionRequest"),
    )


@router.post("/{record_id}/submitted")
def submitted(
    record_id: int,
    body: ReceiveSubmitRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = service.mark_submitted(db, record_id, claims["sui_address"], body.from_tx_hash)
    return {"ok": True, "status": record.status}


@router.get("/{record_id}/status", response_model=ReceiveStatusResponse)
def record_status(
    record_id: int,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    record, raw = service.refresh_status(db, record_id, claims["sui_address"])
    return ReceiveStatusResponse(
        status=record.status,
        sub_status=raw.get("substatus"),
        sub_status_message=raw.get("substatusMessage"),
        receiving_tx_hash=record.receiving_tx_hash,
    )


@router.get("/mine", response_model=list[ReceiveRecordOut])
def list_mine(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return [
        ReceiveRecordOut(
            record_id=r.id,
            from_chain=r.from_chain,
            from_amount=r.from_amount,
            to_amount_min=r.to_amount_min,
            tool=r.tool,
            status=r.status,
            receiving_tx_hash=r.receiving_tx_hash,
        )
        for r in service.list_received(db, claims["sui_address"])
    ]
