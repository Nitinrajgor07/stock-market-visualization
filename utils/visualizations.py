import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Dynamic Theme Colors Resolver ─────────────────────────────────────────────
def get_theme_colors():
    is_dark = st.session_state.get("dark_mode", True)
    if not is_dark:
        # Light Mode (White Glassmorphic theme)
        return {
            "accent": "#2563EB",
            "green": "#16A34A",
            "red": "#DC2626",
            "yellow": "#F59E0B",
            "purple": "#8B5CF6",
            "orange": "#F97316",
            "paper_bg": "rgba(0,0,0,0)", # Transparent for card glassmorphism
            "plot_bg": "rgba(0,0,0,0)",  # Transparent plot canvas
            "text": "#111827",
            "grid": "#e2e8f0",
            "line": "#cbd5e1",
            "legend_bg": "rgba(255, 255, 255, 0.72)",
            "legend_border": "rgba(255, 255, 255, 0.35)",
            "bb_fill": "rgba(245,158,11,0.08)",
            "rsi_upper_fill": "rgba(220,38,38,0.06)",
            "rsi_lower_fill": "rgba(22,163,74,0.06)",
            "pred_fill": "rgba(245,158,11,0.08)",
            "pf_fill": "rgba(37,99,235,0.08)",
        }
    else:
        # Dark Mode (Original Zerodha dark theme colors)
        return {
            "accent": "#58a6ff",
            "green": "#3fb950",
            "red": "#f85149",
            "yellow": "#d29922",
            "purple": "#bc8cff",
            "orange": "#ffa657",
            "paper_bg": "#0d1117",
            "plot_bg": "#0d1117",
            "text": "#e6edf3",
            "grid": "#21262d",
            "line": "#30363d",
            "legend_bg": "#161b22",
            "legend_border": "#30363d",
            "bb_fill": "rgba(210,153,34,0.08)",
            "rsi_upper_fill": "rgba(248,81,73,0.1)",
            "rsi_lower_fill": "rgba(63,185,80,0.1)",
            "pred_fill": "rgba(210,153,34,0.10)",
            "pf_fill": "rgba(88,166,255,0.15)",
        }

def _apply_theme(fig, title="", height=500):
    t = get_theme_colors()
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=t["text"])),
        height=height,
        legend=dict(bgcolor=t["legend_bg"], bordercolor=t["legend_border"], borderwidth=1),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor=t["paper_bg"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["text"], family="Outfit, Inter, sans-serif" if not st.session_state.get("dark_mode", True) else "Inter, sans-serif"),
    )
    # Apply axis line colors
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    return fig

# ── Line Chart with SMA / EMA / Bollinger Bands ───────────────────────────────
def create_line_chart(df, ticker):
    t = get_theme_colors()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"],
        mode="lines", name="Close",
        line=dict(color=t["accent"], width=2)))

    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_20"],
            mode="lines", name="SMA 20",
            line=dict(color=t["orange"], width=1.2, dash="dot")))

    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_50"],
            mode="lines", name="SMA 50",
            line=dict(color=t["purple"], width=1.2, dash="dot")))

    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["BB_Upper"],
            mode="lines", name="BB Upper",
            line=dict(color=t["yellow"], width=1, dash="dash")))
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["BB_Lower"],
            mode="lines", name="BB Lower",
            fill="tonexty", fillcolor=t["bb_fill"],
            line=dict(color=t["yellow"], width=1, dash="dash")))

    return _apply_theme(fig, f"{ticker} — Price & Indicators", 520)

# ── Candlestick + Volume combo ────────────────────────────────────────────────
def create_candlestick_chart(df, ticker):
    t = get_theme_colors()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.03)

    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color=t["green"], decreasing_line_color=t["red"]), row=1, col=1)

    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["SMA_20"], mode="lines",
            name="SMA 20", line=dict(color=t["orange"], width=1.2)), row=1, col=1)

    # Volume bars coloured green/red
    colors = [t["green"] if c >= o else t["red"]
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Volume"],
        marker_color=colors, name="Volume", showlegend=False), row=2, col=1)

    fig.update_layout(
        title=dict(text=f"{ticker} — Candlestick", font=dict(size=15, color=t["text"])),
        height=620, xaxis_rangeslider_visible=False,
        legend=dict(bgcolor=t["legend_bg"], bordercolor=t["legend_border"], borderwidth=1),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor=t["paper_bg"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["text"], family="Outfit, Inter, sans-serif" if not st.session_state.get("dark_mode", True) else "Inter, sans-serif"),
    )
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    return fig

# ── RSI Chart ────────────────────────────────────────────────────────────────
def create_rsi_chart(df, ticker):
    if "RSI" not in df.columns:
        return None
    t = get_theme_colors()
    fig = go.Figure()

    fig.add_hrect(y0=70, y1=100, fillcolor=t["rsi_upper_fill"],
                  line_width=0, annotation_text="Overbought",
                  annotation_position="top right",
                  annotation_font_color=t["red"])
    fig.add_hrect(y0=0, y1=30, fillcolor=t["rsi_lower_fill"],
                  line_width=0, annotation_text="Oversold",
                  annotation_position="bottom right",
                  annotation_font_color=t["green"])
    fig.add_hline(y=70, line=dict(color=t["red"], dash="dash", width=1))
    fig.add_hline(y=30, line=dict(color=t["green"], dash="dash", width=1))

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["RSI"],
        mode="lines", name="RSI",
        line=dict(color=t["purple"], width=2)))

    fig.update_yaxes(range=[0, 100])
    return _apply_theme(fig, f"{ticker} — RSI (14)", 300)

# ── MACD Chart ───────────────────────────────────────────────────────────────
def create_macd_chart(df, ticker):
    if "MACD" not in df.columns:
        return None
    t = get_theme_colors()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.4], vertical_spacing=0.05)

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD"],
        mode="lines", name="MACD",
        line=dict(color=t["accent"], width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD_Signal"],
        mode="lines", name="Signal",
        line=dict(color=t["orange"], width=1.5, dash="dot")), row=1, col=1)

    hist_colors = [t["green"] if v >= 0 else t["red"] for v in df["MACD_Hist"]]
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["MACD_Hist"],
        marker_color=hist_colors, name="Histogram"), row=2, col=1)

    fig.update_layout(
        title=dict(text=f"{ticker} — MACD", font=dict(size=15, color=t["text"])),
        height=420, margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor=t["legend_bg"], bordercolor=t["legend_border"], borderwidth=1),
        paper_bgcolor=t["paper_bg"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["text"], family="Outfit, Inter, sans-serif" if not st.session_state.get("dark_mode", True) else "Inter, sans-serif"),
    )
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    return fig

# ── Volume Chart ─────────────────────────────────────────────────────────────
def create_volume_chart(df, ticker):
    t = get_theme_colors()
    colors = [t["green"] if c >= o else t["red"]
              for c, o in zip(df["Close"], df["Open"])]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Volume"],
        marker_color=colors, name="Volume"))
    return _apply_theme(fig, f"{ticker} — Trading Volume", 400)

# ── Normalised Comparison Chart ───────────────────────────────────────────────
def create_comparison_chart(data_dict):
    t = get_theme_colors()
    palette = [t["accent"], t["green"], t["orange"], t["purple"], t["red"], t["yellow"]]
    fig = go.Figure()
    for i, (ticker, df) in enumerate(data_dict.items()):
        if df is None or df.empty or "Close" not in df.columns:
            continue
        norm = df["Close"] / df["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=df["Date"], y=norm,
            mode="lines", name=ticker,
            line=dict(color=palette[i % len(palette)], width=2)))

    fig.add_hline(y=100, line=dict(color=t["line"], dash="dash", width=1))
    return _apply_theme(fig, "Stock Comparison (Normalised to 100)", 520)

# ── Prediction Chart ─────────────────────────────────────────────────────────
def create_prediction_chart(df, future_df, ticker):
    t = get_theme_colors()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"],
        mode="lines", name="Historical",
        line=dict(color=t["accent"], width=2)))

    fig.add_trace(go.Scatter(
        x=future_df["Date"], y=future_df["Predicted"],
        mode="lines", name="Predicted",
        line=dict(color=t["orange"], width=2, dash="dash")))

    if "Upper" in future_df.columns:
        fig.add_trace(go.Scatter(
            x=future_df["Date"], y=future_df["Upper"],
            mode="lines", name="Upper CI",
            line=dict(color=t["yellow"], width=1, dash="dot")))
        fig.add_trace(go.Scatter(
            x=future_df["Date"], y=future_df["Lower"],
            mode="lines", name="Lower CI",
            fill="tonexty", fillcolor=t["pred_fill"],
            line=dict(color=t["yellow"], width=1, dash="dot")))

    return _apply_theme(fig, f"{ticker} — Price Prediction (30 days)", 520)

# ── Portfolio Performance Chart ───────────────────────────────────────────────
def create_portfolio_chart(portfolio_df):
    t = get_theme_colors()
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Portfolio Value Over Time",
                                        "Allocation by Stock"),
                        specs=[[{"type": "scatter"}, {"type": "pie"}]])

    fig.add_trace(go.Scatter(
        x=portfolio_df["Date"], y=portfolio_df["Total Value"],
        mode="lines", fill="tozeroy",
        fillcolor=t["pf_fill"],
        line=dict(color=t["accent"], width=2), name="Total Value"), row=1, col=1)

    if "Stock" in portfolio_df.columns and "Value" in portfolio_df.columns:
        latest = portfolio_df.sort_values("Date").groupby("Stock")["Value"].last()
        fig.add_trace(go.Pie(
            labels=latest.index, values=latest.values,
            hole=0.45,
            marker=dict(colors=[t["accent"], t["green"], t["orange"], t["purple"], t["red"], t["yellow"]])),
            row=1, col=2)

    fig.update_layout(
        height=420, margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(bgcolor=t["legend_bg"], bordercolor=t["legend_border"], borderwidth=1),
        paper_bgcolor=t["paper_bg"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["text"], family="Outfit, Inter, sans-serif" if not st.session_state.get("dark_mode", True) else "Inter, sans-serif"),
    )
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["line"], zerolinecolor=t["line"])
    return fig


# ── Premium Interactive Multi-Indicator Chart ───────────────────────────────
def create_premium_chart(df, ticker, chart_type="Candlestick", indicators=["Volume"], prediction_df=None, comparison_df_dict=None, theme_mode="dark", fullscreen=False):
    t = get_theme_colors()

    # 1. Determine X column
    x_col = "Datetime" if "Datetime" in df.columns else "Date"

    # 2. Determine Subplots configuration
    active_subplots = []
    if "Volume" in indicators and "Volume" in df.columns:
        active_subplots.append("Volume")
    if "RSI" in indicators and "RSI" in df.columns:
        active_subplots.append("RSI")
    if "MACD" in indicators and "MACD" in df.columns:
        active_subplots.append("MACD")

    num_rows = 1 + len(active_subplots)
    row_heights = [0.65] # Price takes 65%
    remaining_height = 0.35
    if len(active_subplots) > 0:
        each_height = remaining_height / len(active_subplots)
        row_heights.extend([each_height] * len(active_subplots))
    else:
        row_heights = [1.0]

    fig = make_subplots(
        rows=num_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights
    )

    # Map from subplot name to its row index
    row_map = {}
    current_row = 2
    for subplot in active_subplots:
        row_map[subplot] = current_row
        current_row += 1

    # 3. Handle Normalised Comparison if comparison_df_dict is provided
    is_comparison = comparison_df_dict is not None and len(comparison_df_dict) > 0

    if is_comparison:
        # Plot normalized main stock
        main_norm = df["Close"] / df["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=df[x_col], y=main_norm,
            mode="lines", name=ticker,
            line=dict(color=t["accent"], width=2.5)
        ), row=1, col=1)

        # Plot normalized comparison stocks
        palette = [t["green"], t["orange"], t["purple"], t["red"], t["yellow"]]
        for idx, (comp_tkr, comp_df) in enumerate(comparison_df_dict.items()):
            comp_x = "Datetime" if "Datetime" in comp_df.columns else "Date"
            comp_norm = comp_df["Close"] / comp_df["Close"].iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=comp_df[comp_x], y=comp_norm,
                mode="lines", name=comp_tkr,
                line=dict(color=palette[idx % len(palette)], width=1.8)
            ), row=1, col=1)

        # Add baseline line at 100%
        fig.add_hline(y=100, line=dict(color=t["line"], dash="dash", width=1.2), row=1, col=1)

    else:
        # Standard Main Price Chart
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=df[x_col], open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=ticker,
                increasing_line_color=t["green"], decreasing_line_color=t["red"],
                increasing_fillcolor=t["green"], decreasing_fillcolor=t["red"],
                showlegend=False
            ), row=1, col=1)
        elif chart_type == "Line":
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["Close"], mode="lines",
                name=ticker, line=dict(color=t["accent"], width=2.5)
            ), row=1, col=1)
        elif chart_type == "Area":
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["Close"], mode="lines",
                name=ticker, fill="tozeroy",
                fillcolor=t["pf_fill"],
                line=dict(color=t["accent"], width=2.5)
            ), row=1, col=1)

        # 4. Indicators Overlays on Price (Row 1)
        if "SMA 20" in indicators and "SMA_20" in df.columns:
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["SMA_20"], mode="lines",
                name="SMA 20", line=dict(color=t["orange"], width=1.5, dash="dot")
            ), row=1, col=1)

        if "SMA 50" in indicators and "SMA_50" in df.columns:
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["SMA_50"], mode="lines",
                name="SMA 50", line=dict(color=t["purple"], width=1.5, dash="dot")
            ), row=1, col=1)

        if "EMA 20" in indicators and "EMA_20" in df.columns:
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["EMA_20"], mode="lines",
                name="EMA 20", line=dict(color=t["yellow"], width=1.5)
            ), row=1, col=1)

        if "Bollinger Bands" in indicators and "BB_Upper" in df.columns:
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["BB_Upper"], mode="lines",
                name="BB Upper", line=dict(color=t["yellow"], width=1.2, dash="dash")
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["BB_Lower"], mode="lines",
                name="BB Lower", fill="tonexty", fillcolor=t["bb_fill"],
                line=dict(color=t["yellow"], width=1.2, dash="dash")
            ), row=1, col=1)

        # 5. Overlays Prediction if prediction_df is active
        if prediction_df is not None and not prediction_df.empty:
            fig.add_trace(go.Scatter(
                x=prediction_df["Date"], y=prediction_df["Predicted"],
                mode="lines", name="AI Forecast",
                line=dict(color=t["orange"], width=2.2, dash="dash")
            ), row=1, col=1)

            if "Upper" in prediction_df.columns:
                fig.add_trace(go.Scatter(
                    x=prediction_df["Date"], y=prediction_df["Upper"],
                    mode="lines", name="AI Upper CI",
                    line=dict(color=t["yellow"], width=1, dash="dot")
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=prediction_df["Date"], y=prediction_df["Lower"],
                    mode="lines", name="AI Lower CI",
                    fill="tonexty", fillcolor=t["pred_fill"],
                    line=dict(color=t["yellow"], width=1, dash="dot")
                ), row=1, col=1)

    # 6. Volume Subplot
    if "Volume" in row_map:
        r = row_map["Volume"]
        vol_colors = [t["green"] if c >= o else t["red"]
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(
            x=df[x_col], y=df["Volume"],
            marker_color=vol_colors, name="Volume",
            opacity=0.8, showlegend=False
        ), row=r, col=1)
        fig.update_yaxes(title="Vol", title_font=dict(size=9), row=r, col=1)

    # 7. RSI Subplot
    if "RSI" in row_map:
        r = row_map["RSI"]
        fig.add_hrect(y0=70, y1=100, fillcolor=t["rsi_upper_fill"],
                      line_width=0, annotation_text="Overbought",
                      annotation_position="top right",
                      annotation_font_color=t["red"], row=r, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor=t["rsi_lower_fill"],
                      line_width=0, annotation_text="Oversold",
                      annotation_position="bottom right",
                      annotation_font_color=t["green"], row=r, col=1)
        fig.add_hline(y=70, line=dict(color=t["red"], dash="dash", width=1), row=r, col=1)
        fig.add_hline(y=30, line=dict(color=t["green"], dash="dash", width=1), row=r, col=1)
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["RSI"],
            mode="lines", name="RSI (14)",
            line=dict(color=t["purple"], width=1.8),
            showlegend=False
        ), row=r, col=1)
        fig.update_yaxes(range=[0, 100], title="RSI", title_font=dict(size=9), row=r, col=1)

    # 8. MACD Subplot
    if "MACD" in row_map:
        r = row_map["MACD"]
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["MACD"],
            mode="lines", name="MACD",
            line=dict(color=t["accent"], width=1.8)
        ), row=r, col=1)
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df["MACD_Signal"],
            mode="lines", name="Signal",
            line=dict(color=t["orange"], width=1.5, dash="dot")
        ), row=r, col=1)

        hist_colors = [t["green"] if v >= 0 else t["red"] for v in df["MACD_Hist"]]
        fig.add_trace(go.Bar(
            x=df[x_col], y=df["MACD_Hist"],
            marker_color=hist_colors, name="Histogram",
            showlegend=False
        ), row=r, col=1)
        fig.update_yaxes(title="MACD", title_font=dict(size=9), row=r, col=1)

    # 9. Layout styling & Unified Spikes/Hover
    h = 800 if fullscreen else 520
    fig.update_layout(
        height=h,
        hovermode="x unified",
        margin=dict(l=15, r=15, t=35, b=15),
        paper_bgcolor=t["paper_bg"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["text"], size=10, family="Outfit, Inter, sans-serif" if theme_mode == "light" else "Inter, sans-serif"),
        legend=dict(
            orientation="h",
            y=1.02,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=9)
        ),
        xaxis=dict(
            rangeslider_visible=False,
            showspikes=True,
            spikethickness=1,
            spikedash="dot",
            spikemode="across",
            spikecolor=t["line"]
        )
    )

    # Spikes and Grid config
    fig.update_xaxes(
        gridcolor=t["grid"],
        linecolor=t["line"],
        zerolinecolor=t["line"],
        showline=True,
        mirror=True
    )
    fig.update_yaxes(
        gridcolor=t["grid"],
        linecolor=t["line"],
        zerolinecolor=t["line"],
        showline=True,
        mirror=True
    )

    return fig
