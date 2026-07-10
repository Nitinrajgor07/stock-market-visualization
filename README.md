# 📈 Stock Market Visualization Dashboard

An advanced M.Sc CS & IT project built with Python, Streamlit, yfinance, Plotly, scikit-learn, and the Anthropic Claude API.

## ✨ Features

### 📊 Charts Tab
- Line chart with SMA 20, SMA 50, EMA 20 & Bollinger Bands overlay
- Candlestick chart with coloured volume bars
- Normalised multi-stock comparison chart

### 📉 Technical Indicators Tab
- **RSI (14)** — Overbought / Oversold signals
- **MACD** — Bullish/Bearish crossover detection
- **Bollinger Bands** — Bandwidth analysis

### 🤖 Price Prediction Tab
- 30-day forecast using Ridge Regression
- Lag features + rolling volatility inputs
- 95% confidence interval band

### 🌐 News Sentiment Tab
- Real-time headlines via yfinance
- AI-powered sentiment analysis using Claude API
- Per-headline sentiment breakdown

### 💼 Portfolio Tracker Tab
- Track multiple stock holdings
- Live P&L calculation ($ and %)
- Portfolio value history chart

### 📋 Data Tab
- Full historical OHLCV + indicator data
- Company description
- CSV export

## 🛠 Tech Stack
- Python 3.10+
- Streamlit · yfinance · Pandas · NumPy
- Plotly · scikit-learn
- Anthropic Claude API (sentiment)

## 🚀 How to Run

```bash
pip install -r requirements.txt
streamlit run main.py
```

## 📁 File Structure
```
stock-market-visualization/
├── main.py                      # Main Streamlit app
├── requirements.txt
├── utils/
│   ├── data_fetcher.py          # yfinance data + company info
│   ├── analytics.py             # RSI, MACD, Bollinger Bands, SMA/EMA
│   ├── visualizations.py        # All Plotly charts (dark theme)
│   ├── ml_predictor.py          # Ridge Regression price prediction
│   ├── sentiment.py             # Claude AI news sentiment
│   └── portfolio.py             # Portfolio P&L tracker
└── output/
    └── stock_data.csv
```
