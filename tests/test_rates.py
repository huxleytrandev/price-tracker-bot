import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import requests

from src.bot.telegram_bot import rate_command
from src.exceptions.rate_error import RateError
from src.providers.allratestoday import get_rate, supported_currencies


class RatesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        supported_currencies.cache_clear()
        env = patch.dict(os.environ, {'ALLRATESTODAY_API_KEY': 'test-only'})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(supported_currencies.cache_clear)

    def response(self, data, status=200):
        response = Mock(status_code=status, is_redirect=False)
        response.json.return_value = data
        return response

    def test_success_and_request(self):
        rows = [{'source': 'USD', 'target': 'VND', 'rate': Decimal('25000.123456'), 'time': '2026-10-14T00:00:00Z'}]
        with patch('src.providers.allratestoday.requests.get', side_effect=[
            self.response({'currencies': [{'code': 'USD'}, {'code': 'VND'}]}), self.response(rows)
        ]) as request:
            rate = get_rate('usd', 'vnd')
            self.assertEqual(rate.rate, Decimal('25000.123456'))
            self.assertEqual(request.call_args.kwargs['params'], {'source': 'USD', 'target': 'VND'})
            self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer test-only')

    def test_missing_key(self):
        with patch.dict(os.environ, {'ALLRATESTODAY_API_KEY': ''}), self.assertRaises(RateError):
            get_rate('USD', 'VND')

    def test_errors(self):
        with patch('src.providers.allratestoday.supported_currencies', return_value={'USD', 'VND'}):
            for status in [400, 401, 403, 429]:
                with self.subTest(status=status), patch('src.providers.allratestoday.requests.get', return_value=self.response({}, status)) as request:
                    with self.assertRaises(RateError): get_rate('USD', 'VND')
                    self.assertEqual(request.call_count, 1)
            with patch('src.providers.allratestoday.requests.get', side_effect=requests.Timeout()), self.assertRaises(RateError):
                get_rate('USD', 'VND')

    def test_bad_data(self):
        with patch('src.providers.allratestoday.supported_currencies', return_value={'USD', 'VND'}):
            for data in [[], {}, [{'source':'USD','target':'EUR'}], [{'source':'USD','target':'VND','rate':'NaN','time':'bad'}]]:
                with patch('src.providers.allratestoday.get_json', return_value=data), self.assertRaises(RateError):
                    get_rate('USD', 'VND')

    async def test_handler(self):
        update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=AsyncMock()))
        context = SimpleNamespace(args=['USD','VND'])
        with patch('src.bot.telegram_bot.get_rate', return_value=SimpleNamespace(source='USD',target='VND',rate=Decimal('25000'),observed_at='2026-10-14T00:00:00Z')):
            await rate_command(update, context)
        self.assertIn('1 USD = 25,000 VND', update.effective_message.reply_text.call_args.args[0])
        with patch('src.bot.telegram_bot.get_rate', side_effect=RateError('quota')):
            await rate_command(update, context)
        self.assertEqual(update.effective_message.reply_text.call_args.args[0], 'quota')
        context.args = ['100','USD','VND']
        await rate_command(update, context)
        self.assertIn('Cú pháp', update.effective_message.reply_text.call_args.args[0])
