from pydantic import BaseModel


class GoogleVerifyRequest(BaseModel):
    id_token: str


class GoogleVerifyResponse(BaseModel):
    google_sub: str
    salt: str


class SessionRequest(BaseModel):
    google_sub: str
    sui_address: str


class SessionResponse(BaseModel):
    sui_address: str


class MeResponse(BaseModel):
    google_sub: str
    sui_address: str
