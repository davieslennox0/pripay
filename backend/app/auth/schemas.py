from pydantic import BaseModel


class NonceResponse(BaseModel):
    nonce: str


class SessionRequest(BaseModel):
    sui_address: str
    nonce: str
    signature: str


class SessionResponse(BaseModel):
    sui_address: str


class MeResponse(BaseModel):
    sui_address: str
