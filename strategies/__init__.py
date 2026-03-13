from strategies.trend import TrendFollower
from strategies.mean_revert import MeanReversion
from strategies.volatility import VolatilityHandler

STRATEGY_MAP = {
    "trending": TrendFollower(),
    "sideways": MeanReversion(),
    "volatile": VolatilityHandler(),
}

def get_strategy(regime):
    """Return the appropriate strategy for the given market regime."""
    return STRATEGY_MAP.get(regime, VolatilityHandler())
