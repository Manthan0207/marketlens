"""StockScope: local research dashboard with an offline demonstration mode."""
import asyncio
import os
import uuid

import pandas as pd
import streamlit as st

from custom_mcp import get_stock_data, compare_stocks, watchlist
from demo import demo_stock, demo_report
from research import ask, history

st.set_page_config(page_title="StockScope | Research workspace", page_icon="📈", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def prices(symbol, period):
    return get_stock_data(symbol, period)


@st.cache_data(ttl=300, show_spinner=False)
def comparisons(symbols, period):
    return compare_stocks(symbols, period)


with st.sidebar:
    st.title("StockScope")
    st.caption("A stock research workspace")
    mode = st.radio("Data mode", ["Offline demo", "Live research"])
    st.divider()
    monitored = watchlist()
    st.subheader("Watchlist")
    for ticker in monitored.get("stocks", []):
        st.write(ticker)
    for name in monitored.get("unresolved_names", []):
        st.caption(f"Needs ticker confirmation: {name}")
    if "error" in monitored:
        st.warning(monitored["error"])
    st.divider()
    st.caption("Local research tool. Prices may be delayed. No trade execution.")

st.title("Evidence before opinion.")
st.write("Explore price history, compare performance, and ask questions backed by research tools.")
demo = mode == "Offline demo"
if demo:
    st.info("Offline demo · All prices below are synthetic. No API calls or credentials are used.")

overview, compare, chat = st.tabs(["Market overview", "Compare stocks", "Research assistant"])

with overview:
    if demo:
        stock = demo_stock()
    else:
        with st.form("lookup"):
            symbol = st.text_input("Yahoo Finance ticker", "AVANTEL.NS")
            period = st.selectbox("History period", ["1mo", "3mo", "6mo", "1y", "5d", "1d"])
            submitted = st.form_submit_button("Load market data", type="primary")
        if submitted:
            with st.spinner("Fetching price history…"):
                st.session_state["stock"] = prices(symbol.strip().upper(), period)
        stock = st.session_state.get("stock")
    if stock and "error" in stock:
        st.error(stock["error"])
    elif stock:
        st.subheader(f"{stock['shortname'] or stock['symbol']} · {stock['symbol']}")
        m = stock["metrics"]
        columns = st.columns(4)
        columns[0].metric("Last adjusted close" if stock["auto_adjusted"] else "Last close", f"{m['last_close']:.2f}")
        columns[1].metric("Observed return", f"{m['return_pct']:+.2f}%")
        columns[2].metric("Maximum drawdown", f"{m['max_drawdown_pct']:.2f}%")
        volatility = m["annualized_volatility_pct"]
        columns[3].metric("Annualized volatility", f"{volatility:.2f}%" if volatility is not None else "Insufficient data")
        frame = pd.DataFrame(stock["data"]).set_index("Date")
        st.line_chart(frame[["Close"]], height=320)
        st.bar_chart(frame[["Volume"]], height=160)
        st.caption(f"{stock['source']} · Currency: {stock['currency'] or 'unavailable'} · Retrieved: {stock['retrieved_at']}")
        st.caption(f"{m['start_date']} → {m['end_date']} · {m['observations']} observations. Returns use first and last observed closes; they may not cover the full requested calendar period.")
        with st.expander("Calculation details and price history"):
            st.write("Drawdown is the largest decline from an earlier closing-price peak. Volatility is the sample standard deviation of daily returns × √252. SMA20 requires 20 observations.")
            st.dataframe(frame, width="stretch")
        st.download_button("Download price history (CSV)", frame.to_csv(), f"{stock['symbol']}-prices.csv", "text/csv")
        if demo:
            st.download_button("Download example report", demo_report(stock), "demo-research.md", "text/markdown")

with compare:
    st.subheader("Compare on the same trading dates")
    if demo:
        fixture = demo_stock()
        base = pd.DataFrame(fixture["data"]).set_index("Date")["Close"]
        chart = pd.DataFrame({"Synthetic A": base / base.iloc[0] * 100,
                              "Synthetic B": [(100 + i * 0.12) for i in range(len(base))]}, index=base.index)
        st.line_chart(chart)
        st.caption("Synthetic series rebased to 100. Live comparisons calculate metrics from overlapping trading dates.")
    else:
        with st.form("compare"):
            tickers = st.text_input("Two to five tickers, separated by commas", "AVANTEL.NS, INFY.NS")
            compare_period = st.selectbox("Comparison period", ["1mo", "3mo", "6mo", "1y"])
            compare_submit = st.form_submit_button("Compare")
        if compare_submit:
            symbols = tuple(dict.fromkeys(s.strip().upper() for s in tickers.split(",") if s.strip()))
            with st.spinner("Comparing price histories…"):
                st.session_state["comparison"] = comparisons(symbols, compare_period)
        result = st.session_state.get("comparison")
        if result:
            if "error" in result:
                st.error(result["error"])
            else:
                st.dataframe(pd.DataFrame(result["comparisons"]), width="stretch")
                st.caption(result["method"])

with chat:
    st.subheader("Research with a visible evidence trail")
    if demo:
        st.markdown(demo_report(demo_stock()))
        st.caption("This example report is generated deterministically. Switch to Live research to use the AI assistant.")
    else:
        st.session_state.setdefault("thread", uuid.uuid4().hex)
        session = st.text_input("Session ID — reuse it to resume a conversation", st.session_state["thread"])
        if session.strip():
            st.session_state["thread"] = session.strip()
        if st.button("New conversation"):
            st.session_state["thread"] = uuid.uuid4().hex
            st.rerun()
        if not os.getenv("HF_TOKEN"):
            st.warning("Set HF_TOKEN in .env to enable the research assistant.")
        else:
            try:
                saved = asyncio.run(history(st.session_state["thread"]))
                for message in saved:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                question = st.chat_input("Ask about performance, compare stocks, or investigate news")
                if question:
                    with st.chat_message("user"):
                        st.write(question)
                    with st.spinner("Gathering evidence…"):
                        result = asyncio.run(ask(question, st.session_state["thread"]))
                    with st.chat_message("assistant"):
                        st.markdown(result["answer"])
                        st.caption(f"Completed in {result['elapsed_seconds']} seconds")
                        with st.expander("Tools used"):
                            st.json(result["trace"])
                        st.download_button("Download answer", str(result["answer"]), "research.md", "text/markdown")
            except Exception:
                st.error("Research could not complete. Check credentials, model access and connectivity; your session ID can be reused.")
