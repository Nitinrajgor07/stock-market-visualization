import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler


def predict_prices(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """
    Predicts future closing prices using Ridge Regression with
    lag features and technical indicators as inputs.
    Returns a DataFrame with columns: Date, Predicted, Upper, Lower.
    """
    if df is None or df.empty or len(df) < 60:
        return pd.DataFrame()

    close = df["Close"].values
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(close.reshape(-1, 1)).flatten()

    # Build features: 5 / 10 / 20 day lags + rolling std
    lags = [5, 10, 20]
    X, y = [], []
    max_lag = max(lags)

    for i in range(max_lag, len(scaled)):
        row = [scaled[i - l] for l in lags]
        row.append(float(np.std(scaled[i - 20:i])))  # volatility feature
        X.append(row)
        y.append(scaled[i])

    X, y = np.array(X), np.array(y)

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    # Iterative forecast
    window = list(scaled[-max_lag:])
    predictions = []
    for _ in range(days):
        row = [window[-l] for l in lags]
        row.append(float(np.std(window[-20:])))
        pred = model.predict([row])[0]
        predictions.append(pred)
        window.append(pred)

    # Inverse transform
    pred_prices = scaler.inverse_transform(
        np.array(predictions).reshape(-1, 1)).flatten()

    # Simple confidence interval based on residual std
    residuals = y - model.predict(X)
    sigma = scaler.inverse_transform([[float(np.std(residuals))]])[0][0]
    sigma = max(sigma, close[-1] * 0.005)  # at least 0.5%

    last_date = pd.to_datetime(df["Date"].iloc[-1])
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                  periods=days)

    return pd.DataFrame({
        "Date":      future_dates,
        "Predicted": pred_prices,
        "Upper":     pred_prices + 1.96 * sigma,
        "Lower":     pred_prices - 1.96 * sigma,
    })
