import math
import unittest
from unittest.mock import patch
from analytics import calculate_metrics
from custom_mcp import compare_stocks


def rows(prices, start=1):
    return [{"Date": f"2026-01-{i:02}", "Close": price} for i, price in enumerate(prices, start)]


class AnalyticsTests(unittest.TestCase):
    def test_known_return_drawdown_and_volatility(self):
        metrics = calculate_metrics(rows([100, 120, 90, 108]))
        self.assertAlmostEqual(metrics["return_pct"], 8)
        self.assertAlmostEqual(metrics["max_drawdown_pct"], -25)
        self.assertAlmostEqual(metrics["annualized_volatility_pct"], math.sqrt(0.0675) * math.sqrt(252) * 100, places=3)

    def test_one_observation_has_no_volatility(self):
        metrics = calculate_metrics(rows([100]))
        self.assertEqual(metrics["return_pct"], 0)
        self.assertIsNone(metrics["annualized_volatility_pct"])
        self.assertIsNone(metrics["sma_20"])

    def test_sma_requires_twenty_observations(self):
        self.assertEqual(calculate_metrics(rows(list(range(1, 21))))["sma_20"], 10.5)

    def test_invalid_prices_rejected(self):
        for values in ([], [0], [-1], [float("nan")], [float("inf")]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                calculate_metrics(rows(values))

    def test_comparison_aligns_dates(self):
        data = [{"symbol": "A", "currency": "USD", "data": rows([100, 110, 121])},
                {"symbol": "B", "currency": "USD", "data": rows([100, 120], start=2)}]
        with patch("custom_mcp.get_stock_data", side_effect=data):
            result = compare_stocks(["A", "B"])
        self.assertEqual(result["comparisons"][0]["return_pct"], 10)
        self.assertEqual(result["comparisons"][1]["return_pct"], 20)
        self.assertEqual(result["comparisons"][0]["start_date"], "2026-01-02")

    def test_comparison_reports_partial_failure(self):
        data = [{"symbol": "A", "currency": "USD", "data": rows([100, 110])}, {"error": "No data"}]
        with patch("custom_mcp.get_stock_data", side_effect=data):
            result = compare_stocks(["A", "B"])
        self.assertEqual(result["comparisons"][1]["error"], "No data")
