"""Load runtime configuration from the repository .env; OS environment wins."""
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)


def positive_number(name: str, default: str) -> float:
    try:
        value = float(os.getenv(name, default))
        if not math.isfinite(value) or value <= 0:
            raise ValueError()
        return value
    except ValueError:
        raise ValueError(f"{name} phải là số dương hữu hạn.") from None


def integer(name: str, default: str, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, default))
        if value < minimum:
            raise ValueError()
        return value
    except ValueError:
        raise ValueError(f"{name} phải là số nguyên >= {minimum}.") from None


def log_level(name: str) -> str:
    value = os.getenv(name, "WARNING").strip().upper()
    if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError(f"{name} không hợp lệ.")
    return value


def telegram_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def rates_api_key() -> str:
    return os.getenv("ALLRATESTODAY_API_KEY", "").strip()


HTTP_TIMEOUT = (
    positive_number("HTTP_CONNECT_TIMEOUT", "10"),
    positive_number("HTTP_READ_TIMEOUT", "30"),
)
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "PriceTrackerLearning/0.1")
SCRAPER_MAX_REQUESTS = integer("SCRAPER_MAX_REQUESTS", "6")
SCRAPER_DEFAULT_URL = os.getenv("SCRAPER_DEFAULT_URL", "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")
ALLRATESTODAY_BASE_URL = os.getenv("ALLRATESTODAY_BASE_URL", "https://allratestoday.com").rstrip("/")
api_url = urlsplit(ALLRATESTODAY_BASE_URL)
if api_url.scheme != "https" or not api_url.netloc or api_url.username or api_url.password or api_url.query or api_url.fragment:
    raise ValueError("ALLRATESTODAY_BASE_URL phải là URL HTTPS không có thông tin đăng nhập, query hoặc fragment.")
BOT_MAX_URL_LENGTH = integer("BOT_MAX_URL_LENGTH", "2048")
BOT_TITLE_MAX_LENGTH = integer("BOT_TITLE_MAX_LENGTH", "500")
BOT_STOCK_MAX_LENGTH = integer("BOT_STOCK_MAX_LENGTH", "300")
if BOT_MAX_URL_LENGTH + BOT_TITLE_MAX_LENGTH + BOT_STOCK_MAX_LENGTH > 3300:
    raise ValueError("Tổng giới hạn URL, tên và tình trạng phải <= 3300 để vừa tin nhắn Telegram.")
BOT_BOOTSTRAP_RETRIES = integer("BOT_BOOTSTRAP_RETRIES", "0", minimum=0)
LOG_LEVEL = log_level("LOG_LEVEL")
HTTPX_LOG_LEVEL = log_level("HTTPX_LOG_LEVEL")

# User-facing rate errors; empty overrides fall back to a usable message.
RATE_ERROR_INVALID_CODE = os.getenv("RATE_ERROR_INVALID_CODE", "").strip() or 'Mã tiền phải có 3 chữ cái, ví dụ USD hoặc VND.'
RATE_ERROR_AUTH = os.getenv("RATE_ERROR_AUTH", "").strip() or 'API key tỷ giá không hợp lệ hoặc không có quyền truy cập.'
RATE_ERROR_QUOTA = os.getenv("RATE_ERROR_QUOTA", "").strip() or 'Đã hết hạn mức API tỷ giá. Hãy kiểm tra tài khoản AllRatesToday.'
RATE_ERROR_PAIR = os.getenv("RATE_ERROR_PAIR", "").strip() or 'API không chấp nhận cặp tiền này. Hãy kiểm tra mã tiền.'
RATE_ERROR_REDIRECT = os.getenv("RATE_ERROR_REDIRECT", "").strip() or 'API tỷ giá chuyển hướng ngoài dự kiến.'
RATE_ERROR_TIMEOUT = os.getenv("RATE_ERROR_TIMEOUT", "").strip() or 'API tỷ giá phản hồi quá lâu. Hãy thử lại sau.'
RATE_ERROR_NETWORK = os.getenv("RATE_ERROR_NETWORK", "").strip() or 'Không kết nối được API tỷ giá. Hãy thử lại sau.'
RATE_ERROR_JSON = os.getenv("RATE_ERROR_JSON", "").strip() or 'API tỷ giá trả dữ liệu không hợp lệ.'
RATE_ERROR_SYMBOLS = os.getenv("RATE_ERROR_SYMBOLS", "").strip() or 'Không đọc được danh sách tiền tệ từ API.'
RATE_ERROR_MISSING_KEY = os.getenv("RATE_ERROR_MISSING_KEY", "").strip() or 'Chưa cấu hình ALLRATESTODAY_API_KEY cho bot.'
RATE_ERROR_UNSUPPORTED_CODE = os.getenv("RATE_ERROR_UNSUPPORTED_CODE", "").strip() or 'Mã tiền chưa được hỗ trợ. Ví dụ: USD, VND, EUR, JPY.'
RATE_ERROR_SAME_CURRENCY = os.getenv("RATE_ERROR_SAME_CURRENCY", "").strip() or 'Hãy chọn hai đồng tiền khác nhau; cùng đồng tiền thì tỷ lệ luôn là 1.'
RATE_ERROR_INVALID_RATE = os.getenv("RATE_ERROR_INVALID_RATE", "").strip() or 'API trả tỷ giá hoặc thời điểm không hợp lệ cho cặp tiền này.'


def message_template(name: str, default: str, fields: tuple[str, ...] = ()) -> str:
    """Check placeholders at startup so a typo does not break a reply later."""
    from string import Formatter
    template = os.getenv(name, "").strip() or default
    try:
        for _, field, spec, conversion in Formatter().parse(template):
            if field is not None and (field not in fields or spec or conversion):
                raise ValueError()
    except ValueError:
        raise ValueError(f"{name}: placeholder không hợp lệ; cho phép {fields}.") from None
    if len(template) > 3500:
        raise ValueError(f"{name}: nội dung quá dài.")
    return template

BOT_MSG_HELP = message_template('BOT_MSG_HELP', 'Gửi một link sách Books to Scrape hoặc /add <url>.\nVí dụ: {default_url}\n/rate USD VND — xem tỷ giá 1 USD sang VND.\n/help — xem hướng dẫn.\nBot trả tên, giá và tình trạng sách. Chưa lưu theo dõi lâu dài.', ('default_url',))

BOT_MSG_INVALID_URL = message_template('BOT_MSG_INVALID_URL', 'Hãy gửi đúng một URL, không kèm nội dung khác.', ())

BOT_MSG_UNSUPPORTED_SITE = message_template('BOT_MSG_UNSUPPORTED_SITE', 'Hiện chỉ hỗ trợ https://books.toscrape.com/.', ())

BOT_MSG_LOADING_BOOK = message_template('BOT_MSG_LOADING_BOOK', 'Đang lấy thông tin sách, bạn chờ một chút nhé.', ())

BOT_MSG_BOOK_TIMEOUT = message_template('BOT_MSG_BOOK_TIMEOUT', 'Trang phản hồi quá lâu. Bạn thử lại sau nhé.', ())

BOT_MSG_BOOK_NETWORK = message_template('BOT_MSG_BOOK_NETWORK', 'Không tải được trang sách. Hãy kiểm tra link hoặc thử lại sau.', ())

BOT_MSG_BOOK_INVALID = message_template('BOT_MSG_BOOK_INVALID', 'Không đọc được thông tin sách. Hãy gửi link trang chi tiết một cuốn sách; trang danh sách không được hỗ trợ.', ())

BOT_MSG_BOOK_RESULT = message_template('BOT_MSG_BOOK_RESULT', 'Tên sách: {title}\nGiá: {price} {currency}\nTình trạng: {availability}\nThời điểm kiểm tra (UTC): {checked_at}\nLink: {url}\n\nĐây là kết quả kiểm tra hiện tại, chưa lưu theo dõi giá.', ('title', 'price', 'currency', 'availability', 'checked_at', 'url'))

BOT_MSG_RATE_USAGE = message_template('BOT_MSG_RATE_USAGE', 'Cú pháp: /rate USD VND — tra tỷ giá của 1 đơn vị tiền nguồn.', ())

BOT_MSG_RATE_RESULT = message_template('BOT_MSG_RATE_RESULT', '1 {source} = {rate} {target}\nThời điểm dữ liệu: {observed_at}\nNguồn: AllRatesToday — tỷ giá tham khảo mid-market.', ('source', 'rate', 'target', 'observed_at'))

BOT_MSG_ADD_USAGE = message_template('BOT_MSG_ADD_USAGE', 'Cú pháp: /add <url>', ())

BOT_MSG_UNSUPPORTED_MESSAGE = message_template('BOT_MSG_UNSUPPORTED_MESSAGE', 'Hãy gửi URL bằng tin nhắn văn bản. Gõ /help để xem hướng dẫn.', ())

BOT_MSG_UNKNOWN_COMMAND = message_template('BOT_MSG_UNKNOWN_COMMAND', 'Lệnh chưa được hỗ trợ. Gõ /help để xem hướng dẫn.', ())

# Scraper validation errors
SCRAPER_ERROR_URL = message_template('SCRAPER_ERROR_URL', 'Chi ho tro URL https://books.toscrape.com/.', ())
SCRAPER_ERROR_PRICE = message_template('SCRAPER_ERROR_PRICE', 'Gia khong hop le: {price_text}', ('price_text',))
SCRAPER_ERROR_DETAIL = message_template('SCRAPER_ERROR_DETAIL', 'Khong tim thay chi tiet san pham. Hay cung cap link mot cuon sach.', ())
SCRAPER_ERROR_MISSING_FIELDS = message_template('SCRAPER_ERROR_MISSING_FIELDS', 'San pham thieu ten, gia hoac tinh trang hang.', ())
SCRAPER_ERROR_EMPTY_FIELDS = message_template('SCRAPER_ERROR_EMPTY_FIELDS', 'Ten hoac tinh trang hang bi rong.', ())
SCRAPER_ERROR_REDIRECTS = message_template('SCRAPER_ERROR_REDIRECTS', 'Qua nhieu chuyen huong URL.', ())


# IANA time zone used for exchange-rate replies.
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
DISPLAY_TIMEZONE = os.getenv("DISPLAY_TIMEZONE", "Asia/Ho_Chi_Minh").strip()
try:
    DISPLAY_ZONE = ZoneInfo(DISPLAY_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):
    raise ValueError("DISPLAY_TIMEZONE không hợp lệ hoặc thiếu thư viện tzdata.") from None
