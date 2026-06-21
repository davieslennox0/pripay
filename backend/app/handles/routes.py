from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_session
from app.db import get_db
from app.handles import service
from app.handles.schemas import (
    BindEmailConfirmRequest,
    BindEmailStartRequest,
    BoundHandleOut,
    SearchResult,
    UnbindRequest,
)

router = APIRouter(prefix="/handles", tags=["handles"])


@router.post("/email/start")
def start_email_bind(
    body: BindEmailStartRequest,
    claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    service.start_email_bind(db, claims["sui_address"], body.email)
    return {"ok": True}


@router.post("/email/confirm", response_model=BoundHandleOut)
def confirm_email_bind(body: BindEmailConfirmRequest, db: Session = Depends(get_db)):
    bound = service.confirm_email_bind(db, body.token)
    return BoundHandleOut(
        platform=bound.platform, handle=bound.handle_display, verified_at=bound.verified_at
    )


@router.post("/unbind")
def unbind(
    body: UnbindRequest, claims: dict = Depends(require_session), db: Session = Depends(get_db)
):
    service.unbind_handle(db, claims["sui_address"], body.platform, body.handle, body.pin)
    return {"ok": True}


@router.get("/mine", response_model=list[BoundHandleOut])
def list_mine(claims: dict = Depends(require_session), db: Session = Depends(get_db)):
    return [
        BoundHandleOut(platform=h.platform, handle=h.handle_display, verified_at=h.verified_at)
        for h in service.list_handles(db, claims["sui_address"])
    ]


@router.get("/search", response_model=list[SearchResult])
def search(
    platform: str,
    query: str,
    _claims: dict = Depends(require_session),
    db: Session = Depends(get_db),
):
    return [
        SearchResult(platform=h.platform, handle=h.handle_display, sui_address=h.sui_address)
        for h in service.search_handles(db, platform, query)
    ]
