from pydantic import BaseModel, field_validator


class PinBody(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not (4 <= len(value) <= 6) or not value.isdigit():
            raise ValueError("PIN must be 4-6 digits")
        return value


class PinStatusResponse(BaseModel):
    is_set: bool
