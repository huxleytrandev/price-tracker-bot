import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache

import requests

from src import settings
from src.exceptions.rate_error import RateError
from src.models.exchange_rate import ExchangeRate


def currency_code(value: str) -> str:
    code = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise RateError(settings.RATE_ERROR_INVALID_CODE)
    return code


def get_json(path: str, *, params=None, key=None):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        response = requests.get(settings.ALLRATESTODAY_BASE_URL + path, params=params, headers=headers,
                                timeout=settings.HTTP_TIMEOUT, allow_redirects=False)
        if response.status_code in (401, 403):
            raise RateError(settings.RATE_ERROR_AUTH)
        if response.status_code == 429:
            raise RateError(settings.RATE_ERROR_QUOTA)
        if response.status_code == 400:
            raise RateError(settings.RATE_ERROR_PAIR)
        if response.is_redirect:
            raise RateError(settings.RATE_ERROR_REDIRECT)
        response.raise_for_status()
        return response.json(parse_float=Decimal)
    except requests.Timeout:
        raise RateError(settings.RATE_ERROR_TIMEOUT) from None
    except requests.RequestException:
        raise RateError(settings.RATE_ERROR_NETWORK) from None
    except ValueError:
        raise RateError(settings.RATE_ERROR_JSON) from None


@lru_cache(maxsize=1)
def supported_currencies() -> frozenset[str]:
    # Cache the public list for this process; invalid input won't spend rate quota.
    data = get_json("/api/v1/symbols")
    try:
        codes = frozenset(currency_code(item["code"]) for item in data["currencies"])
        if not codes:
            raise ValueError()
        return codes
    except (KeyError, TypeError, ValueError):
        raise RateError(settings.RATE_ERROR_SYMBOLS) from None


def get_rate(source: str, target: str) -> ExchangeRate:
    source, target = currency_code(source), currency_code(target)
    key = settings.rates_api_key()
    if not key:
        raise RateError(settings.RATE_ERROR_MISSING_KEY)
    codes = supported_currencies()
    if source not in codes or target not in codes:
        raise RateError(settings.RATE_ERROR_UNSUPPORTED_CODE)
    if source == target:
        raise RateError(settings.RATE_ERROR_SAME_CURRENCY)
    data = get_json("/api/v1/rates", params={"source": source, "target": target}, key=key)
    try:
        if not isinstance(data, list) or len(data) != 1:
            raise ValueError()
        row = data[0]
        if row["source"] != source or row["target"] != target:
            raise ValueError()
        value = Decimal(str(row["rate"]))
        if not value.is_finite() or value <= 0:
            raise ValueError()
        timestamp = row["time"]
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError()
        return ExchangeRate(source, target, value, timestamp)
    except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation):
        raise RateError(settings.RATE_ERROR_INVALID_RATE) from None
