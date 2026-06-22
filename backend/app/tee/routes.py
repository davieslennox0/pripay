"""Exposes the active enclave's public identity (brief §4). A client/relayer
pins this measurement before sealing a request to the enclave, and the
dashboard can show which enclave a send was settled in."""

from fastapi import APIRouter

from app.config import settings
from app.tee import get_tee_executor

router = APIRouter(prefix="/tee", tags=["tee"])


@router.get("/attestation")
def attestation():
    executor = get_tee_executor()
    return {
        "provider": executor.provider,
        "enclave_measurement": settings.tee_enclave_measurement,
        # The mock is in-process and provides no real isolation — say so
        # plainly so a deployment doesn't mistake it for a hardware enclave.
        "is_mock": executor.provider == "mock",
    }
