import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Dark theme defaults ───────────────────────────────────────────────────────
DARK = dict(
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3", family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zerolinecolor="#30363d"),
)

ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
RED     = "#f85149"
YELLOW  = "#d29922"
PURPLE  = "#bc8cff"
ORANGE  = "#ffa657"


def _apply_dark(fig, title="", height=500):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#e6edf3")),
        height=height,
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        margin=dict(l=20, r=20, t=50, b=20),
        **DARK,
    )
    return fig


# ── Line Chart with SMA / EMA / Bollinger Bands ───────────────────────────────
def create_line_chart(df, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"],
        mode="lines", name="Close",
        line=dict(color=ACCENT, width=2)))

    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_20"],
            mode="lines", name="SMA 20",
            line=dict(color=ORANGE, width=1.2, dash="dot")))

    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_50"],
            mode="lines", name="SMA 50",
            line=dict(color=PURPLE, width=1.2, dash="dot")))

    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["BB_Upper"],
            mode="lines", name="BB Upper",
            line=dict(color=YELLOW, width=1, dash="dash")))
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["BB_Lower"],
            mode="lines", name="BB Lower",
            fill="tonexty", fillcolor="rgba(210,153,34,0.08)",
            line=dict(color=YELLOW, width=1, dash="dash")))

    return _apply_dark(fig, f"{ticker} — Price & Indicators", 520)


# ── Candlestick + Volume combo ────────────────────────────────────────────────
def create_candlestick_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.03)

    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color=GREEN, decreasing_line_color=RED), row=1, col=1)

    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_20"], mode="lines",
            name="SMA 20", line=dict(color=ORANGE, width=1.2)), row=1, col=1)

    # Volume bars coloured green/red
    colors = [GREEN if c >= o else RED
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Volume"],
        marker_color=colors, name="Volume", showlegend=False), row=2, col=1)

    fig.update_layout(
        title=dict(text=f"{ticker} — Candlestick", font=dict(size=16, color="#e6edf3")),
        height=620, xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        margin=dict(l=20, r=20, t=50, b=20),
        **DARK,
    )
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")
    return fig


# ── RSI Chart ────────────────────────────────────────────────────────────────
def create_rsi_chart(df, ticker):
    if "RSI" not in df.columns:
        return None
    fig = go.Figure()

    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.1)",
                  line_width=0, annotation_text="Overbought",
                  annotation_position="top right",
                  annotation_font_color=RED)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(63,185,80,0.1)",
                  line_width=0, annotation_text="Oversold",
                  annotation_position="bottom right",
                  annotation_font_color=GREEN)
    fig.add_hline(y=70, line=dict(color=RED, dash="dash", width=1))
    fig.add_hline(y=30, line=dict(color=GREEN, dash="dash", width=1))

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["RSI"],
        mode="lines", name="RSI",
        line=dict(color=PURPLE, width=2)))

    fig.update_yaxes(range=[0, 100])
    return _apply_dark(fig, f"{ticker} — RSI (14)", 300)


# ── MACD Chart ───────────────────────────────────────────────────────────────
def create_macd_chart(df, ticker):
    if "MACD" not in df.columns:
        return None
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.4], vertical_spacing=0.05)

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD"],
        mode="lines", name="MACD",
        line=dict(color=ACCENT, width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD_Signal"],
        mode="lines", name="Signal",
        line=dict(color=ORANGE, width=1.5, dash="dot")), row=1, col=1)

    hist_colors = [GREEN if v >= 0 else RED for v in df["MACD_Hist"]]
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["MACD_Hist"],
        marker_color=hist_colors, name="Histogram"), row=2, col=1)

    fig.update_layout(
        title=dict(text=f"{ticker} — MACD", font=dict(size=16, color="#e6edf3")),
        height=420, margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        **DARK,
    )
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")
    return fig


# ── Volume Chart ─────────────────────────────────────────────────────────────
def create_volume_chart(df, ticker):
    colors = [GREEN if c >= o else RED
              for c, o in zip(df["Close"], df["Open"])]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Volume"],
        marker_color=colors, name="Volume"))
    return _apply_dark(fig, f"{ticker} — Trading Volume", 400)


# ── Normalised Comparison Chart ───────────────────────────────────────────────
def create_comparison_chart(data_dict):
    palette = [ACCENT, GREEN, ORANGE, PURPLE, RED, YELLOW]
    fig = go.Figure()
    for i, (ticker, df) in enumerate(data_dict.items()):
        if df is None or df.empty or "Close" not in df.columns:
            continue
        norm = df["Close"] / df["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=df["Date"], y=norm,
            mode="lines", name=ticker,
            line=dict(color=palette[i % len(palette)], width=2)))

    fig.add_hline(y=100, line=dict(color="#30363d", dash="dash", width=1))
    return _apply_dark(fig, "Stock Comparison (Normalised to 100)", 520)


# ── Prediction Chart ─────────────────────────────────────────────────────────
def create_prediction_chart(df, future_df, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"],
        mode="lines", name="Historical",
        line=dict(color=ACCENT, width=2)))

    fig.add_trace(go.Scatter(
        x=future_df["Date"], y=future_df["Predicted"],
        mode="lines", name="Predicted",
        line=dict(color=ORANGE, width=2, dash="dash")))

    if "Upper" in future_df.columns:
        fig.add_trace(go.Scatter(
            x=future_df["Date"], y=future_df["Upper"],
            mode="lines", name="Upper CI",
            line=dict(color=YELLOW, width=1, dash="dot")))
        fig.add_trace(go.Scatter(
            x=future_df["Date"], y=future_df["Lower"],
            mode="lines", name="Lower CI",
            fill="tonexty", fillcolor="rgba(210,153,34,0.10)",
            line=dict(color=YELLOW, width=1, dash="dot")))

    return _apply_dark(fig, f"{ticker} — Price Prediction (30 days)", 520)


# ── Portfolio Performance Chart ───────────────────────────────────────────────
def create_portfolio_chart(portfolio_df):
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Portfolio Value Over Time",
                                        "Allocation by Stock"),
                        specs=[[{"type": "scatter"}, {"type": "pie"}]])

    fig.add_trace(go.Scatter(
        x=portfolio_df["Date"], y=portfolio_df["Total Value"],
        mode="lines", fill="tozeroy",
        fillcolor="rgba(88,166,255,0.15)",
        line=dict(color=ACCENT, width=2), name="Total Value"), row=1, col=1)

    if "Stock" in portfolio_df.columns and "Value" in portfolio_df.columns:
        latest = portfolio_df.sort_values("Date").groupby("Stock")["Value"].last()
        fig.add_trace(go.Pie(
            labels=latest.index, values=latest.values,
            hole=0.45,
            marker=dict(colors=[ACCENT, GREEN, ORANGE, PURPLE, RED, YELLOW])),
            row=1, col=2)

    fig.update_layout(
        height=420, margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        **DARK,
    )
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")
    return fig
