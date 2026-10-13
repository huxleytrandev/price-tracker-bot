from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExchangeRate:
    source: str
    target: str
    rate: Decimal
    observed_at: str
