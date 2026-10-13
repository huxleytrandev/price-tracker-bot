import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import requests

from src.bot.telegram_bot import add_command, parse_product_url, text_message

URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


class BotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.scraper_patch = patch("src.bot.telegram_bot.scrape_book")
        self.scraper = self.scraper_patch.start()
        self.addCleanup(self.scraper_patch.stop)
        self.scraper.return_value = SimpleNamespace(
            title="Test book", price=Decimal("51.77"), currency="GBP",
            availability="In stock", url=URL, checked_at="2026-10-14T00:00:00+00:00",
        )

    async def test_scrape_errors_reply(self):
        for error, expected in [
            (requests.Timeout(), "quá lâu"),
            (requests.ConnectionError(), "Không tải được"),
            (ValueError(), "trang chi tiết"),
        ]:
            with self.subTest(error=type(error).__name__):
                self.scraper.side_effect = error
                update = self.make_update()
                await text_message(update, SimpleNamespace(user_data={}))
                self.assertIn(expected, update.effective_message.reply_text.call_args.args[0])

    def test_urls(self):
        self.assertEqual(parse_product_url("  " + URL + "#top  "), URL)
        for text in ["", "hello", URL + " " + URL, "https://example.com/", "http://books.toscrape.com/", "https://books.toscrape.com.evil.test/", "https://user@books.toscrape.com/"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_product_url(text)

    def make_update(self, text=URL, user=1):
        return SimpleNamespace(
            effective_message=SimpleNamespace(text=text, message_id=10, reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=user), effective_chat=SimpleNamespace(id=user),
        )

    async def test_text_receives_metadata(self):
        update = self.make_update()
        context = SimpleNamespace(user_data={})
        await text_message(update, context)
        self.assertEqual(context.user_data["last_request"]["url"], URL)
        self.assertEqual(context.user_data["last_request"]["user_id"], 1)
        self.assertEqual(update.effective_message.reply_text.await_count, 2)
        result = update.effective_message.reply_text.call_args.args[0]
        self.assertIn("Test book", result)
        self.assertIn("51.77 GBP", result)
        self.scraper.assert_called_once_with(URL)

    async def test_invalid_text_not_stored(self):
        context = SimpleNamespace(user_data={})
        await text_message(self.make_update("hello"), context)
        self.assertEqual(context.user_data, {})
        self.scraper.assert_not_called()

    async def test_add_argument_count(self):
        for args in [[], [URL, URL]]:
            context = SimpleNamespace(args=args, user_data={})
            await add_command(self.make_update(), context)
            self.assertEqual(context.user_data, {})

    async def test_add_and_users_isolated(self):
        contexts = [SimpleNamespace(args=[URL], user_data={}) for _ in range(2)]
        for user, context in enumerate(contexts, start=1):
            await add_command(self.make_update(user=user), context)
            self.assertEqual(context.user_data["last_request"]["user_id"], user)


if __name__ == "__main__":
    unittest.main()
