import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, start_date, end_date) -> pd.DataFrame:
    try:
        df = yf.download(ticker, start=start_date, end=end_date,
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        df.reset_index(inplace=True)
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if col[1] == "" else col[0]
                          for col in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def fetch_company_info(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
        return {
            "name":    info.get("longName", ticker),
            "sector":  info.get("sector", "N/A"),
            "industry":info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", None),
            "52w_high": info.get("fiftyTwoWeekHigh", None),
            "52w_low":  info.get("fiftyTwoWeekLow", None),
            "description": info.get("longBusinessSummary", "")[:400],
        }
    except Exception:
        return {}
