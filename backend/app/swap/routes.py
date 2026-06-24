from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.db import get_db
from app.swap import service
from app.swap.schemas import (
    SwapExecuteRequest,
    SwapExecuteResponse,
    SwapQuoteRequest,
    SwapQuoteResponse,
    SwapRecordOut,
)

router = APIRouter(prefix="/swap", tags=["swap"])


@router.post("/quote", response_model=SwapQuoteResponse)
def quote(
    body: SwapQuoteRequest, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    quoted, route = service.quote(
        db, claims["sui_address"], body.coin_in_type, body.coin_out_type, body.amount_in
    )
    return SwapQuoteResponse(
        quote_id=quoted.id,
        amount_in=quoted.amount_in,
        amount_out=route["coinOut"]["amount"].removesuffix("n"),
        spot_price=route["spotPrice"],
        net_trade_fee_percentage=route["netTradeFeePercentage"],
    )


@router.post("/execute", response_model=SwapExecuteResponse)
def execute(
    body: SwapExecuteRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = service.execute(
        db, claims["sui_address"], body.quote_id, body.pin, body.slippage
    )
    return SwapExecuteResponse(
        status=record.status,
        tx_ref=record.tx_ref,
        tee_provider=record.tee_provider,
        tee_attestation=record.tee_attestation,
    )


@router.get("/mine", response_model=list[SwapRecordOut])
def list_mine(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return [
        SwapRecordOut(
            coin_in_type=r.coin_in_type,
            coin_out_type=r.coin_out_type,
            amount_in=r.amount_in,
            amount_out_min=r.amount_out_min,
            status=r.status,
            tx_ref=r.tx_ref,
            created_at=r.created_at,
        )
        for r in service.list_swaps(db, claims["sui_address"])
    ]
