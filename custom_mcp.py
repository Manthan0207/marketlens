import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import requests
from analytics import calculate_metrics

mcp = FastMCP("stock-watch")


load_dotenv(Path(__file__).with_name(".env"))

WATCHLIST_PATH = Path(__file__).with_name("watchlist.json")
Period = Literal["1d", "5d", "1mo", "3mo", "6mo", "1y"]


@mcp.resource("resource://watchlist", mime_type="application/json")
def watchlist() -> dict:
    """User's monitored stocks (yfinance tickers, e.g. AVANTEL.NS)."""
    try:
        result = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Expected object")
        for key in ("stocks", "unresolved_names"):
            values = result.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError("Expected list of names")
        return result
    except (OSError, ValueError):
        return {"error": "Unable to read watchlist.json. Check that it contains valid JSON."}


@mcp.tool(name="get_watchlist")
def get_watchlist() -> dict:
    """Read monitored tickers and unresolved names requiring user clarification."""
    return watchlist()


@mcp.tool(name="get_stock_data")
def get_stock_data(symbol: str, period: Period = "1mo") -> dict:
    """Get company info and price history for a ticker like AVANTEL.NS."""
    symbol = symbol.strip().upper()
    if not symbol:
        return {"error": "Please provide a ticker."}
    if period not in ("1d", "5d", "1mo", "3mo", "6mo", "1y"):
        return {"error": "Unsupported history period."}
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, auto_adjust=True, timeout=20)
    except Exception:
        return {"error": f"Price data is unavailable for '{symbol}'. Try again later."}
    if hist.empty:
        return {"error": f"No data for '{symbol}'. Check the ticker and exchange suffix."}

    try:
        info = ticker.info or {}
        if not isinstance(info, dict):
            info = {}
    except Exception:
        info = {}

    try:
        hist = hist.reset_index()
        hist["Date"] = hist["Date"].dt.strftime("%Y-%m-%d")
        records = hist[["Date", "Open", "High", "Low", "Close", "Volume"]].to_dict("records")
        json.dumps(records, allow_nan=False)
        metrics = calculate_metrics(records)
    except (ValueError, TypeError, KeyError, AttributeError):
        return {"error": "Provider returned invalid price data."}

    return {
        "symbol": symbol,
        "shortname": info.get("shortName"),
        "sector": info.get("sector"),
        "currency": info.get("currency"),
        "period": period,
        "auto_adjusted": True,
        "source": "Yahoo Finance via yfinance",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "data": records,
    }

@mcp.tool(name="get_stock_news")
def get_news(stock_name: str) -> dict:
    """Search stock news; returns articles with source links when available."""
    stock_name = stock_name.strip()
    if not stock_name:
        return {"error": "Please provide a stock name."}
    key = os.getenv("SERPER_API_KEY")
    if not key:
        return {"error": "Set SERPER_API_KEY to enable news search."}
    try:
        response = requests.post("https://google.serper.dev/news", headers={"X-API-KEY": key},
                                 json={"q": stock_name, "num": 5}, timeout=20)
        response.raise_for_status()
        results = response.json()
        if not isinstance(results, dict) or not isinstance(results.get("news", []), list):
            raise ValueError("Invalid news response")
    except (requests.RequestException, ValueError):
        return {"error": "News search unavailable. Check SERPER_API_KEY and connectivity."}
    return {"success": True, "source": "Serper", "news": results.get("news", []),
            "retrieved_at": datetime.now(timezone.utc).isoformat()}


@mcp.tool()
def compare_stocks(symbols: list[str], period: Period = "1mo") -> dict:
    """Compare two to five stocks on overlapping trading dates in local currencies."""
    if not 2 <= len(symbols) <= 5:
        return {"error": "Provide two to five tickers."}
    results = [get_stock_data(symbol, period) for symbol in symbols]
    valid = [result for result in results if "error" not in result]
    dates = set.intersection(*(set(row["Date"] for row in result["data"]) for result in valid)) if valid else set()
    comparisons = []
    for symbol, result in zip(symbols, results):
        if "error" in result:
            comparisons.append({"symbol": symbol, **result})
        elif len(dates) < 2:
            comparisons.append({"symbol": symbol, "error": "Insufficient overlapping trading dates."})
        else:
            comparisons.append({"symbol": result["symbol"], "currency": result["currency"],
                                **calculate_metrics([row for row in result["data"] if row["Date"] in dates])})
    return {"comparisons": comparisons, "period": period,
            "method": "Overlapping trading dates; local-currency returns without FX conversion."}
    


if __name__ == "__main__":
    mcp.run()
