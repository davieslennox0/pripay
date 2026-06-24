"""Swap module (brief §10 + §12 step 9). `get_swap_venue()` mirrors
`app.tee.get_tee_executor()` — the venue it returns is selected by
`settings.swap_venue`, so adding Uniswap/Jupiter/THORChain later is a config
change plus a new SwapVenue implementation, not a rewrite of
app/swap/service.py."""

from functools import lru_cache

from app.config import settings
from app.swap.venue import AftermathSwapVenue, SwapVenue

_VENUES: dict[str, type[SwapVenue]] = {
    AftermathSwapVenue.name: AftermathSwapVenue,
}


@lru_cache(maxsize=1)
def get_swap_venue() -> SwapVenue:
    try:
        return _VENUES[settings.swap_venue]()
    except KeyError:
        raise ValueError(
            f"Unknown swap_venue '{settings.swap_venue}'. "
            f"Available: {', '.join(sorted(_VENUES))}"
        )


__all__ = ["get_swap_venue", "SwapVenue"]
