import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src import settings
from src.utils.time_format import format_rate_time
from src.exceptions.rate_error import RateError
from src.models.product_request import ProductRequest
from src.providers.allratestoday import get_rate
from src.scraper.scrape_demo import scrape_book

logger = logging.getLogger(__name__)




def parse_product_url(text: str) -> str:
    """Accept exactly one plain URL; this does not verify page existence."""
    url = text.strip()
    if not url or len(url) > settings.BOT_MAX_URL_LENGTH or any(char.isspace() for char in url):
        raise ValueError(settings.BOT_MSG_INVALID_URL)
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "books.toscrape.com":
        raise ValueError(settings.BOT_MSG_UNSUPPORTED_SITE)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(settings.BOT_MSG_HELP.format(default_url=settings.SCRAPER_DEFAULT_URL), disable_web_page_preview=True)


async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    message = update.effective_message
    try:
        url = parse_product_url(text)
    except ValueError as exc:
        await message.reply_text(str(exc), disable_web_page_preview=True)
        return
    request = ProductRequest(
        user_id=update.effective_user.id,
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
        url=url,
        received_at=datetime.now(UTC).isoformat(),
    )
    # One request per user in RAM; replace this with a service/storage later.
    context.user_data["last_request"] = asdict(request)
    await message.reply_text(settings.BOT_MSG_LOADING_BOOK)
    try:
        # requests is synchronous: run it in a worker thread, outside the event loop.
        book = await asyncio.to_thread(scrape_book, url)
    except requests.Timeout:
        await message.reply_text(settings.BOT_MSG_BOOK_TIMEOUT)
        return
    except requests.RequestException:
        await message.reply_text(settings.BOT_MSG_BOOK_NETWORK)
        return
    except ValueError:
        await message.reply_text(
            settings.BOT_MSG_BOOK_INVALID
        )
        return

    result = settings.BOT_MSG_BOOK_RESULT.format(
        title=book.title[:settings.BOT_TITLE_MAX_LENGTH],
        price=f"{book.price:.2f}", currency=book.currency,
        availability=book.availability[:settings.BOT_STOCK_MAX_LENGTH],
        checked_at=book.checked_at, url=book.url[:settings.BOT_MAX_URL_LENGTH],
    )
    await message.reply_text(result, disable_web_page_preview=True)



async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if len(context.args) != 2:
        await message.reply_text(settings.BOT_MSG_RATE_USAGE)
        return
    try:
        rate = await asyncio.to_thread(get_rate, context.args[0], context.args[1])
    except RateError as exc:
        await message.reply_text(str(exc))
        return
    await message.reply_text(settings.BOT_MSG_RATE_RESULT.format(
        source=rate.source, rate=f"{rate.rate:,f}", target=rate.target,
        observed_at=format_rate_time(rate.observed_at),
    ))



async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.effective_message.reply_text(settings.BOT_MSG_ADD_USAGE)
        return
    await receive_url(update, context, context.args[0])


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await receive_url(update, context, update.effective_message.text)


async def unsupported_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(settings.BOT_MSG_UNSUPPORTED_MESSAGE)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(settings.BOT_MSG_UNKNOWN_COMMAND)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Avoid logging request URLs/exceptions that may contain the bot token.
    logger.error("Telegram handler failed: %s", type(context.error).__name__)


def build_application(token: str) -> Application:
    #Tạo bộ cấu hình ứng dụng Telegram Bot với token và các handler cho các lệnh và tin nhắn.
    builder = Application.builder().token(token)
    app = builder.build()

    #Chỉ nhận tin nhắn từ chat riêng tư (private chat) với bot.
    private = filters.ChatType.PRIVATE

    #CommadHandler nhận diện các lệnh bắt đầu bằng dấu /
    #Khai báo các lệnh commandhandler thì ko dùng dấu / trong tên lệnh, ví dụ "start" thay vì "/start".
    app.add_handler(CommandHandler(["start", "help"], help_command, filters=private))
    app.add_handler(CommandHandler("add", add_command, filters=private))
    app.add_handler(CommandHandler("rate", rate_command, filters=private))

    #MessageHandler nhận tin nhắn văn bản hoặc các loại khác.
    app.add_handler(MessageHandler(private & filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(MessageHandler(private & ~filters.TEXT, unsupported_message))
    app.add_error_handler(on_error)
    return app


def main() -> int:
    token = settings.telegram_token()
    if not token:
        print("Thiếu TELEGRAM_BOT_TOKEN. Hãy thêm token vào .env ở thư mục gốc dự án.")
        return 1
    #cấu hình logging để hiển thị cảnh báo và lỗi từ thư viện httpx và các phần khác của bot.
    logging.basicConfig(level=settings.LOG_LEVEL)
    logging.getLogger("httpx").setLevel(settings.HTTPX_LOG_LEVEL)
    try:
        #Tạo ứng dụng bot và bắt đầu nhận tin nhắn từ người dùng.
        app = build_application(token)
        print("Bot đang chạy. Nhấn Ctrl+C để dừng.")
        app.run_polling(allowed_updates=["message"], bootstrap_retries=settings.BOT_BOOTSTRAP_RETRIES)
    except Exception as exc:
        print(f"Không chạy được bot ({type(exc).__name__}). Kiểm tra token, mạng và bot có đang chạy nơi khác không.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
