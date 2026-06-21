from datetime import datetime

from pydantic import BaseModel, EmailStr


class BindEmailStartRequest(BaseModel):
    email: EmailStr


class BindEmailConfirmRequest(BaseModel):
    token: str


class UnbindRequest(BaseModel):
    platform: str
    handle: str
    pin: str


class BoundHandleOut(BaseModel):
    platform: str
    handle: str
    verified_at: datetime


class SearchResult(BaseModel):
    platform: str
    handle: str
    sui_address: str
