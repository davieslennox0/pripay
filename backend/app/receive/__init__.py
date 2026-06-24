"""Multi-chain receiving (brief §8 + §12 step 8). `get_aggregator()` mirrors
`app.tee.get_tee_executor()` — the aggregator it returns is selected by
`settings.receive_aggregator`, so adding deBridge/Wormhole later is a config
change plus a new BridgeAggregator implementation, not a rewrite of the
quote/status flow in app/receive/service.py."""

from functools import lru_cache

from app.config import settings
from app.receive.aggregator import BridgeAggregator, LiFiAggregator

_AGGREGATORS: dict[str, type[BridgeAggregator]] = {
    LiFiAggregator.name: LiFiAggregator,
}


@lru_cache(maxsize=1)
def get_aggregator() -> BridgeAggregator:
    try:
        return _AGGREGATORS[settings.receive_aggregator]()
    except KeyError:
        raise ValueError(
            f"Unknown receive_aggregator '{settings.receive_aggregator}'. "
            f"Available: {', '.join(sorted(_AGGREGATORS))}"
        )


__all__ = ["get_aggregator", "BridgeAggregator"]
