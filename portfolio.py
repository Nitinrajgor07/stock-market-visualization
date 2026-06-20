"""
Portfolio Tracker — tracks multiple stock holdings, calculates P&L,
current value, allocation, and daily change.
"""
import pandas as pd
import numpy as np


DEFAULT_PORTFOLIO = [
    {"ticker": "AAPL",  "shares": 10, "buy_price": 175.0},
    {"ticker": "MSFT",  "shares":  5, "buy_price": 380.0},
    {"ticker": "NVDA",  "shares":  3, "buy_price": 480.0},
    {"ticker": "GOOGL", "shares":  4, "buy_price": 140.0},
]


def build_portfolio_summary(holdings: list[dict], price_map: dict) -> pd.DataFrame:
    """
    holdings: [{"ticker": "AAPL", "shares": 10, "buy_price": 175.0}, ...]
    price_map: {"AAPL": <current_price>, ...}
    Returns a DataFrame with one row per holding.
    """
    rows = []
    for h in holdings:
        ticker     = h["ticker"]
        shares     = h["shares"]
        buy_price  = h["buy_price"]
        cur_price  = price_map.get(ticker, buy_price)
        invested   = shares * buy_price
        cur_value  = shares * cur_price
        pnl        = cur_value - invested
        pnl_pct    = (pnl / invested) * 100 if invested else 0
        rows.append({
            "Ticker":       ticker,
            "Shares":       shares,
            "Buy Price":    round(buy_price, 2),
            "Current Price":round(cur_price, 2),
            "Invested":     round(invested, 2),
            "Current Value":round(cur_value, 2),
            "P&L ($)":      round(pnl, 2),
            "P&L (%)":      round(pnl_pct, 2),
        })
    return pd.DataFrame(rows)


def build_portfolio_history(holdings: list[dict], data_map: dict) -> pd.DataFrame:
    """
    Builds a combined daily portfolio value DataFrame across all holdings.
    data_map: {ticker: df_with_Date_and_Close}
    """
    combined = None
    for h in holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        df = data_map.get(ticker)
        if df is None or df.empty:
            continue
        tmp = df[["Date", "Close"]].copy()
        tmp["Value"] = tmp["Close"] * shares
        tmp["Stock"] = ticker
        combined = tmp if combined is None else pd.concat([combined, tmp], ignore_index=True)

    if combined is None or combined.empty:
        return pd.DataFrame()

    total = (combined.groupby("Date")["Value"]
             .sum().reset_index()
             .rename(columns={"Value": "Total Value"}))
    return total
