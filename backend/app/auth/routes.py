from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.schemas import (
    GoogleVerifyRequest,
    GoogleVerifyResponse,
    MeResponse,
    SessionRequest,
    SessionResponse,
)
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/verify", response_model=GoogleVerifyResponse)
def verify_google(body: GoogleVerifyRequest, db: Session = Depends(get_db)):
    """Step 1 of login: verify the Google ID token the frontend obtained via
    Google Identity Services, and return the zkLogin salt for this user.

    The frontend uses this salt + the ID token + its ephemeral keypair to
    derive the zkLogin Sui address and request a ZK proof — that happens
    client-side / via the prover service, not here.
    """
    google_sub = service.verify_google_id_token(body.id_token)
    salt = service.get_or_create_salt(db, google_sub)
    return GoogleVerifyResponse(google_sub=google_sub, salt=salt)


@router.post("/session", response_model=SessionResponse)
def create_session(body: SessionRequest, response: Response, db: Session = Depends(get_db)):
    """Step 2 of login: once the frontend has derived its zkLogin Sui
    address (using the salt from /google/verify), bind it and issue an
    Umbra session cookie for subsequent API calls."""
    service.bind_sui_address(db, body.google_sub, body.sui_address)
    token = service.create_session_token(body.google_sub, body.sui_address)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_ttl_minutes * 60,
    )
    return SessionResponse(sui_address=body.sui_address)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(claims: dict = Depends(service.require_session)):
    return MeResponse(google_sub=claims["sub"], sui_address=claims["sui_address"])
