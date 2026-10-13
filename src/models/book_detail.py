from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BookDetail:
    title: str
    price: Decimal
    currency: str
    availability: str
    url: str
    checked_at: str
