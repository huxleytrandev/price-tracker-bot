import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src import settings
from src.utils.time_format import format_rate_time


class TimeFormatTests(unittest.TestCase):
    def test_vietnam_rolls_over_to_next_day(self):
        with patch.object(settings, "DISPLAY_ZONE", ZoneInfo("Asia/Ho_Chi_Minh")), patch.object(settings, "DISPLAY_TIMEZONE", "Asia/Ho_Chi_Minh"):
            self.assertEqual(format_rate_time("2026-10-13T20:11:01+0000"), "14/10/2026 03:11:01 (Asia/Ho_Chi_Minh, UTC+07:00)")

    def test_utc(self):
        with patch.object(settings, "DISPLAY_ZONE", ZoneInfo("UTC")), patch.object(settings, "DISPLAY_TIMEZONE", "UTC"):
            self.assertEqual(format_rate_time("2026-10-13T20:11:01Z"), "13/10/2026 20:11:01 (UTC, UTC+00:00)")

    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            format_rate_time("2026-10-13T20:11:01")
