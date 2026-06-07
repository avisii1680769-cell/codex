import json
import os
import tempfile
import unittest
from unittest import mock

from rustchain_telegram_bot.formatting import fmt_balance, fmt_epoch, fmt_health, fmt_miners
from rustchain_telegram_bot.price import get_wrtc_price


class FormattingTests(unittest.TestCase):
    def test_health(self):
        self.assertIn("ok", fmt_health({"status": "ok", "version": "1.2"}))

    def test_miners(self):
        text = fmt_miners([{"miner_id": "m1"}, {"miner_id": "m2"}])
        self.assertIn("Active miners: 2", text)
        self.assertIn("m1", text)

    def test_epoch(self):
        text = fmt_epoch({"epoch": 7, "block_height": 99, "reward": 1.5}, "https://explorer")
        self.assertIn("Epoch: 7", text)
        self.assertIn("https://explorer", text)

    def test_balance(self):
        self.assertIn("12.5", fmt_balance("alice", {"balance": 12.5}))


class PriceTests(unittest.TestCase):
    def test_unconfigured_price(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            result = get_wrtc_price()
        self.assertFalse(result.available)
        self.assertIn("not configured", result.text)

    def test_dot_path(self):
        payload = json.dumps({"data": {"price": "0.123"}}).encode()
        class FakeResp:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                return payload
        with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
            with mock.patch.dict(os.environ, {"WRTC_PRICE_API_URL": "https://example.test", "WRTC_PRICE_JSON_PATH": "data.price"}):
                result = get_wrtc_price()
        self.assertTrue(result.available)
        self.assertEqual(result.value, 0.123)


if __name__ == "__main__":
    unittest.main()
