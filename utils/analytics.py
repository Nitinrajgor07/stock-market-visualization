import numpy as np
import pandas as pd


def calculate_summary(df: pd.DataFrame):
    if df is None or df.empty or "Close" not in df.columns:
        return {}

    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else None

    # Daily returns
    returns = close.pct_change().dropna()

    summary = {
        "mean_close":   float(close.mean()),
        "min_close":    float(close.min()),
        "max_close":    float(close.max()),
        "std_close":    float(close.std()),
        "daily_return": float(returns.mean() * 100),
        "volatility":   float(returns.std() * np.sqrt(252) * 100),
        "total_return": float((close.iloc[-1] / close.iloc[0] - 1) * 100),
    }

    if volume is not None:
        summary["total_volume"] = float(volume.sum())
        summary["avg_volume"]   = float(volume.mean())

    return summary


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "Close" not in df.columns:
        return df

    df = df.copy()
    close = df["Close"]

    # ── Moving Averages ──────────────────────────────────────────
    df["SMA_20"]  = close.rolling(window=20).mean()
    df["SMA_50"]  = close.rolling(window=50).mean()
    df["EMA_20"]  = close.ewm(span=20, adjust=False).mean()

    # ── Bollinger Bands ──────────────────────────────────────────
    sma20 = df["SMA_20"]
    std20 = close.rolling(window=20).std()
    df["BB_Upper"] = sma20 + 2 * std20
    df["BB_Lower"] = sma20 - 2 * std20

    # ── RSI (14) ─────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs        = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # ── MACD ─────────────────────────────────────────────────────
    ema12        = close.ewm(span=12, adjust=False).mean()
    ema26        = close.ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"]

    return df
