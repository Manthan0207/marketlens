"""Deterministic metrics from adjusted closing prices."""
import math
import statistics


def calculate_metrics(records):
    closes = [float(row["Close"]) for row in records]
    if not closes or any(not math.isfinite(x) or x <= 0 for x in closes):
        raise ValueError("Expected finite, positive closing prices.")
    returns = [b / a - 1 for a, b in zip(closes, closes[1:])]
    peak, drawdown = closes[0], 0
    for close in closes:
        peak = max(peak, close)
        drawdown = min(drawdown, close / peak - 1)
    return {"start_date": records[0]["Date"], "end_date": records[-1]["Date"],
            "observations": len(closes), "first_close": closes[0], "last_close": closes[-1],
            "return_pct": round((closes[-1] / closes[0] - 1) * 100, 4),
            "max_drawdown_pct": round(drawdown * 100, 4),
            "annualized_volatility_pct": round(statistics.stdev(returns) * math.sqrt(252) * 100, 4) if len(returns) >= 2 else None,
            "sma_20": round(statistics.mean(closes[-20:]), 4) if len(closes) >= 20 else None}
