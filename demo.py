"""Synthetic, reproducible data for credential-free demonstrations."""
import math
from datetime import date, timedelta
from analytics import calculate_metrics


def demo_stock():
    records = []
    day = date(2026, 8, 3)
    while len(records) < 45:
        if day.weekday() < 5:
            i = len(records)
            close = round(100 + i * 0.35 + math.sin(i / 3) * 4, 2)
            records.append({"Date": day.isoformat(), "Open": close - 0.6,
                            "High": close + 1.2, "Low": close - 1.4,
                            "Close": close, "Volume": 100000 + i * 1700})
        day += timedelta(days=1)
    return {"symbol": "DEMO", "shortname": "Synthetic demonstration company",
            "currency": "demo units", "source": "Synthetic fixture — not market data",
            "retrieved_at": "Static demo fixture", "period": "45 trading observations",
            "auto_adjusted": False, "data": records, "metrics": calculate_metrics(records)}


def demo_report(stock):
    m = stock["metrics"]
    return (f"# Research snapshot: {stock['symbol']}\n\n"
            f"Source: {stock['source']}\n\n"
            f"Observed range: {m['start_date']} to {m['end_date']} ({m['observations']} observations).\n\n"
            f"- First close: {m['first_close']:.2f}\n"
            f"- Last close: {m['last_close']:.2f}\n"
            f"- Observed return: {m['return_pct']:.2f}%\n"
            f"- Maximum closing-price drawdown: {m['max_drawdown_pct']:.2f}%\n"
            f"- Annualized daily-return volatility: {m['annualized_volatility_pct']:.2f}%\n\n"
            "Volatility uses sample standard deviation and 252 trading days. "
            "This report uses synthetic data for demonstration; it is not investment advice.\n")
