"""TEE execution layer (brief §4). `get_tee_executor()` is the single entry
point the rest of the app uses; it returns the executor selected by
`settings.tee_provider` so swapping the mock for real enclave infra is a
config change, not a code change."""

from functools import lru_cache

from app.config import settings
from app.tee.base import TeeExecutor
from app.tee.mock import MockTeeExecutor

_EXECUTORS: dict[str, type[TeeExecutor]] = {
    MockTeeExecutor.provider: MockTeeExecutor,
}


@lru_cache(maxsize=1)
def get_tee_executor() -> TeeExecutor:
    try:
        return _EXECUTORS[settings.tee_provider]()
    except KeyError:
        raise ValueError(
            f"Unknown tee_provider '{settings.tee_provider}'. "
            f"Available: {', '.join(sorted(_EXECUTORS))}"
        )


__all__ = ["get_tee_executor", "TeeExecutor"]
