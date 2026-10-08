import unittest
import os
import pandas as pd
from unittest.mock import patch

import custom_mcp


class StockToolTests(unittest.TestCase):
    def test_price_history_preserves_precision_and_metrics(self):
        frame = pd.DataFrame({"Open": [100.001, 109.9], "High": [101, 111],
                              "Low": [99, 109], "Close": [100.001, 110.0011], "Volume": [1000, 1200]},
                             index=pd.DatetimeIndex(["2026-01-01", "2026-01-02"], name="Date"))
        with patch.object(custom_mcp.yf, "Ticker") as ticker:
            ticker.return_value.history.return_value = frame
            ticker.return_value.info = {"currency": "INR"}
            result = custom_mcp.get_stock_data(" avantel.ns ")
        self.assertEqual(result["symbol"], "AVANTEL.NS")
        self.assertEqual(result["data"][0]["Close"], 100.001)
        self.assertEqual(result["metrics"]["return_pct"], 10)
        self.assertEqual(result["currency"], "INR")
        self.assertIn("retrieved_at", result)

    def test_malformed_watchlist_is_reported(self):
        with patch.object(custom_mcp.Path, "read_text", return_value='{"stocks": "wrong"}'):
            self.assertIn("error", custom_mcp.watchlist())

    def test_invalid_news_payload_is_reported(self):
        with patch.dict(os.environ, {"SERPER_API_KEY": "test"}), patch.object(custom_mcp.requests, "post") as request:
            request.return_value.json.return_value = {"news": "wrong"}
            self.assertIn("error", custom_mcp.get_news("Avantel"))

    def test_watchlist_read_failure_is_reported(self):
        with patch.object(custom_mcp.Path, "read_text", side_effect=OSError):
            self.assertIn("error", custom_mcp.watchlist())

    def test_blank_ticker_does_not_contact_provider(self):
        with patch.object(custom_mcp.yf, "Ticker") as ticker:
            self.assertIn("error", custom_mcp.get_stock_data("  "))
            ticker.assert_not_called()

    def test_price_provider_failure_is_reported(self):
        with patch.object(custom_mcp.yf, "Ticker") as ticker:
            ticker.return_value.history.side_effect = RuntimeError("offline")
            self.assertIn("error", custom_mcp.get_stock_data("AVANTEL.NS"))

    def test_missing_news_configuration_is_reported(self):
        with patch.dict(os.environ, {"SERPER_API_KEY": ""}):
            self.assertIn("error", custom_mcp.get_news("Avantel"))

    def test_news_preserves_source_links(self):
        article = {"title": "Example", "link": "https://example.com/news"}
        with patch.dict(os.environ, {"SERPER_API_KEY": "test"}), patch.object(custom_mcp.requests, "post") as search:
            search.return_value.json.return_value = {"news": [article]}
            self.assertEqual(custom_mcp.get_news("Avantel")["news"], [article])


if __name__ == "__main__":
    unittest.main()
