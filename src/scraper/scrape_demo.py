import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from src import settings
from src.models.book_detail import BookDetail

DEFAULT_URL = settings.SCRAPER_DEFAULT_URL



def validate_url(url: str) -> str:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "books.toscrape.com"
            or parts.username or parts.password):
        raise ValueError(settings.SCRAPER_ERROR_URL)
    return url

def parse_price(text: str) -> Decimal:
    match = re.fullmatch(r"\s*£\s*(\d+(?:,\d{3})*\.\d{2})\s*", text)
    if not match:
        raise ValueError(settings.SCRAPER_ERROR_PRICE.format(price_text=repr(text)))
    return Decimal(match.group(1).replace(",", ""))

def parse_book(html: bytes | str, url: str) -> BookDetail:
    soup = BeautifulSoup(
        html, 
        "html.parser", 
        from_encoding="utf-8" if isinstance(html, bytes) else None
    )
    checked_at = datetime.now(UTC).isoformat()
    detail = soup.select_one("div.product_main")
    if detail is None:
        raise ValueError(settings.SCRAPER_ERROR_DETAIL)

    title = detail.select_one("h1")
    price = detail.select_one(".price_color")
    stock = detail.select_one(".availability")
    if title is None or price is None or stock is None:
        raise ValueError(settings.SCRAPER_ERROR_MISSING_FIELDS)

    name = title.get_text(strip=True)
    availability = " ".join(stock.stripped_strings)
    if not name or not availability:
        raise ValueError(settings.SCRAPER_ERROR_EMPTY_FIELDS)

    return BookDetail(
        title=name,
        price=parse_price(price.get_text(strip=True)),
        currency="GBP",
        availability=availability,
        url=validate_url(url),
        checked_at=checked_at,
    )

def scrape_book(url: str = DEFAULT_URL) -> BookDetail:
    validate_url(url)
    for _ in range(settings.SCRAPER_MAX_REQUESTS):
        response = requests.get(
            url,
            timeout=settings.HTTP_TIMEOUT,
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            allow_redirects=False,
        )
        if response.is_redirect:
            new_address = response.headers["Location"]
            new_url = urljoin(url, new_address)
            url = validate_url(new_url)
            continue
        response.raise_for_status()
        return parse_book(response.content, url)
    raise ValueError(settings.SCRAPER_ERROR_REDIRECTS)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    args = parser.parse_args()
    try:
        book = scrape_book(args.url)
    except (requests.RequestException, ValueError) as exc:
        print(f"Scrape failed: {exc}", file=sys.stderr)
        return 1
    # asdict chuyen dataclass thanh dict de co the chuyen sang JSON.
    book_dict = asdict(book)
    # json.dumps chuyen dict thanh JSON string.
    json_text = json.dumps(book_dict, ensure_ascii=True, indent=2, default=str)
    print(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())