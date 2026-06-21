from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.db import get_db
from app.pin import service
from app.pin.schemas import PinBody, PinStatusResponse

router = APIRouter(prefix="/pin", tags=["pin"])


@router.get("/status", response_model=PinStatusResponse)
def status_(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return PinStatusResponse(is_set=service.is_set(db, claims["sui_address"]))


@router.post("/set")
def set_pin(
    body: PinBody, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    service.set_pin(db, claims["sui_address"], body.pin)
    return {"ok": True}


@router.post("/verify")
def verify_pin(
    body: PinBody, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    service.verify_pin(db, claims["sui_address"], body.pin)
    return {"ok": True}
