from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class Signal:
    action: str           # "buy", "sell", or "hold"
    confidence: float     # 0.0 to 1.0
    stop_loss: float      # Price for stop-loss
    take_profit: Optional[float] = None  # Price for take-profit (if applicable)
    reason: str = ""      # Human-readable reason


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """Analyze the DataFrame and return a trading signal."""
        pass
