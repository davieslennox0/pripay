from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.schemas import MeResponse, NonceResponse, SessionRequest, SessionResponse
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/nonce", response_model=NonceResponse)
def get_nonce(db: Session = Depends(get_db)):
    """Step 1 of login: a one-time challenge the frontend asks the connected
    Sui wallet (Slush or any Wallet-Standard wallet) to sign, proving control
    of the address before a session is issued."""
    return NonceResponse(nonce=service.create_nonce(db))


@router.post("/session", response_model=SessionResponse)
def create_session(body: SessionRequest, response: Response, db: Session = Depends(get_db)):
    """Step 2 of login: verify the wallet's signature over the nonce from
    /auth/nonce and, if valid, issue an Umbra session cookie."""
    service.consume_nonce(db, body.nonce)
    message = service.signin_message(body.nonce)
    if not service.verify_wallet_signature(message, body.signature, body.sui_address):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid wallet signature")

    token = service.create_session_token(body.sui_address)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=settings.session_ttl_minutes * 60,
    )
    return SessionResponse(sui_address=body.sui_address)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(claims: dict = Depends(service.require_session)):
    return MeResponse(sui_address=claims["sui_address"])
