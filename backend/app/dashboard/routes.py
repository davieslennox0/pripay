from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.dashboard import service
from app.dashboard.schemas import (
    BalanceOut,
    HistoryDecrypted,
    HistoryItem,
    PersonalVolumeOut,
    PlatformVolumeOut,
)
from app.db import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/balances", response_model=list[BalanceOut])
def balances(claims: dict = Depends(require_session)):
    return service.get_balances(claims["sui_address"])


@router.get("/history", response_model=list[HistoryItem])
def history(
    platform: str | None = None,
    handle: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    return service.get_history(
        db, claims["sui_address"], platform, handle, since, until, limit, offset
    )


@router.get("/history/{record_id}/decrypt", response_model=HistoryDecrypted)
def decrypt(
    record_id: int, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    payload = service.decrypt_history_item(db, claims["sui_address"], record_id)
    return HistoryDecrypted(**payload)


@router.get("/volume", response_model=PersonalVolumeOut)
def volume(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return service.get_personal_volume(db, claims["sui_address"])


@router.get("/volume/platform", response_model=PlatformVolumeOut)
def platform_volume(db: Session = Depends(get_db)):
    return service.get_platform_volume(db)
