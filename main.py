import os
import time
import json
import base64
import requests
import pytz
import textwrap
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta
import plotly.graph_objects as go

# ── Auto-refresh interval (seconds) ────────────────────────────────────────────
_AUTO_REFRESH_SECS = 60

from utils.data_fetcher   import fetch_stock_data, fetch_company_info
from utils.analytics      import calculate_summary, add_indicators
from utils.visualizations import (
    create_line_chart, create_candlestick_chart,
    create_volume_chart, create_rsi_chart, create_macd_chart,
    create_prediction_chart, create_comparison_chart,
)
from utils.ml_predictor import predict_prices
from utils.sentiment    import fetch_news_headlines, analyse_sentiment

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# 🔐 PASSWORD AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════
import hashlib

def check_password(input_pwd: str, correct_hash: str) -> bool:
    return hashlib.sha256(input_pwd.encode()).hexdigest() == correct_hash

# Password must be set in Streamlit Secrets (local .streamlit/secrets.toml or Streamlit Cloud)
try:
    CORRECT_HASH = st.secrets["APP_PASSWORD_HASH"]
except Exception:
    st.error("APP_PASSWORD_HASH not set in secrets. Please set it in .streamlit/secrets.toml or Streamlit Cloud secrets.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_failed" not in st.session_state:
    st.session_state.login_failed = False
if "authenticating" not in st.session_state:
    st.session_state.authenticating = False
if "login_email" not in st.session_state:
    st.session_state.login_email = ""
if "login_password" not in st.session_state:
    st.session_state.login_password = ""
if "login_btn_clicked" not in st.session_state:
    st.session_state.login_btn_clicked = False
# ── User Preferences Loading & Initialization ──
PREFERENCES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_preferences.json")

@st.cache_data(ttl=300)
def load_preferences():
    try:
        if os.path.exists(PREFERENCES_FILE):
            with open(PREFERENCES_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_preferences():
    data = {
        "settings_theme": st.session_state.get("settings_theme", "Auto Theme"),
        "settings_accent": st.session_state.get("settings_accent", "Blue"),
        "settings_font_size": st.session_state.get("settings_font_size", "Medium"),
        "settings_density": st.session_state.get("settings_density", "Comfortable"),
        "notify_market": st.session_state.get("notify_market", True),
        "notify_price": st.session_state.get("notify_price", True),
        "notify_portfolio": st.session_state.get("notify_portfolio", True),
        "notify_news": st.session_state.get("notify_news", False),
        "notify_ai": st.session_state.get("notify_ai", True),
        "notify_email": st.session_state.get("notify_email", True),
        "notify_push": st.session_state.get("notify_push", False),
        "pref_landing": st.session_state.get("pref_landing", "home"),
        "pref_visible_cards": st.session_state.get("pref_visible_cards", ["Portfolio Value", "Daily P&L", "Cash Balance", "Total Invested"]),
        "pref_favorite_widgets": st.session_state.get("pref_favorite_widgets", ["Market Breadth", "Sector Performance", "Top Gainers/Losers"]),
        "pref_chart_view": st.session_state.get("pref_chart_view", "Candlestick"),
        "pref_watchlist_sort": st.session_state.get("pref_watchlist_sort", "Ticker A-Z"),
    }
    try:
        with open(PREFERENCES_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

# Initialize session state theme variables
pref = load_preferences()
if pref:
    if "settings_theme" not in st.session_state: st.session_state.settings_theme = pref.get("settings_theme", "Auto Theme")
    if "settings_accent" not in st.session_state: st.session_state.settings_accent = pref.get("settings_accent", "Blue")
    if "settings_font_size" not in st.session_state: st.session_state.settings_font_size = pref.get("settings_font_size", "Medium")
    if "settings_density" not in st.session_state: st.session_state.settings_density = pref.get("settings_density", "Comfortable")
    if "notify_market" not in st.session_state: st.session_state.notify_market = pref.get("notify_market", True)
    if "notify_price" not in st.session_state: st.session_state.notify_price = pref.get("notify_price", True)
    if "notify_portfolio" not in st.session_state: st.session_state.notify_portfolio = pref.get("notify_portfolio", True)
    if "notify_news" not in st.session_state: st.session_state.notify_news = pref.get("notify_news", False)
    if "notify_ai" not in st.session_state: st.session_state.notify_ai = pref.get("notify_ai", True)
    if "notify_email" not in st.session_state: st.session_state.notify_email = pref.get("notify_email", True)
    if "notify_push" not in st.session_state: st.session_state.notify_push = pref.get("notify_push", False)
    if "pref_landing" not in st.session_state: st.session_state.pref_landing = pref.get("pref_landing", "home")
    if "pref_visible_cards" not in st.session_state: st.session_state.pref_visible_cards = pref.get("pref_visible_cards", ["Portfolio Value", "Daily P&L", "Cash Balance", "Total Invested"])
    if "pref_favorite_widgets" not in st.session_state: st.session_state.pref_favorite_widgets = pref.get("pref_favorite_widgets", ["Market Breadth", "Sector Performance", "Top Gainers/Losers"])
    if "pref_chart_view" not in st.session_state: st.session_state.pref_chart_view = pref.get("pref_chart_view", "Candlestick")
    if "pref_watchlist_sort" not in st.session_state: st.session_state.pref_watchlist_sort = pref.get("pref_watchlist_sort", "Ticker A-Z")
else:
    if "settings_theme" not in st.session_state: st.session_state.settings_theme = "Auto Theme"
    if "settings_accent" not in st.session_state: st.session_state.settings_accent = "Blue"
    if "settings_font_size" not in st.session_state: st.session_state.settings_font_size = "Medium"
    if "settings_density" not in st.session_state: st.session_state.settings_density = "Comfortable"
    if "notify_market" not in st.session_state: st.session_state.notify_market = True
    if "notify_price" not in st.session_state: st.session_state.notify_price = True
    if "notify_portfolio" not in st.session_state: st.session_state.notify_portfolio = True
    if "notify_news" not in st.session_state: st.session_state.notify_news = False
    if "notify_ai" not in st.session_state: st.session_state.notify_ai = True
    if "notify_email" not in st.session_state: st.session_state.notify_email = True
    if "notify_push" not in st.session_state: st.session_state.notify_push = False
    if "pref_landing" not in st.session_state: st.session_state.pref_landing = "home"
    if "pref_visible_cards" not in st.session_state: st.session_state.pref_visible_cards = ["Portfolio Value", "Daily P&L", "Cash Balance", "Total Invested"]
    if "pref_favorite_widgets" not in st.session_state: st.session_state.pref_favorite_widgets = ["Market Breadth", "Sector Performance", "Top Gainers/Losers"]
    if "pref_chart_view" not in st.session_state: st.session_state.pref_chart_view = "Candlestick"
    if "pref_watchlist_sort" not in st.session_state: st.session_state.pref_watchlist_sort = "Ticker A-Z"

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"

# Theme forced to Light across the entire dashboard (dark theme disabled)
st.session_state.settings_theme = "Light Theme"
st.session_state.theme_mode = "light"
st.session_state.dark_mode = False

# ── Dynamic Theme Palette definition ──────────────────────────────────────────
if not st.session_state.dark_mode:
    BG_COLOR = "#F7F9FC"
    CARD_BG = "rgba(255,255,255,0.72)"
    BORDER = "rgba(255,255,255,0.35)"
    BLUE = "#2563EB"
    LIGHT_BLUE = "#60A5FA"
    GREEN = "#16A34A"
    RED = "#DC2626"
    YELLOW = "#F59E0B"
    TEXT = "#111827"
    MUTED = "#94A3B8"
    SECONDARY_TEXT = "#6B7280"
    
    # Chart design system variables
    CHART_PAPER_BG = "rgba(0,0,0,0)"
    CHART_PLOT_BG = "rgba(0,0,0,0)"
    CHART_GRID = "#e2e8f0"
    CHART_LINE = "#cbd5e1"
    
    # Login styling specific variables
    login_icon_bg = "linear-gradient(135deg, #2563EB, #60A5FA)"
    login_icon_border = "rgba(255,255,255,0.4)"
    login_title_color = "#111827"
    login_sub_color = "#6B7280"
    login_card_bg = "rgba(255,255,255,0.72)"
    login_card_border = "rgba(255,255,255,0.35)"
    login_card_shadow = "0 20px 50px rgba(15,23,42,0.08)"
    login_footer_color = "#94A3B8"
    err_bg = "rgba(220,38,38,0.08)"
    err_border = "rgba(220,38,38,0.2)"
    err_color = "#DC2626"
else:
    BG_COLOR = "#0f1116"
    CARD_BG = "#1a1d27"
    BORDER = "#2a2d3a"
    BLUE = "#3b82f6"
    LIGHT_BLUE = "#58a6ff"
    GREEN = "#27ae60"
    RED = "#e74c3c"
    YELLOW = "#f59e0b"
    TEXT = "#e8eaf0"
    MUTED = "#8b90a0"
    SECONDARY_TEXT = "#8b90a0"
    
    # Chart design system variables
    CHART_PAPER_BG = "#0f1116"
    CHART_PLOT_BG = "#0f1116"
    CHART_GRID = "#1e2130"
    CHART_LINE = "#2a2d3a"
    
    # Login styling specific variables
    login_icon_bg = "linear-gradient(145deg,#1c2d50,#0d1626)"
    login_icon_border = "#2a3d60"
    login_title_color = "#f0f3ff"
    login_sub_color = "#3d4460"
    login_card_bg = "rgba(14,17,28,0.97)"
    login_card_border = "#1c2040"
    login_card_shadow = "0 20px 60px rgba(0,0,0,0.7)"
    login_footer_color = "#1e2235"
    err_bg = "#1c0808"
    err_border = "rgba(231,76,60,0.38)"
    err_color = "#e05c4b"

# Define accent colors mapping
accent_color = st.session_state.get("settings_accent", "Blue")
if accent_color == "Blue":
    PRIMARY_BLUE = "#3b82f6"
    ACCENT_GRADIENT = "linear-gradient(135deg, #2563EB, #60A5FA)" if not st.session_state.dark_mode else "linear-gradient(135deg, #3b82f6, #58a6ff)"
    BLUE = "#2563EB" if not st.session_state.dark_mode else "#3b82f6"
    LIGHT_BLUE = "#60A5FA" if not st.session_state.dark_mode else "#58a6ff"
elif accent_color == "Purple":
    PRIMARY_BLUE = "#8b5cf6"
    ACCENT_GRADIENT = "linear-gradient(135deg, #7C3AED, #A78BFA)" if not st.session_state.dark_mode else "linear-gradient(135deg, #8b5cf6, #a78bfa)"
    BLUE = "#7C3AED" if not st.session_state.dark_mode else "#8b5cf6"
    LIGHT_BLUE = "#A78BFA" if not st.session_state.dark_mode else "#a78bfa"
elif accent_color == "Green":
    PRIMARY_BLUE = "#10b981"
    ACCENT_GRADIENT = "linear-gradient(135deg, #059669, #34D399)" if not st.session_state.dark_mode else "linear-gradient(135deg, #10b981, #34d399)"
    BLUE = "#059669" if not st.session_state.dark_mode else "#10b981"
    LIGHT_BLUE = "#34D399" if not st.session_state.dark_mode else "#34d399"
elif accent_color == "Orange":
    PRIMARY_BLUE = "#f97316"
    ACCENT_GRADIENT = "linear-gradient(135deg, #EA580C, #FB923C)" if not st.session_state.dark_mode else "linear-gradient(135deg, #f97316, #fb923c)"
    BLUE = "#EA580C" if not st.session_state.dark_mode else "#f97316"
    LIGHT_BLUE = "#FB923C" if not st.session_state.dark_mode else "#fb923c"
else:
    PRIMARY_BLUE = "#3b82f6"
    ACCENT_GRADIENT = "linear-gradient(135deg, #2563EB, #60A5FA)" if not st.session_state.dark_mode else "linear-gradient(135deg, #3b82f6, #58a6ff)"
    BLUE = "#2563EB" if not st.session_state.dark_mode else "#3b82f6"
    LIGHT_BLUE = "#60A5FA" if not st.session_state.dark_mode else "#58a6ff"

# Define density variable mappings
density_setting = st.session_state.get("settings_density", "Comfortable")
if density_setting == "Compact":
    CARD_PADDING = "12px"
    ELEMENT_GAP = "8px"
    TABLE_PADDING = "6px 10px"
elif density_setting == "Spacious":
    CARD_PADDING = "28px"
    ELEMENT_GAP = "24px"
    TABLE_PADDING = "16px 22px"
else: # Comfortable
    CARD_PADDING = "20px"
    ELEMENT_GAP = "16px"
    TABLE_PADDING = "12px 16px"

# Define font size mappings
font_size_setting = st.session_state.get("settings_font_size", "Medium")
if font_size_setting == "Small":
    FONT_SIZE_BASE = "0.9rem"
elif font_size_setting == "Large":
    FONT_SIZE_BASE = "1.1rem"
else: # Medium
    FONT_SIZE_BASE = "1.0rem"

if not st.session_state.authenticated:
    # Design tokens matching clean corporate fintech style
    PAGE_BG        = "#F8FAFC"
    CARD_BG        = "#FFFFFF"
    BORDER_COLOR   = "#E5E7EB"
    TEXT_COLOR     = "#111827"
    SEC_TEXT_COLOR = "#6B7280"
    PRIMARY_COLOR  = "#2563EB"
    HOVER_COLOR    = "#1D4ED8"
    ERR_BG, ERR_BORDER, ERR_COLOR = "rgba(220,38,38,0.06)", "rgba(220,38,38,0.15)", "#DC2626"

    login_style = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(16px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes float-1 {{
        0%, 100% {{ transform: translate(0, 0) scale(1); }}
        50% {{ transform: translate(15px, -20px) scale(1.03); }}
    }}
    @keyframes float-2 {{
        0%, 100% {{ transform: translate(0, 0) scale(1); }}
        50% {{ transform: translate(-15px, 12px) scale(0.97); }}
    }}
    @keyframes float-3 {{
        0%, 100% {{ transform: translate(0, 0) scale(1); }}
        50% {{ transform: translate(10px, 15px) scale(1.01); }}
    }}
    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}

    /* Force full-screen split-screen layout & neutralize block padding */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], section[data-testid="stMain"] {{
        background: {PAGE_BG} !important;
        font-family: 'Inter', sans-serif !important;
        overflow: hidden !important;
        height: 100vh !important;
        width: 100vw !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    
    .stApp .main .block-container,
    .stApp [data-testid="stMain"] .block-container,
    [data-testid="stAppViewContainer"] .main .block-container,
    [data-testid="stAppViewBlockContainer"],
    .block-container {{
        padding: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin: 0 auto !important;
        max-width: 100vw !important;
        width: 100vw !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        background: {PAGE_BG} !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
    }}
    
    h1, h2, h3, .brand-headline, .brand-logo-text, .login-head h1 {{
        font-family: 'Outfit', sans-serif !important;
    }}

    [data-testid="stHeader"] {{ display:none !important; }}
    footer {{ display:none !important; }}
    #MainMenu {{ display:none !important; }}
    
    [data-testid="stAppViewBlockContainer"] > div {{
        height: 100% !important;
    }}
    
    [data-testid="stAppViewBlockContainer"] [data-testid="stVerticalBlock"] {{
        gap: 0 !important;
        height: 100% !important;
        width: 100% !important;
    }}

    /* Outer layout split-screen shell */
    [data-testid='stHorizontalBlock']:has(.brand-inner) {{
        gap: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        min-height: 100vh !important;
        height: 100vh !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        overflow: hidden !important;
    }}
    
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] {{
        padding: 0 !important;
        margin: 0 !important;
        height: 100vh !important;
        min-height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        box-sizing: border-box !important;
    }}
    
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] > div,
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
        width: 100% !important;
        height: auto !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        margin: auto !important;
        padding: 0 !important;
    }}

    /* Compress Streamlit gaps and margins on login widgets */
    [data-testid='stHorizontalBlock']:has(.brand-inner) div[data-testid="stElementContainer"] {{
        margin-top: 0 !important;
        margin-bottom: 6px !important;
    }}
    
    [data-testid='stHorizontalBlock']:has(.brand-inner) [data-testid="stVerticalBlock"] {{
        gap: 6px !important;
    }}

    div[data-testid='stForm'] {{
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        width: 100% !important;
    }}

    /* ── LEFT — visual panel ── */
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(1) {{
        background: radial-gradient(circle at 0% 0%, #EFF6FF 0%, #FFFFFF 50%, #F0F9FF 100%);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 3vh 2vw !important;
        position: relative !important;
        overflow: hidden !important;
        border-right: 1px solid {BORDER_COLOR} !important;
        box-sizing: border-box !important;
    }}
    
    .brand-inner {{
        position: relative;
        z-index: 2;
        max-width: 360px;
        width: 100%;
        animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    
    .brand-logo {{
        display: inline-flex;
        align-items: center;
        align-self: flex-start;
        gap: 8px;
        font-size: 1rem;
        font-weight: 800;
        color: {PRIMARY_COLOR};
        letter-spacing: -0.02em;
        margin-bottom: 2vh;
        padding: 4px 10px;
        background: rgba(37, 99, 235, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(37, 99, 235, 0.08);
    }}
    
    .brand-logo-text {{
        font-weight: 700;
        color: #0F172A;
    }}
    
    .logo-svg {{
        display: block;
    }}

    .brand-headline {{
        font-size: 1.95rem;
        font-weight: 850;
        line-height: 1.15;
        color: #0F172A;
        letter-spacing: -0.03em;
        margin-bottom: 1vh;
    }}
    
    .brand-sub {{
        font-size: 0.88rem;
        color: {SEC_TEXT_COLOR};
        line-height: 1.45;
        margin-bottom: 2vh;
    }}
    
    .brand-illustration-wrapper {{
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 2vh;
    }}
    
    .hero-illustration {{
        width: auto !important;
        max-width: 280px;
        max-height: 18vh !important;
        display: block;
        animation: float-3 15s ease-in-out infinite alternate;
    }}
    
    .feat-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        width: 100%;
        box-sizing: border-box;
    }}
    
    .feat-card {{
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(226, 232, 240, 0.7) !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        height: auto !important;
        min-height: 76px !important;
        box-sizing: border-box !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 8px rgba(15, 23, 42, 0.01) !important;
    }}
    
    .feat-card:hover {{
        border-color: {PRIMARY_COLOR} !important;
        transform: translateY(-1.5px) !important;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.04) !important;
        background: rgba(255, 255, 255, 0.85) !important;
    }}
    
    .feat-icon {{
        width: 28px;
        height: 28px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem;
        margin-bottom: 6px;
        background: rgba(37, 99, 235, 0.06);
        color: {PRIMARY_COLOR};
        border: 1px solid rgba(37, 99, 235, 0.08);
        transition: all 0.25s ease;
    }}
    
    .feat-card:hover .feat-icon {{
        background: {PRIMARY_COLOR} !important;
        color: #fff !important;
        transform: scale(1.02);
    }}
    
    .feat-title {{
        font-weight: 700;
        color: #0F172A;
        font-size: 0.82rem;
        margin-bottom: 1px;
    }}
    
    .feat-desc {{
        font-size: 0.72rem;
        color: {SEC_TEXT_COLOR};
        line-height: 1.3;
    }}

    .floating-shape {{
        position: fixed !important;
        border-radius: 50% !important;
        pointer-events: none !important;
        z-index: 0 !important;
    }}
    .shape-1 {{
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(37, 99, 235, 0.05) 0%, rgba(37, 99, 235, 0) 70%);
        filter: blur(40px);
        top: -100px;
        left: -100px;
        animation: float-1 25s ease-in-out infinite;
    }}
    .shape-2 {{
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(96, 165, 250, 0.05) 0%, rgba(96, 165, 250, 0) 70%);
        filter: blur(50px);
        bottom: -100px;
        right: -100px;
        animation: float-2 30s ease-in-out infinite alternate;
    }}
    .shape-3 {{
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(14, 165, 233, 0.03) 0%, rgba(14, 165, 233, 0) 70%);
        filter: blur(30px);
        top: 30%;
        left: 40%;
        animation: float-3 20s ease-in-out infinite alternate;
    }}

    /* ── RIGHT — login panel ── */
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) {{
        background: radial-gradient(circle at 100% 100%, #EFF6FF 0%, #FFFFFF 70%, {PAGE_BG} 100%);
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 3vh 2vw !important;
        position: relative !important;
        box-sizing: border-box !important;
    }}
    
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) > [data-testid='stVerticalBlock'], 
    [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) > [data-testid='stVerticalBlockBorderWrapper'] > div > [data-testid='stVerticalBlock'] {{
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) saturate(120%) !important;
        -webkit-backdrop-filter: blur(25px) saturate(120%) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 20px !important;
        padding: 24px 32px !important; /* Compact wrapping padding */
        box-shadow: 
            0 4px 30px rgba(0, 0, 0, 0.02),
            0 24px 60px rgba(15, 23, 42, 0.08),
            inset 0 1px 1px rgba(255, 255, 255, 0.8) !important;
        width: 100% !important;
        max-width: 500px !important; /* Increased width to 500px */
        box-sizing: border-box !important;
        animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) !important;
        z-index: 2 !important;
        margin: auto !important;
        height: auto !important;
        min-height: 0 !important;
    }}

    .login-head {{
        text-align: center;
        margin-bottom: 12px;
    }}
    
    .brand-logo-container {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-bottom: 6px;
    }}
    .brand-logo-icon {{
        font-size: 1.45rem;
    }}
    .brand-logo-name {{
        font-family: 'Outfit', sans-serif;
        font-weight: 900;
        font-size: 1.25rem;
        color: #0F172A;
        letter-spacing: -0.025em;
    }}
    
    .login-head h1 {{
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.025em;
        margin: 0 0 2px 0;
    }}
    
    .login-head p {{
        font-size: 0.78rem;
        color: {SEC_TEXT_COLOR};
        margin: 0;
    }}

    [data-testid='stTextInput'] label {{
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        margin-bottom: 4px !important;
    }}
    
    [data-testid="stTextInput"] > div {{
        position: relative !important;
    }}

    [data-testid="stTextInput"] input {{
        background: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        padding: 0 44px 0 36px !important; /* 44px right padding prevents overlap with eye button */
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        height: 42px !important; /* Consistent height */
        line-height: 42px !important; /* Vertically centered */
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}
    
    [data-testid="stTextInput"] input::placeholder {{
        color: #94A3B8 !important;
        opacity: 0.8 !important;
    }}
    
    [data-testid="stTextInput"] input:hover {{
        border-color: #94A3B8 !important;
    }}
    
    [data-testid="stTextInput"] input:focus {{
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3.5px rgba(37, 99, 235, 0.12) !important;
        outline: none !important;
        background: #FFFFFF !important;
    }}
    
    [data-testid="stTextInput"] input:disabled {{
        background: rgba(241, 245, 249, 0.8) !important;
        color: {TEXT_COLOR} !important;
        cursor: not-allowed !important;
    }}
    
    [data-testid="stTextInput"] input[aria-label="Email Address"] {{
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMyNTYzRUIiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNNCA0aDE2YzEuMSAwIDIgLjkgMiAydjEyYzAgMS4xLS45IDItMiAySDRjLTEuMSAwLTItLjktMi0yVjZjMC0xLjEuOS0yIDItMnoiLz48cG9seWxpbmUgcG9pbnRzPSIyMiw2IDEyLDEzIDIsNiIvPjwvc3ZnPg==");
        background-repeat: no-repeat;
        background-position: 12px center;
        background-size: 16px;
    }}
    
    [data-testid="stTextInput"] input[aria-label="Password"] {{
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMyNTYzRUIiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cmVjdCB4PSIzIiB5PSIxMSIgd2lkdGg9IjE4IiBoZWlnaHQ9IjExIiByeD0iMiIgcnk9IjIiLz48cGF0aCBkPSJNNyAxMVY3YTUgNSAwIDAgMSAxMCAwdjQiLz48L3N2Zz4=");
        background-repeat: no-repeat;
        background-position: 12px center;
        background-size: 16px;
    }}

    /* Align and style native eye toggle icon button cleanly */
    [data-testid="stTextInput"] button {{
        position: absolute !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        right: 12px !important;
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 24px !important;
        width: 24px !important;
        padding: 0 !important;
        margin: 0 !important;
        z-index: 10 !important;
    }}

    /* Hide 'Press Enter to submit form' instructions overlay */
    [data-testid="InputInstructions"],
    .stInputInstructions,
    .st-ae,
    div[data-testid="InputInstructions"],
    span[data-testid="InputInstructions"],
    p[data-testid="InputInstructions"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}

    /* Custom styles for Remember me / Show Password / Forgot row */
    [data-testid="stForm"] + [data-testid="stHorizontalBlock"],
    [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
        margin-top: 2px !important;
        margin-bottom: 8px !important;
        gap: 0 !important;
    }}
    
    [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) > div[data-testid="stColumn"] {{
        width: auto !important;
        min-width: 0 !important;
        flex: 1 1 auto !important;
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    [data-testid="stCheckbox"] {{
        margin: 0 !important;
    }}
    
    [data-testid="stCheckbox"] label {{
        padding: 0 !important;
    }}
    
    [data-testid="stCheckbox"] label p {{
        font-size: 0.76rem !important;
        color: {SEC_TEXT_COLOR} !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
    }}
    
    [data-testid="stCheckbox"] input {{
        accent-color: {PRIMARY_COLOR} !important;
        width: 14px !important;
        height: 14px !important;
    }}
    
    .forgot-link {{
        font-size: 0.76rem;
        color: {PRIMARY_COLOR};
        text-decoration: none;
        font-weight: 600;
        white-space: nowrap;
    }}
    
    .forgot-link:hover {{
        color: {HOVER_COLOR};
        text-decoration: underline;
    }}

    [data-testid='stFormSubmitButton'] > button {{
        background: linear-gradient(135deg, {PRIMARY_COLOR}, {HOVER_COLOR}) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-weight: 650 !important;
        height: 38px !important;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.18) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: relative !important;
        overflow: hidden !important;
        letter-spacing: 0.01em;
        cursor: pointer;
    }}
    
    [data-testid='stFormSubmitButton'] > button:hover:not(:disabled) {{
        box-shadow: 0 5px 12px rgba(37, 99, 235, 0.25) !important;
        transform: translateY(-1px) !important;
    }}
    
    [data-testid="stFormSubmitButton"] > button:active:not(:disabled) {{
        transform: translateY(0) !important;
    }}

    .divider {{
        display: flex;
        align-items: center;
        margin: 1.5vh 0;
        color: {SEC_TEXT_COLOR};
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
    }}
    
    .divider::before, .divider::after {{
        content: "";
        flex: 1;
        height: 1px;
        background: #E2E8F0;
    }}
    
    .divider span {{
        padding: 0 8px;
    }}

    .social-row {{
        display: flex;
        gap: 10px;
        width: 100%;
        margin-bottom: 6px;
    }}

    .social-btn {{
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1.5px solid #E2E8F0;
        background: rgba(255, 255, 255, 0.6);
        color: #0F172A;
        font-size: 0.8rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        cursor: pointer;
    }}
    
    .social-btn:hover {{
        background: #fff;
        border-color: {PRIMARY_COLOR};
        box-shadow: 0 3px 8px rgba(15, 23, 42, 0.02);
        transform: translateY(-0.5px);
    }}
    
    .social-btn svg, .social-btn img {{
        width: 14px;
        height: 14px;
    }}

    .register-row {{
        text-align: center;
        margin-top: 1.5vh;
        font-size: 0.8rem;
        color: {SEC_TEXT_COLOR};
    }}
    
    .register-row a {{
        color: {PRIMARY_COLOR};
        font-weight: 700;
        text-decoration: none;
        margin-left: 3px;
        transition: color 0.2s ease;
    }}
    
    .register-row a:hover {{
        color: {HOVER_COLOR};
        text-decoration: underline;
    }}

    .login-error {{
        display: flex;
        align-items: center;
    }}
    
    .login-error-box {{
        width: 100%;
        background: {ERR_BG};
        border: 1px solid {ERR_BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 6px;
        animation: fadeIn 0.3s ease;
    }}
    
    .login-error-box span.msg {{
        color: {ERR_COLOR};
        font-size: 0.78rem;
        font-weight: 600;
    }}

    .login-footer {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 3px;
        margin-top: 1.5vh;
        font-size: 0.68rem;
        color: {SEC_TEXT_COLOR};
        border-top: 1px solid #E2E8F0;
        padding-top: 1vh;
        width: 100%;
        text-align: center;
    }}

    /* Hide elements that are just for code execution injection */
    div[data-testid="stElementContainer"]:has(style),
    div[data-testid="stElementContainer"]:has(iframe) {{
        display: none !important;
    }}

    /* Responsive/Height adjustments */
    @media (max-height: 700px) {{
        .login-head {{ margin-bottom: 1.5vh; }}
        .login-logo {{ width: 32px; height: 32px; font-size: 0.9rem; margin-bottom: 0.5vh; }}
        .login-head h1 {{ font-size: 1.25rem; }}
        .login-head p {{ font-size: 0.76rem; }}
        [data-testid="stTextInput"] input {{ height: 34px !important; font-size: 0.8rem !important; }}
        [data-testid='stFormSubmitButton'] > button {{ height: 34px !important; font-size: 0.8rem !important; }}
        .divider {{ margin: 1vh 0; }}
        .social-btn {{ padding: 6px 8px !important; font-size: 0.76rem !important; }}
        .register-row {{ margin-top: 1vh; font-size: 0.76rem; }}
        .login-footer {{ margin-top: 1vh; padding-top: 0.8vh; font-size: 0.64rem; }}
        .feat-card {{ min-height: 68px !important; padding: 8px 10px !important; }}
        .brand-headline {{ font-size: 1.7rem; }}
        .brand-logo {{ margin-bottom: 1.5vh; }}
        .hero-illustration {{ max-height: 15vh !important; }}
    }}

    @media (max-width: 1024px) {{
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(1) {{ padding: 3vh 2vw !important; }}
        .brand-headline {{ font-size: 1.8rem; }}
        .hero-illustration {{ max-width: 240px; }}
        .feat-grid {{ gap: 8px; }}
        .feat-card {{ padding: 8px !important; min-height: 70px !important; }}
    }}
    
    @media (max-width: 768px) {{
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], section[data-testid="stMain"] {{
            overflow: auto !important;
            height: auto !important;
        }}
        .stApp .main .block-container,
        .stApp [data-testid="stMain"] .block-container,
        [data-testid="stAppViewContainer"] .main .block-container,
        [data-testid="stAppViewBlockContainer"],
        .block-container {{
            height: auto !important;
            min-height: 100vh !important;
            max-height: none !important;
            overflow: auto !important;
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) {{
            flex-direction: column !important;
            height: auto !important;
            min-height: 100vh !important;
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] {{
            width: 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
            flex: 0 0 auto !important;
            height: auto !important;
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] > div,
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
            height: auto !important;
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(1) {{ 
            display: none !important; 
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) {{ 
            min-height: 100vh !important; 
            padding: 30px 16px !important; 
        }}
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) > [data-testid='stVerticalBlock'], 
        [data-testid='stHorizontalBlock']:has(.brand-inner) > div[data-testid='stColumn']:nth-of-type(2) > [data-testid='stVerticalBlockBorderWrapper'] > div > [data-testid='stVerticalBlock'] {{ 
            width: 100% !important;
            max-width: 380px !important;
            min-width: 0 !important;
            padding: 32px 24px !important; 
            border-radius: 20px !important; 
            margin: auto !important;
        }}
    }}
    </style>
    """
    st.html(login_style)

    left_col, right_col = st.columns([45, 55], gap="small")

    with left_col:
        st.html(textwrap.dedent("""
        <div class="floating-shape shape-1"></div>
        <div class="floating-shape shape-2"></div>
        <div class="floating-shape shape-3"></div>
        <div class="brand-inner">
            <div class="brand-logo" style="background:transparent; border:none; padding:0; margin-bottom:12px;">
                <span style="font-size: 1.6rem; margin-right: 4px;">💎</span>
                <span style="font-family:'Outfit',sans-serif; font-weight:900; font-size:1.45rem; color:#0F172A; letter-spacing:-0.03em;">FintechHub</span>
            </div>
            <div class="brand-headline" style="font-size: 2.20rem; line-height:1.2; margin-top:14px; margin-bottom:10px;">Next-Gen Market Simulator & AI Insights</div>
            <div class="brand-sub" style="font-size: 0.95rem; line-height: 1.5; color: #4B5563; margin-bottom: 24px;">
                Empowering retail investors with professional-grade portfolio visualization, live indices metrics, and predictive sector trends.
            </div>
            
            <div class="brand-illustration-wrapper">
                <svg class="hero-illustration" width="320" height="190" viewBox="0 0 380 230" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="illustrationGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#2563EB" stop-opacity="0.15" />
                            <stop offset="100%" stop-color="#60A5FA" stop-opacity="0.02" />
                        </linearGradient>
                        <linearGradient id="chartLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#2563EB" />
                            <stop offset="100%" stop-color="#60A5FA" />
                        </linearGradient>
                        <linearGradient id="chartAreaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#60A5FA" stop-opacity="0.25" />
                            <stop offset="100%" stop-color="#60A5FA" stop-opacity="0.0" />
                        </linearGradient>
                        <filter id="shadowFilter" x="-10%" y="-10%" width="120%" height="120%">
                            <feDropShadow dx="0" dy="12" stdDeviation="10" flood-color="#0F172A" flood-opacity="0.04" />
                        </filter>
                    </defs>
                    <!-- Background Grid Lines -->
                    <g opacity="0.3">
                        <line x1="20" y1="20" x2="360" y2="20" stroke="#E2E8F0" stroke-dasharray="4 4" />
                        <line x1="20" y1="70" x2="360" y2="70" stroke="#E2E8F0" stroke-dasharray="4 4" />
                        <line x1="20" y1="120" x2="360" y2="120" stroke="#E2E8F0" stroke-dasharray="4 4" />
                        <line x1="20" y1="170" x2="360" y2="170" stroke="#E2E8F0" stroke-dasharray="4 4" />
                    </g>
                    <!-- Container -->
                    <rect x="15" y="15" width="350" height="200" rx="20" fill="white" fill-opacity="0.65" stroke="#E2E8F0" stroke-width="1.5" filter="url(#shadowFilter)" />
                    <!-- Browser Controls -->
                    <circle cx="38" cy="34" r="5" fill="#FF5F56" />
                    <circle cx="52" cy="34" r="5" fill="#FFBD2E" />
                    <circle cx="66" cy="34" r="5" fill="#27C93F" />
                    <!-- Tab -->
                    <rect x="90" y="27" width="90" height="14" rx="7" fill="#F1F5F9" />
                    <!-- Chart Graph -->
                    <path d="M 30 160 Q 70 120 110 135 T 190 85 T 270 110 T 350 70" fill="none" stroke="url(#chartLineGrad)" stroke-width="3" stroke-linecap="round" />
                    <path d="M 30 160 Q 70 120 110 135 T 190 85 T 270 110 T 350 70 L 350 190 L 30 190 Z" fill="url(#chartAreaGrad)" />
                    <!-- Nodes -->
                    <circle cx="190" cy="85" r="5" fill="#2563EB" stroke="white" stroke-width="1.5" />
                    <circle cx="270" cy="110" r="5" fill="#60A5FA" stroke="white" stroke-width="1.5" />
                    <circle cx="350" cy="70" r="5" fill="#2563EB" stroke="white" stroke-width="1.5" />
                    <!-- Metric Box -->
                    <g transform="translate(195, 125)">
                        <rect x="0" y="0" width="140" height="65" rx="12" fill="white" fill-opacity="0.9" stroke="#E2E8F0" stroke-width="1" />
                        <text x="14" y="22" fill="#64748B" font-family="'Inter', sans-serif" font-size="10" font-weight="600" letter-spacing="0.02em">PORTFOLIO YIELD</text>
                        <text x="14" y="44" fill="#10B981" font-family="'Outfit', sans-serif" font-size="16" font-weight="700">+24.8%</text>
                    </g>
                </svg>
            </div>

            <div class="feat-grid">
                <div class="feat-card">
                    <div class="feat-icon">📈</div>
                    <div class="feat-title">Live Market</div>
                    <div class="feat-desc">Real-time NSE & BSE Updates</div>
                </div>
                <div class="feat-card">
                    <div class="feat-icon">🤖</div>
                    <div class="feat-title">AI Analytics</div>
                    <div class="feat-desc">AI Powered Insights</div>
                </div>
                <div class="feat-card">
                    <div class="feat-icon">💼</div>
                    <div class="feat-title">Portfolio Tracking</div>
                    <div class="feat-desc">Monitor Holdings Securely</div>
                </div>
                <div class="feat-card">
                    <div class="feat-icon">🔒</div>
                    <div class="feat-title">Bank Grade Security</div>
                    <div class="feat-desc">256-bit Encryption</div>
                </div>
            </div>
        </div>
        """))

    with right_col:
        st.html(textwrap.dedent("""
        <div class="login-head">
            <div class="brand-logo-container">
                <div class="brand-logo-icon">💎</div>
                <span class="brand-logo-name">FintechHub</span>
            </div>
            <h1>Welcome Back 👋</h1>
            <p>Sign in to access your dashboard</p>
        </div>
        """))

        with st.form("login_form", clear_on_submit=False):
            email_input = st.text_input(
                "Email Address",
                placeholder="Enter your email address",
                key="email_field",
                value="nitin@fintech.com",
            )

            pwd_input = st.text_input(
                "Password",
                type="password", # Streamlit natively puts eye toggle inside password inputs
                placeholder="Enter your password",
                key="pwd_field",
                value="",
            )

            login_btn = st.form_submit_button(
                "Sign In",
                use_container_width=True,
            )

        # Remember Me and Forgot Password row (aligned left/right)
        opt_col1, opt_col2 = st.columns([1, 1])
        with opt_col1:
            st.checkbox("Remember Me", key="remember_me_val")
        with opt_col2:
            st.markdown('<div style="text-align:right; font-size:0.8rem; margin-top:4px; padding-right:4px;"><a href="#" class="forgot-link">Forgot Password?</a></div>', unsafe_allow_html=True)

        if login_btn:
            with st.spinner("Verifying credentials..."):
                if email_input.strip().lower() != "nitin@fintech.com":
                    st.session_state.login_failed_msg = "Invalid email address."
                    st.session_state.login_failed = True
                elif check_password(pwd_input, CORRECT_HASH):
                    st.session_state.authenticated = True
                    st.session_state.login_failed = False
                    st.session_state.login_failed_msg = ""
                else:
                    st.session_state.login_failed_msg = "Invalid password. Please try again."
                    st.session_state.login_failed = True
            st.rerun()

        # Reserved-height error slot — prevents layout shift whether or not an error is shown
        error_msg = st.session_state.get("login_failed_msg", "")
        if st.session_state.get("login_failed") and error_msg:
            st.markdown(f'<div class="login-error"><div class="login-error-box">❌<span class="msg">{error_msg}</span></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="login-error"></div>', unsafe_allow_html=True)

    st.stop()

# ── IST / market helpers ──────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)


def calculate_streak(history):
    """
    Trade history se consecutive profitable days ka streak nikalo.
    Har din ke saare SELL trades ka net P&L check karo —
    agar positive hai to streak continue, warna break.
    """
    sell_trades = [t for t in history if t.get("Action") == "SELL" and t.get("P&L") is not None]
    if not sell_trades:
        return 0, 0, 0  # streak, total_profitable_days, total_trade_days

    # Date → daily net P&L
    from collections import defaultdict
    daily_pnl = defaultdict(float)
    for t in sell_trades:
        try:
            day_key = datetime.strptime(t["Time"], "%d %b %Y %I:%M %p").strftime("%Y-%m-%d")
            daily_pnl[day_key] += t["P&L"]
        except Exception:
            continue

    if not daily_pnl:
        return 0, 0, 0

    sorted_days = sorted(daily_pnl.keys(), reverse=True)  # latest pehle
    streak = 0
    for day in sorted_days:
        if daily_pnl[day] > 0:
            streak += 1
        else:
            break

    profitable_days = sum(1 for v in daily_pnl.values() if v > 0)
    total_days      = len(daily_pnl)
    return streak, profitable_days, total_days

# ── Aaj Ka Trade insight generate karo ────────────────────────────────────
def get_aaj_ka_trade_insight(rows, history, streak):
    """
    Portfolio data se ek random-daily insight pick karo.
    Seed = aaj ki date, so roz naya card dikhega.
    """
    import random, hashlib
    today_seed = datetime.now().strftime("%Y-%m-%d")
    rng = random.Random(int(hashlib.md5(today_seed.encode()).hexdigest(), 16))

    insights = []

    # Holding period insights
    if rows:
        oldest = max(rows, key=lambda r: r.get("held_days") or 0)
        newest = min(rows, key=lambda r: r.get("held_days") or 9999)
        if oldest.get("held_days"):
            insights.append(("📅", f"Aapka sabse purana holding <b>{oldest['name']}</b> hai — {oldest['held_days']} din se hold kiya hai!"))
        if newest.get("held_days") is not None:
            insights.append(("🆕", f"<b>{newest['name']}</b> aapki newest holding hai — sirf {newest.get('held_days', 0)} din purani."))

    # Best/worst performer
    if rows:
        best  = max(rows, key=lambda r: r["pnl_p"])
        worst = min(rows, key=lambda r: r["pnl_p"])
        if best["pnl_p"] > 0:
            insights.append(("🏆", f"Aapka <b>best performer</b> aaj <b>{best['name']}</b> hai — {best['pnl_p']:+.1f}% return!"))
        if worst["pnl_p"] < 0:
            insights.append(("⚠️", f"<b>{worst['name']}</b> portfolio mein sabse zyada under-performing hai ({worst['pnl_p']:+.1f}%). Revisit karein?"))

    # Trade history insights
    sell_trades = [t for t in history if t.get("Action") == "SELL" and t.get("P&L") is not None]
    if sell_trades:
        profitable = sum(1 for t in sell_trades if t["P&L"] > 0)
        win_rate   = profitable / len(sell_trades) * 100
        insights.append(("📊", f"Aapka overall <b>win rate</b> {win_rate:.0f}% hai — {profitable}/{len(sell_trades)} profitable trades!"))

        # Last week trades
        try:
            week_ago = ist_now() - timedelta(days=7)
            recent = [t for t in sell_trades if datetime.strptime(t["Time"], "%d %b %Y %I:%M %p") >= week_ago]
            if recent:
                rp = sum(1 for t in recent if t["P&L"] > 0)
                insights.append(("📅", f"Is hafte aapne <b>{len(recent)} trades</b> kiye — {rp} profitable rahe!"))
        except Exception:
            pass

        # Best single trade
        best_trade = max(sell_trades, key=lambda t: t["P&L"])
        if best_trade["P&L"] > 0:
            insights.append(("💰", f"Aapka <b>best trade</b> tha {best_trade.get('Name', best_trade['Ticker'])} — ₹{best_trade['P&L']:,.0f} profit!"))

    # Streak-based insight
    if streak >= 3:
        insights.append(("🔥", f"Kya baat hai! Aap {streak} din se continuously profitable trade kar rahe ho! Streak alive rakho!"))
    elif streak == 0 and sell_trades:
        insights.append(("💪", f"Streak toot gayi, koi baat nahi — har trader ke kuch aisa din aate hain. Dobara focus karo!"))

    # Holdings count
    if rows:
        insights.append(("🗂️", f"Aapke portfolio mein abhi <b>{len(rows)} stocks</b> hain. Diversification ka dhyan rakho!"))

    # LTCG/STCG insight
    lt_stocks = [r for r in rows if r.get("term_label") == "Long Term"]
    if lt_stocks:
        insights.append(("📈", f"<b>{lt_stocks[0]['name']}</b> ab Long Term holding ban gaya hai — LTCG benefit milega tax mein!"))

    # Cash utilisation
    if rows:
        cash_pct = st.session_state.pt_cash / (st.session_state.pt_cash + sum(r["cur_v"] for r in rows)) * 100
        if cash_pct > 50:
            insights.append(("💵", f"Aapka {cash_pct:.0f}% capital abhi cash mein hai — koi achha opportunity dhundhne ka waqt!"))
        elif cash_pct < 10:
            insights.append(("⚡", f"Portfolio fully deployed hai — sirf {cash_pct:.0f}% cash bacha hai. Risk manage karo!"))

    if not insights:
        insights.append(("💡", "Roz trade karo, roz seekho — market sabse bada teacher hai!"))

    emoji, text = rng.choice(insights)
    return emoji, text

def get_calendar_events():
    """
    Shared economic calendar events — Calendar tab aur Portfolio tab (results
    season reminder) dono yahi function use karte hain, taaki data duplicate
    na ho. Static curated events for 2025-2026.
    """
    from datetime import date as _date
    BLUE = "#3b82f6"; GREEN = "#27ae60"; PURPLE = "#a78bfa"; AMBER = "#f59e0b"
    return [
        # ── RBI MPC Meetings ──
        {"date": _date(2025,  4,  9), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "Monetary Policy Committee — repo rate decision"},
        {"date": _date(2025,  6,  6), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "Bi-monthly MPC meeting — interest rate review"},
        {"date": _date(2025,  8,  8), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "August MPC — inflation & growth outlook"},
        {"date": _date(2025, 10,  8), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "October MPC — pre-festive policy review"},
        {"date": _date(2025, 12,  5), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "December MPC — year-end policy decision"},
        {"date": _date(2026,  2,  7), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "February MPC — post-budget policy review"},
        {"date": _date(2026,  4,  9), "type": "RBI",      "icon": "🏦", "color": BLUE,
         "title": "RBI MPC Policy Meeting", "desc": "April MPC — new fiscal year review"},

        # ── F&O Expiry (last Thursday of each month) ──
        {"date": _date(2025,  6, 26), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — June 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025,  7, 31), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — July 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025,  8, 28), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Aug 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025,  9, 25), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Sep 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025, 10, 30), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Oct 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025, 11, 27), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Nov 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2025, 12, 25), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Dec 2025", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2026,  1, 29), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Jan 2026", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2026,  2, 26), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Feb 2026", "desc": "Nifty & BankNifty monthly contracts expire"},
        {"date": _date(2026,  3, 26), "type": "FNO",      "icon": "⚡", "color": AMBER,
         "title": "F&O Monthly Expiry — Mar 2026", "desc": "Nifty & BankNifty monthly contracts expire"},

        # ── Results Season ──
        {"date": _date(2025,  7, 11), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q1 FY26 Results Season Starts", "desc": "TCS, Infosys, HDFC Bank — IT results first"},
        {"date": _date(2025,  7, 14), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "TCS Q1 FY26 Results", "desc": "TCS quarterly earnings announcement"},
        {"date": _date(2025,  7, 17), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Infosys Q1 FY26 Results", "desc": "Infosys quarterly earnings + guidance"},
        {"date": _date(2025,  7, 19), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "HDFC Bank Q1 FY26 Results", "desc": "HDFC Bank quarterly earnings"},
        {"date": _date(2025, 10, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q2 FY26 Results Season Starts", "desc": "July-September quarter earnings"},
        {"date": _date(2026,  1, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q3 FY26 Results Season Starts", "desc": "October-December quarter earnings"},
        {"date": _date(2026,  4, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q4 FY26 Results Season Starts", "desc": "Full year FY26 earnings — annual results"},
        {"date": _date(2026,  7, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q1 FY27 Results Season Starts", "desc": "April-June 2026 quarter — TCS, Infosys lead (mid-July)"},
        {"date": _date(2026, 10, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q2 FY27 Results Season Starts", "desc": "July-September 2026 quarter — festive season commentary"},
        {"date": _date(2027,  1, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q3 FY27 Results Season Starts", "desc": "October-December 2026 quarter — sets budget narrative"},
        {"date": _date(2027,  4, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q4 FY27 Results Season Starts", "desc": "January-March 2027 quarter — full year FY27 annual results"},
        {"date": _date(2027,  7, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q1 FY28 Results Season Starts", "desc": "April-June 2027 quarter earnings"},
        {"date": _date(2027, 10, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q2 FY28 Results Season Starts", "desc": "July-September 2027 quarter earnings"},
        {"date": _date(2028,  1, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q3 FY28 Results Season Starts", "desc": "October-December 2027 quarter earnings"},
        {"date": _date(2028,  4, 10), "type": "RESULTS",  "icon": "📊", "color": GREEN,
         "title": "Q4 FY28 Results Season Starts", "desc": "January-March 2028 quarter — full year FY28 annual results"},

        # ── Budget ──
        {"date": _date(2026,  2,  1), "type": "BUDGET",   "icon": "💼", "color": PURPLE,
         "title": "Union Budget 2026-27", "desc": "Finance Minister presents Annual Budget — market mover"},

        # ── Market Holidays ──
        {"date": _date(2025,  8, 15), "type": "HOLIDAY",  "icon": "🇮🇳", "color": "#f43f5e",
         "title": "Independence Day — Market Closed", "desc": "NSE/BSE closed"},
        {"date": _date(2025, 10,  2), "type": "HOLIDAY",  "icon": "🇮🇳", "color": "#f43f5e",
         "title": "Gandhi Jayanti — Market Closed", "desc": "NSE/BSE closed"},
        {"date": _date(2025, 10, 24), "type": "HOLIDAY",  "icon": "🪔", "color": "#f43f5e",
         "title": "Diwali Muhurat Trading", "desc": "Special 1-hour Muhurat Trading session"},
        {"date": _date(2025, 11, 5),  "type": "HOLIDAY",  "icon": "🇮🇳", "color": "#f43f5e",
         "title": "Diwali Laxmi Puja — Market Closed", "desc": "NSE/BSE closed"},
        {"date": _date(2025, 11, 15), "type": "HOLIDAY",  "icon": "🇮🇳", "color": "#f43f5e",
         "title": "Gurunanak Jayanti — Market Closed", "desc": "NSE/BSE closed"},
        {"date": _date(2025, 12, 25), "type": "HOLIDAY",  "icon": "🎄", "color": "#f43f5e",
         "title": "Christmas — Market Closed", "desc": "NSE/BSE closed"},
        {"date": _date(2026,  1, 26), "type": "HOLIDAY",  "icon": "🇮🇳", "color": "#f43f5e",
         "title": "Republic Day — Market Closed", "desc": "NSE/BSE closed"},

        # ── GDP / Macro Data ──
        {"date": _date(2025,  8, 29), "type": "MACRO",    "icon": "📈", "color": "#06b6d4",
         "title": "India GDP Q1 FY26 Data", "desc": "Ministry of Statistics — GDP growth announcement"},
        {"date": _date(2025, 11, 28), "type": "MACRO",    "icon": "📈", "color": "#06b6d4",
         "title": "India GDP Q2 FY26 Data", "desc": "GDP growth rate for July-September 2025"},
        {"date": _date(2026,  2, 28), "type": "MACRO",    "icon": "📈", "color": "#06b6d4",
         "title": "India GDP Q3 FY26 Data", "desc": "GDP growth rate for October-December 2025"},
    ]

def get_ipo_data():
    """
    IPO Tracker — Mainboard + SME IPOs ka curated/static reference data
    (jaise get_calendar_events — live GMP/subscription % nahi, sirf
    confirmed dates/price-band). Live GMP/subscription ke liye broker
    app ya IPO platform (InvestorGain, Chittorgarh) check karna better hai,
    kyunki wo minute-by-minute badalta hai.
    """
    from datetime import date as _date
    return [
        {"name": "Aastha Spintex", "exchange": "Mainboard", "sector": "Textiles",
         "price_low": 125, "price_high": 136, "lot_size": 1000, "issue_size_cr": 84,
         "open_date": _date(2026, 6, 29), "close_date": _date(2026, 7, 1),
         "listing_date": _date(2026, 7, 6)},

        {"name": "Twinkle Papers", "exchange": "SME", "sector": "Paper & Packaging",
         "price_low": 64, "price_high": 69, "lot_size": 2000, "issue_size_cr": 28,
         "open_date": _date(2026, 6, 29), "close_date": _date(2026, 7, 1),
         "listing_date": _date(2026, 7, 6)},

        {"name": "Adon Agro Commodities", "exchange": "SME", "sector": "Agro/FMCG",
         "price_low": 66, "price_high": 70, "lot_size": 2000, "issue_size_cr": 22,
         "open_date": _date(2026, 6, 29), "close_date": _date(2026, 7, 1),
         "listing_date": _date(2026, 7, 6)},

        {"name": "Atharva Polyplast", "exchange": "SME", "sector": "Plastics/Materials",
         "price_low": 55, "price_high": 60, "lot_size": 2000, "issue_size_cr": 19,
         "open_date": _date(2026, 6, 30), "close_date": _date(2026, 7, 2),
         "listing_date": _date(2026, 7, 7)},

        {"name": "Sampark India Logistics", "exchange": "SME", "sector": "Logistics",
         "price_low": 80, "price_high": 84, "lot_size": 1600, "issue_size_cr": 31,
         "open_date": _date(2026, 6, 30), "close_date": _date(2026, 7, 2),
         "listing_date": _date(2026, 7, 7)},

        {"name": "Kratikal Tech", "exchange": "SME", "sector": "Cybersecurity/IT",
         "price_low": 128, "price_high": 135, "lot_size": 1000, "issue_size_cr": 56,
         "open_date": _date(2026, 6, 30), "close_date": _date(2026, 7, 2),
         "listing_date": _date(2026, 7, 7)},

        {"name": "Knack Packaging", "exchange": "Mainboard", "sector": "Packaging",
         "price_low": 161, "price_high": 170, "lot_size": 800, "issue_size_cr": 112,
         "open_date": _date(2026, 7, 1), "close_date": _date(2026, 7, 3),
         "listing_date": _date(2026, 7, 8)},
    ]

def is_market_open():
    now = ist_now()
    if now.weekday() >= 5:
        return False
    from datetime import date as _d
    MARKET_HOLIDAYS = {
        _d(2025,8,15),_d(2025,10,2),_d(2025,10,24),_d(2025,11,5),_d(2025,11,15),_d(2025,12,25),
        _d(2026,1,26),_d(2026,3,3),_d(2026,3,26),_d(2026,3,31),_d(2026,4,3),_d(2026,4,14),
        _d(2026,5,1),_d(2026,5,28),_d(2026,6,26),_d(2026,9,14),_d(2026,10,2),_d(2026,10,20),
        _d(2026,11,10),_d(2026,11,24),_d(2026,12,25),
    }
    if now.date() in MARKET_HOLIDAYS:
        return False
    o = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    c = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return o <= now <= c

def is_pre_open():
    """
    NSE/BSE pre-open session: 9:08 AM - 9:15 AM (order matching/price discovery).
    Same trading-day/holiday rules as is_market_open(), bas time-band alag hai.
    Zerodha/other brokers jaisa "PRE-OPEN" badge dikhane ke liye use hota hai.
    """
    now = ist_now()
    if now.weekday() >= 5:
        return False
    from datetime import date as _d
    MARKET_HOLIDAYS = {
        _d(2025,8,15),_d(2025,10,2),_d(2025,10,24),_d(2025,11,5),_d(2025,11,15),_d(2025,12,25),
        _d(2026,1,26),_d(2026,3,3),_d(2026,3,26),_d(2026,3,31),_d(2026,4,3),_d(2026,4,14),
        _d(2026,5,1),_d(2026,5,28),_d(2026,6,26),_d(2026,9,14),_d(2026,10,2),_d(2026,10,20),
        _d(2026,11,10),_d(2026,11,24),_d(2026,12,25),
    }
    if now.date() in MARKET_HOLIDAYS:
        return False
    p_start = now.replace(hour=9, minute=8,  second=0, microsecond=0)
    p_end   = now.replace(hour=9, minute=15, second=0, microsecond=0)
    return p_start <= now < p_end

def process_target_orders():
    """
    Pending target orders ko check karo:
    - Agar target price hit ho gaya (market open hote hue) → auto execute (BUY/SELL)
    - Agar din khatam ho gaya (3:30 PM cross) aur target hit nahi hua → silently expire
    Yeh function har page load/refresh pe chalta hai taaki targets live track ho.
    """
    if not st.session_state.get("pt_targets"):
        return

    now = ist_now()
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    still_pending = []
    changed = False

    for tgt in st.session_state.pt_targets:
        tkr      = tgt["ticker"]
        action   = tgt["action"]      # "BUY" or "SELL"
        qty      = tgt["qty"]
        tgt_price = tgt["target_price"]
        placed_date = tgt["placed_date"]   # "%Y-%m-%d" — sirf aaj ke din valid hai

        # Purane din ka order (app khuli hi nahi thi 3:30 ke baad) — expire karo
        if placed_date != now.strftime("%Y-%m-%d"):
            changed = True
            continue

        q = get_index_quote(tkr)
        cur_price = q[0] if q else None

        triggered = False
        if cur_price is not None and is_market_open():
            if action == "BUY" and cur_price <= tgt_price:
                triggered = True
            elif action == "SELL" and cur_price >= tgt_price:
                triggered = True

        if triggered:
            if action == "BUY":
                cost = round(cur_price * qty, 2)
                if cost <= st.session_state.pt_cash:
                    holding = st.session_state.pt_holdings.get(tkr, {"shares": 0, "avg_price": 0.0})
                    new_shares = holding["shares"] + qty
                    new_avg    = round((holding["shares"] * holding["avg_price"] + cost) / new_shares, 2)
                    first_buy_date = holding.get("first_buy_date") or now.strftime("%Y-%m-%d")
                    st.session_state.pt_holdings[tkr] = {
                        "shares": new_shares, "avg_price": new_avg, "first_buy_date": first_buy_date
                    }
                    st.session_state.pt_cash = round(st.session_state.pt_cash - cost, 2)
                    st.session_state.pt_history.append({
                        "Action": "BUY", "Ticker": tkr, "Name": tgt["name"],
                        "Shares": qty, "Price": cur_price, "Value": cost, "P&L": None,
                        "Time": now.strftime("%d %b %Y %I:%M %p"),
                    })
                    changed = True
                else:
                    # Balance kaafi nahi — target ko pending hi rehne do, shayad cash badh jaye
                    still_pending.append(tgt)
            else:  # SELL
                holding = st.session_state.pt_holdings.get(tkr, {"shares": 0, "avg_price": 0.0})
                if holding["shares"] >= qty:
                    proceeds = round(cur_price * qty, 2)
                    pnl      = round((cur_price - holding["avg_price"]) * qty, 2)
                    remaining = holding["shares"] - qty
                    if remaining == 0:
                        del st.session_state.pt_holdings[tkr]
                    else:
                        st.session_state.pt_holdings[tkr]["shares"] = remaining
                    st.session_state.pt_cash = round(st.session_state.pt_cash + proceeds, 2)
                    st.session_state.pt_history.append({
                        "Action": "SELL", "Ticker": tkr, "Name": tgt["name"],
                        "Shares": qty, "Price": cur_price, "Value": proceeds, "P&L": pnl,
                        "Time": now.strftime("%d %b %Y %I:%M %p"),
                    })
                    changed = True
                else:
                    # Holdings kaafi nahi — pending hi rehne do
                    still_pending.append(tgt)
        elif now >= market_close:
            # 3:30 baj gaye, target hit nahi hua — silently expire karo
            changed = True
        else:
            still_pending.append(tgt)

    if changed:
        st.session_state.pt_targets = still_pending
        save_portfolio()

os.makedirs("output", exist_ok=True)

# ── CSS — Dynamic Glassmorphism Theme ──────────────────────────────────────────
if not st.session_state.dark_mode:
    css_vars = f"""
    :root {{
        --bg-color: #F7F9FC;
        --card-bg: rgba(255, 255, 255, 0.72);
        --border-color: rgba(255, 255, 255, 0.35);
        --text-color: #111827;
        --secondary-text: #6B7280;
        --muted-text: #94A3B8;
        --primary-blue: {PRIMARY_BLUE};
        --light-blue: {LIGHT_BLUE};
        --success-color: #16A34A;
        --danger-color: #DC2626;
        --warning-color: #F59E0B;
        --card-radius: 20px;
        --btn-radius: 14px;
        --input-radius: 14px;
        --modal-radius: 24px;
        --backdrop-blur: blur(20px);
        --box-shadow: 0 20px 50px rgba(15,23,42,.08);
        --box-shadow-hover: 0 30px 60px rgba(15,23,42,.12);
        --btn-hover-transform: translateY(-2px);
        --card-hover-transform: translateY(-4px);
        --font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --topbar-bg: rgba(255, 255, 255, 0.8);
        --bottom-nav-bg: rgba(255, 255, 255, 0.85);
        --scrolling-ticker-bg: rgba(255, 255, 255, 0.6);
        --input-bg: rgba(255, 255, 255, 0.6);
        --input-border: rgba(255, 255, 255, 0.4);
        --tab-list-bg: rgba(255, 255, 255, 0.5);
        --tab-active-bg: #ffffff;
        --scrollbar-thumb: rgba(15, 23, 42, 0.1);
        --hover-bg: rgba(15, 23, 42, 0.03);
        --row-border: rgba(15, 23, 42, 0.05);
        --btn-secondary-bg: rgba(255, 255, 255, 0.6);
        --btn-secondary-border: rgba(255, 255, 255, 0.4);
        --btn-secondary-color: #111827;
        --btn-danger-bg: rgba(220, 38, 38, 0.08);
        --btn-danger-border: rgba(220, 38, 38, 0.2);
        --btn-danger-color: #DC2626;
        --accent-gradient: {ACCENT_GRADIENT};
        --btn-primary-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
        --btn-primary-shadow-hover: 0 6px 20px rgba(37, 99, 235, 0.45);
        --card-padding: {CARD_PADDING};
        --element-gap: {ELEMENT_GAP};
        --table-padding: {TABLE_PADDING};
        --font-size-base: {FONT_SIZE_BASE};
    }}
    """
else:
    css_vars = f"""
    :root {{
        --bg-color: #0f1116;
        --card-bg: #1a1d27;
        --border-color: #2a2d3a;
        --text-color: #e8eaf0;
        --secondary-text: #8b90a0;
        --muted-text: #8b90a0;
        --primary-blue: {PRIMARY_BLUE};
        --light-blue: {LIGHT_BLUE};
        --success-color: #27ae60;
        --danger-color: #e74c3c;
        --warning-color: #f59e0b;
        --card-radius: 12px;
        --btn-radius: 12px;
        --input-radius: 8px;
        --modal-radius: 16px;
        --backdrop-blur: none;
        --box-shadow: none;
        --box-shadow-hover: none;
        --btn-hover-transform: none;
        --card-hover-transform: none;
        --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --topbar-bg: #1a1d27;
        --bottom-nav-bg: #1a1d27;
        --scrolling-ticker-bg: #0d0f17;
        --input-bg: #1a1d27;
        --input-border: #2a2d3a;
        --tab-list-bg: #1a1d27;
        --tab-active-bg: rgba(59, 130, 246, 0.15);
        --scrollbar-thumb: #2a2d3a;
        --hover-bg: #1e2130;
        --row-border: #1e2130;
        --btn-secondary-bg: #1a1d27;
        --btn-secondary-border: #2a2d3a;
        --btn-secondary-color: #e8eaf0;
        --btn-danger-bg: #330d0d;
        --btn-danger-border: #e74c3c;
        --btn-danger-color: #e74c3c;
        --accent-gradient: {ACCENT_GRADIENT};
        --btn-primary-shadow: none;
        --btn-primary-shadow-hover: none;
        --card-padding: {CARD_PADDING};
        --element-gap: {ELEMENT_GAP};
        --table-padding: {TABLE_PADDING};
        --font-size-base: {FONT_SIZE_BASE};
    }}
    """

st.markdown(f"""
<style>
{css_vars}

/* Glassmorphic Plotly Chart Container overrides */
div[data-testid="stPlotlyChart"] {{
    background: var(--card-bg) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 16px !important;
    padding: 12px 14px !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.04) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    transition: all 0.3s ease;
}}
div[data-testid="stPlotlyChart"]:hover {{
    border-color: var(--primary-blue) !important;
}}

@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stSidebar"],
[data-testid="stMain"], section.main {{
    background-color: var(--bg-color) !important;
    color: var(--text-color) !important;
    font-family: var(--font-family) !important;
    font-size: var(--font-size-base, 1rem) !important;
    transition: background-color 0.3s ease, color 0.3s ease;
}}

/* Premium Hover Lift & Transitive styles */
.premium-lift-hover {{
    transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.22s, border-color 0.22s !important;
}}
.premium-lift-hover:hover {{
    transform: translateY(-3px) !important;
    box-shadow: var(--box-shadow-hover) !important;
    border-color: var(--primary-blue) !important;
}}

/* Dynamic Tab Fade-in Animation */
.stTabs, [data-testid="stAppViewContainer"] {{
    animation: fadeIn 0.4s ease-out;
}}

/* Smooth scroll behavior */
html {{
    scroll-behavior: smooth;
}}
/* Hide default Streamlit header background/borders but keep collapsedControl clickable */
[data-testid="stHeader"] {{
    background-color: transparent !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    height: 0px !important;
    position: relative !important;
    overflow: hidden !important;
    pointer-events: none !important;
}}

/* Position the Streamlit status widget (Rerun / Always rerun / Stop) to the left of custom nav elements */
.stStatusWidget,
[data-testid="stStatusWidget"] {{
    position: fixed !important;
    top: 19px !important;
    right: 340px !important;
    z-index: 1000 !important;
    display: flex !important;
    align-items: center !important;
    height: 32px !important;
    margin: 0 !important;
    pointer-events: auto !important;
}}
/* Root cause of the top-right overlap: Streamlit's built-in "Deploy" button and
   toolbar (stAppToolbar) live inside stHeader and are absolutely positioned, so
   even at height:0 they were escaping the clipped header and rendering on top
   of our custom .profile-avatar / .nav-icon. Target the deploy control itself
   with stable, specific selectors (covers current + slightly older Streamlit
   versions) instead of a broad toolbar-wide hide, so nothing else in the
   native toolbar is affected beyond this one control. */
[data-testid="stAppToolbar"],
.stAppToolbar,
[data-testid="stAppDeployButton"],
[data-testid="stDeployButton"],
.stAppDeployButton,
.stDeployButton {{
    display: none !important;
}}
footer                            {{ display:none !important; }}
#MainMenu                         {{ display:none !important; }}

/* Style collapsed control as premium floating glass menu button */
[data-testid="collapsedControl"] {{
    position: fixed !important;
    top: 15px !important;
    left: 15px !important;
    z-index: 1001 !important;
    background: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 50% !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: var(--box-shadow) !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    transition: all 0.2s ease !important;
}}
[data-testid="collapsedControl"]:hover {{
    transform: scale(1.05) !important;
    border-color: var(--primary-blue) !important;
}}

/* ── SIDEBAR Redesign ── */
[data-testid="stSidebar"] {{
    background-color: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border-right: 1px solid var(--border-color) !important;
    box-shadow: var(--box-shadow) !important;
    width: 260px !important;
    transition: width 0.3s ease !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    width: 260px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{
    display: none !important;
}}

/* Sidebar navigation buttons custom styling */
[data-testid="stSidebar"] [data-testid="stButton"] button {{
    background-color: transparent !important;
    border: none !important;
    color: var(--secondary-text) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 12px 18px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    font-family: var(--font-family) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    margin: 3px 0 !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {{
    background-color: var(--hover-bg) !important;
    color: var(--text-color) !important;
    transform: translateX(4px) !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {{
    background: var(--accent-gradient) !important;
    color: #ffffff !important;
    box-shadow: var(--btn-primary-shadow) !important;
    transform: none !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {{
    color: #ffffff !important;
}}
.sidebar-logo {{
    font-family: var(--font-family) !important;
    font-size: 1.3rem;
    font-weight: 800;
    color: var(--primary-blue);
    padding: 0.5rem 1.1rem 1.5rem !important;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
}}

/* ── HEADER & BREADCRUMBS Redesign ── */
.top-nav-bar {{
    position: fixed;
    top: 0;
    left: 260px;
    right: 0;
    height: 70px;
    background: var(--topbar-bg);
    backdrop-filter: var(--backdrop-blur);
    -webkit-backdrop-filter: var(--backdrop-blur);
    border-bottom: 1px solid var(--border-color);
    z-index: 999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2.5rem;
    transition: all 0.3s ease;
}}
.nav-left {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.nav-left .logo {{
    font-weight: 800;
    font-size: 1.15rem;
    color: var(--primary-blue);
}}
.nav-left .divider {{
    color: var(--muted-text);
    font-weight: 300;
}}
.nav-left .page-title {{
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-color);
}}
.nav-center .search-box {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--input-bg);
    border: 1px solid var(--input-border);
    border-radius: 10px;
    padding: 6px 12px;
    width: 280px;
}}
.nav-center .search-box input {{
    border: none;
    background: transparent;
    outline: none;
    width: 100%;
    color: var(--text-color);
    font-size: 0.82rem;
}}
.nav-right {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 20px !important;
}}
.market-badge {{
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--tab-list-bg);
    border: 1px solid var(--border-color);
    padding: 5px 12px;
    border-radius: 20px;
    flex-shrink: 0;
    white-space: nowrap;
}}
.status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}}
.status-text {{
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--secondary-text);
    text-transform: uppercase;
}}
.nav-icon {{
    font-size: 1.1rem;
    cursor: pointer;
    color: var(--secondary-text);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    transition: background 0.18s ease, color 0.18s ease;
    flex-shrink: 0;
}}
.nav-icon:hover {{
    background: var(--tab-list-bg);
    color: var(--primary-blue);
}}
.profile-avatar {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent-gradient);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    cursor: pointer;
    flex-shrink: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
.profile-avatar:hover {{
    transform: scale(1.06);
    box-shadow: 0 4px 14px rgba(15,23,42,0.18);
}}

/* Profile Dropdown Container */
.profile-dropdown {{
    position: absolute !important;
    top: 45px !important;
    right: 0 !important;
    width: 220px !important;
    background: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important;
    display: none;
    flex-direction: column;
    padding: 8px 0 !important;
    z-index: 10002 !important;
    animation: fadeIn 0.2s ease-out;
    box-sizing: border-box !important;
    text-align: left !important;
}}
.profile-dropdown.open {{
    display: flex !important;
}}
.pd-header {{
    padding: 12px 16px !important;
    display: flex;
    flex-direction: column;
}}
.pd-name {{
    font-weight: 700;
    font-size: 0.88rem;
    color: var(--text-color);
}}
.pd-email {{
    font-size: 0.72rem;
    color: var(--secondary-text);
    margin-top: 2px;
}}
.pd-divider {{
    height: 1px;
    background: var(--border-color);
    margin: 6px 0 !important;
}}
.pd-item {{
    padding: 8px 16px !important;
    font-size: 0.82rem;
    color: var(--text-color);
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    display: flex;
    align-items: center;
    gap: 8px;
    box-sizing: border-box !important;
}}
.pd-item:hover {{
    background: var(--tab-list-bg);
    color: var(--primary-blue);
}}

/* Breadcrumbs */
.breadcrumbs {{
    margin-top: 10px;
    margin-bottom: 20px;
    font-size: 0.78rem;
    color: var(--secondary-text);
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.bc-root {{
    cursor: pointer;
}}
.bc-sep {{
    color: var(--muted-text);
}}
.bc-active {{
    color: var(--primary-blue);
    font-weight: 600;
}}

/* Spacing fixes for fixed elements & script/style wrappers */
div[data-testid="element-container"]:has(style),
div[data-testid="element-container"]:has(script) {{
    display: none !important;
}}

div[data-testid="element-container"]:has(.top-nav-bar),
div[data-testid="element-container"]:has(.ticker-wrap) {{
    height: 0px !important;
    min-height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    overflow: visible !important;
}}


/* Responsive Content padding */
@media (min-width: 992px) {{
    .block-container {{
        max-width: 1200px !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        padding-top: 110px !important;
        padding-bottom: 80px !important;
    }}
}}
@media (max-width: 991px) {{
    .top-nav-bar {{
        left: 0 !important;
        padding: 0 1rem !important;
    }}
    .block-container {{
        padding-top: 110px !important;
        padding-bottom: 80px !important;
    }}
}}

/* ── LIVE SCROLLING TICKER ── */
.ticker-wrap {{
    position: fixed !important;
    top: 70px !important;
    left: 260px !important;
    right: 0 !important;
    z-index: 998 !important;
    background: var(--scrolling-ticker-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border-bottom: 1px solid var(--border-color) !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    padding: 8px 0 !important;
    transition: left 0.3s ease !important;
}}
.ticker-track {{
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 35s linear infinite;
}}
.ticker-wrap:hover .ticker-track {{
    animation-play-state: paused;
}}
@keyframes ticker-scroll {{
    0%   {{ transform: translateX(0%); }}
    100% {{ transform: translateX(-50%); }}
}}
.ticker-item {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 0 28px;
    font-size: 0.85rem; font-weight: 600;
    border-right: 1px solid var(--border-color);
}}
.ticker-item .ti-name {{ color: var(--secondary-text); font-weight: 700; letter-spacing: .03em; }}
.ticker-item .ti-val  {{ color: var(--text-color); }}
.ticker-item .ti-up   {{ color: var(--success-color); }}
.ticker-item .ti-down {{ color: var(--danger-color); }}

/* ── BOTTOM NAV ── */
.bottom-nav {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
    background: var(--bottom-nav-bg);
    backdrop-filter: var(--backdrop-blur);
    -webkit-backdrop-filter: var(--backdrop-blur);
    border-top: 1px solid var(--border-color);
    display: flex; justify-content: space-around; align-items: center;
    padding: 8px 0 12px 0;
    box-shadow: 0 -10px 30px rgba(15,23,42,.03);
}}
.nav-item {{
    display:flex; flex-direction:column; align-items:center;
    font-size:0.7rem; color:var(--secondary-text); cursor:pointer;
    padding: 6px 18px; border-radius: var(--btn-radius);
    transition: all 0.2s ease;
    font-weight: 500;
}}
.nav-item:hover {{
    background: var(--hover-bg);
    color: var(--text-color);
}}
.nav-item.active {{ color: var(--primary-blue); font-weight: 700; background: rgba(37, 99, 235, 0.08); }}
.nav-item .nav-icon {{ font-size:1.35rem; margin-bottom:3px; }}

/* ── WATCHLIST ROWS ── */
.wl-row {{
    display:flex; justify-content:space-between; align-items:center;
    padding: 14px 20px;
    border-bottom: 1px solid var(--row-border);
    transition: all 0.2s ease;
}}
.wl-row:hover {{
    background: var(--hover-bg);
    transform: translateX(4px);
}}
.wl-name  {{ font-size:0.92rem; font-weight:600; color:var(--text-color); }}
.wl-ticker{{ font-size:0.72rem; color:var(--secondary-text); margin-top:2px; }}
.wl-price {{ font-size:0.98rem; font-weight:700; color:var(--text-color); text-align:right; }}
.wl-chg-g {{ font-size:0.78rem; color:var(--success-color); font-weight:600; text-align:right; }}
.wl-chg-r {{ font-size:0.78rem; color:var(--danger-color); font-weight:600; text-align:right; }}

/* ── SECTION TITLE ── */
.sec-title {{
    font-size:0.8rem; font-weight:700; color:var(--secondary-text);
    letter-spacing:0.1em; text-transform:uppercase;
    padding: 16px 20px 8px 20px;
    font-family: var(--font-family) !important;
}}

/* ── PREMIUM CARDS (PORTFOLIO, ORDER, ETC.) ── */
.port-card {{
    background: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--card-radius) !important;
    padding: 24px !important;
    margin: 12px 8px !important;
    box-shadow: var(--box-shadow) !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
}}
.port-card:hover {{
    transform: var(--card-hover-transform) !important;
    box-shadow: var(--box-shadow-hover) !important;
}}
.port-label {{ font-size:0.75rem; color:var(--secondary-text); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom:6px; }}
.port-val   {{ font-size:1.6rem; font-weight:800; color:var(--text-color); }}
.port-sub   {{ font-size:0.8rem; color:var(--secondary-text); margin-top:4px; }}
.pnl-green  {{ color:var(--success-color) !important; font-weight: 600; }}
.pnl-red    {{ color:var(--danger-color) !important; font-weight: 600; }}

.order-card {{
    background: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--card-radius) !important;
    padding: 18px 24px !important;
    margin-bottom: 12px !important;
    box-shadow: var(--box-shadow) !important;
    display:flex; justify-content:space-between; align-items:center;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
}}
.order-card:hover {{
    transform: var(--card-hover-transform) !important;
    box-shadow: var(--box-shadow-hover) !important;
}}
.order-left .o-ticker {{ font-size:0.98rem; font-weight:700; color:var(--text-color); }}
.order-left .o-detail {{ font-size:0.75rem; color:var(--secondary-text); margin-top:3px; }}
.order-right {{ text-align:right; }}
.order-right .o-price {{ font-size:0.98rem; font-weight:600; color:var(--text-color); }}
.badge-buy  {{ background:rgba(22, 163, 74, 0.12) !important; color:var(--success-color) !important; border-radius:6px; padding:3px 10px; font-size:0.72rem; font-weight:700; border: 1px solid rgba(22, 163, 74, 0.2); }}
.badge-sell {{ background:rgba(220, 38, 38, 0.1) !important; color:var(--danger-color) !important; border-radius:6px; padding:3px 10px; font-size:0.72rem; font-weight:700; border: 1px solid rgba(220, 38, 38, 0.2); }}

/* ── GAINER/LOSER ROW ── */
.mover-row {{
    display:flex; justify-content:space-between; align-items:center;
    padding:12px 20px; border-bottom:1px solid var(--row-border);
    transition: background 0.15s ease;
}}
.mover-row:hover {{ background: var(--hover-bg); }}
.mover-name  {{ font-size:0.9rem; font-weight:600; color:var(--text-color); }}
.mover-price {{ font-size:0.9rem; font-weight:600; color:var(--text-color); }}
.mover-pct-g {{ font-size:0.8rem; font-weight:700; color:var(--success-color); }}
.mover-pct-r {{ font-size:0.8rem; font-weight:700; color:var(--danger-color); }}

/* Streamlit widget overrides */
[data-testid="metric-container"] {{
    background: var(--card-bg) !important;
    backdrop-filter: var(--backdrop-blur) !important;
    -webkit-backdrop-filter: var(--backdrop-blur) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--card-radius) !important;
    padding: 16px 20px !important;
    box-shadow: var(--box-shadow) !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
}}
[data-testid="metric-container"]:hover {{
    transform: var(--card-hover-transform) !important;
    box-shadow: var(--box-shadow-hover) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    color: var(--text-color) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    font-size: 0.75rem !important;
    color: var(--secondary-text) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-weight: 600 !important;
}}

[data-baseweb="tab-list"]  {{
    background: var(--tab-list-bg) !important;
    border-radius: var(--btn-radius) !important;
    padding: 4px !important;
    border: 1px solid var(--border-color) !important;
}}
[data-baseweb="tab"]       {{
    color: var(--secondary-text) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 10px !important;
    padding: 8px 16px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}}
[aria-selected="true"]     {{
    background: var(--tab-active-bg) !important;
    color: var(--primary-blue) !important;
    box-shadow: var(--box-shadow) !important;
}}

/* Streamlit input fields */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background: var(--input-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: var(--input-radius) !important;
    padding: 10px 14px !important;
    font-family: var(--font-family) !important;
    transition: all 0.2s ease !important;
    box-shadow: inset 0 2px 4px rgba(15,23,42,0.01) !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{
    border-color: var(--primary-blue) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
    outline: none !important;
}}
div[data-testid="stSelectbox"] > div {{
    background: var(--input-bg) !important;
    color: var(--text-color) !important;
    border-radius: var(--input-radius) !important;
    border: 1px solid var(--input-border) !important;
    font-family: var(--font-family) !important;
}}

/* Streamlit buttons custom overrides */
[data-testid="stButton"] button {{
    border-radius: var(--btn-radius) !important;
    font-family: var(--font-family) !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    font-size: 0.9rem !important;
    transition: all 0.25s ease !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

/* Primary buttons (blue gradient) */
[data-testid="stButton"] button[kind="primary"] {{
    background: var(--accent-gradient) !important;
    color: white !important;
    border: none !important;
    box-shadow: var(--btn-primary-shadow) !important;
}}
[data-testid="stButton"] button[kind="primary"]:hover {{
    box-shadow: var(--btn-primary-shadow-hover) !important;
    transform: var(--btn-hover-transform) !important;
}}

/* Secondary buttons (glass white or clean grey border) */
[data-testid="stButton"] button[kind="secondary"] {{
    background: var(--btn-secondary-bg) !important;
    border: 1px solid var(--btn-secondary-border) !important;
    color: var(--btn-secondary-color) !important;
    box-shadow: var(--box-shadow) !important;
}}
[data-testid="stButton"] button[kind="secondary"]:hover {{
    background: var(--hover-bg) !important;
    transform: var(--btn-hover-transform) !important;
}}

/* Danger buttons */
[data-testid="stButton"] button[kind="danger"] {{
    background: var(--btn-danger-bg) !important;
    border: 1px solid var(--btn-danger-border) !important;
    color: var(--btn-danger-color) !important;
}}
[data-testid="stButton"] button[kind="danger"]:hover {{
    opacity: 0.9 !important;
    transform: var(--btn-hover-transform) !important;
}}

/* Modern tables styling */
div[data-testid="stTable"] table,
div[data-testid="stDataFrame"] table {{
    border-collapse: separate !important;
    border-spacing: 0 !important;
    width: 100% !important;
    border-radius: var(--input-radius) !important;
    overflow: hidden !important;
    border: 1px solid var(--border-color) !important;
}}
div[data-testid="stTable"] th,
div[data-testid="stDataFrame"] th {{
    background-color: var(--tab-list-bg) !important;
    color: var(--secondary-text) !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid var(--border-color) !important;
}}
div[data-testid="stTable"] td,
div[data-testid="stDataFrame"] td {{
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    font-size: 0.9rem !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid var(--row-border) !important;
    transition: background-color 0.15s ease !important;
}}
div[data-testid="stTable"] tr:last-child td,
div[data-testid="stDataFrame"] tr:last-child td {{
    border-bottom: none !important;
}}
div[data-testid="stTable"] tr:hover td,
div[data-testid="stDataFrame"] tr:hover td {{
    background-color: var(--hover-bg) !important;
}}

/* Custom scrollbars */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--scrollbar-thumb); border-radius: 3px; }}

/* Micro-animations */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
/* Phase 10 Dashboard Summary Cards */
.db-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
    animation: fadeIn 0.4s ease-out;
}}
.db-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    transition: transform 0.22s cubic-bezier(.25,.8,.25,1), box-shadow 0.22s, border-color 0.22s;
    position: relative;
    overflow: hidden;
}}
.db-card:hover {{
    transform: translateY(-3px);
    box-shadow: var(--box-shadow-hover);
    border-color: var(--primary-blue);
}}
.db-label {{
    font-size: 0.65rem;
    color: var(--secondary-text);
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
}}
.db-val {{
    font-size: 1.45rem;
    font-weight: 800;
    color: var(--text-color);
    margin-top: 6px;
}}
.db-sub {{
    font-size: 0.68rem;
    color: var(--muted-text);
    margin-top: 3px;
}}

/* Premium Orders Table & Containers */
.table-container {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    overflow: hidden;
    margin-top: 10px;
    margin-bottom: 16px;
    box-shadow: var(--box-shadow);
}}
.premium-table {{
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.82rem;
}}
.premium-table th {{
    background: var(--tab-list-bg);
    color: var(--secondary-text);
    font-weight: 700;
    padding: 12px 16px;
    font-size: 0.68rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 10;
}}
.premium-table td {{
    padding: 12px 16px;
    color: var(--text-color);
    border-bottom: 1px solid var(--row-border);
    transition: background-color 0.15s ease;
}}
.premium-table tr:last-child td {{
    border-bottom: none;
}}
.premium-table tr:hover td {{
    background-color: var(--hover-bg);
}}

/* Chronological Transaction Timeline */
.timeline-wrap {{
    position: relative;
    padding-left: 16px;
    border-left: 2px solid var(--border-color);
    margin: 10px 0;
    animation: fadeIn 0.4s ease-out;
}}
.timeline-node {{
    position: relative;
    padding-bottom: 16px;
}}
.timeline-dot {{
    position: absolute;
    left: -22px;
    top: 4px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid var(--bg-color);
    z-index: 2;
}}
.timeline-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 12px 16px;
    transition: transform 0.2s ease, border-color 0.2s ease;
}}
.timeline-card:hover {{
    transform: translateX(3px);
    border-color: var(--primary-blue);
}}

/* Pulse skeleton loader class */
.skeleton-pulse {{
    background: linear-gradient(-90deg, rgba(148, 163, 184, 0.08) 0%, rgba(148, 163, 184, 0.18) 50%, rgba(148, 163, 184, 0.08) 100%);
    background-size: 400% 400%;
    animation: pulse 1.5s ease infinite;
    border-radius: 6px;
}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 12 — PREMIUM CSS POLISH (purely additive, uses CSS custom properties)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ─── PHASE 12: Enhanced Keyframes ─────────────────────────────────────────── */
@keyframes slideInUp      { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:translateY(0); } }
@keyframes slideInRight   { from { opacity:0; transform:translateX(-18px); } to { opacity:1; transform:translateX(0); } }
@keyframes scaleIn        { from { opacity:0; transform:scale(0.92); } to { opacity:1; transform:scale(1); } }
@keyframes shimmer        { 0% { background-position:-200% 0; } 100% { background-position:200% 0; } }
@keyframes bounceIn       { 0% { opacity:0; transform:scale(0.3); } 55% { transform:scale(1.06); } 75% { transform:scale(0.92); } 100% { opacity:1; transform:scale(1); } }
@keyframes glowPulse      { 0%,100% { box-shadow:0 0 0 0 rgba(59,130,246,.45); } 50% { box-shadow:0 0 0 10px rgba(59,130,246,0); } }
@keyframes toastIn        { from { opacity:0; transform:translateX(110%); } to { opacity:1; transform:translateX(0); } }
@keyframes toastOut       { from { opacity:1; transform:translateX(0); } to { opacity:0; transform:translateX(110%); } }
@keyframes spin           { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
@keyframes liveBlip       { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:.4; transform:scale(.7); } }
@keyframes toastProgress  { from { width:100%; } to { width:0%; } }
@keyframes fabGlow        { 0%,100% { box-shadow:0 4px 20px rgba(59,130,246,.45),0 2px 8px rgba(0,0,0,.2); } 50% { box-shadow:0 4px 36px rgba(59,130,246,.75),0 2px 8px rgba(0,0,0,.2); } }
@keyframes pulse2         { 0% { background-position:-200% 0; } 100% { background-position:200% 0; } }

/* ─── INDEX CHIPS (top nav bar) ─────────────────────────────────────────────── */
.index-chip          { display:inline-flex; align-items:center; gap:8px; padding:5px 12px; background:var(--tab-list-bg); border:1px solid var(--border-color); border-radius:20px; transition:all .2s ease; cursor:default; }
.index-chip:hover    { border-color:var(--primary-blue); background:var(--hover-bg); transform:translateY(-1px); }
.ic-name             { font-size:.7rem; font-weight:700; color:var(--secondary-text); letter-spacing:.04em; }
.ic-val              { font-size:.85rem; font-weight:700; color:var(--text-color); }
.ic-chg-g            { font-size:.75rem; font-weight:600; color:var(--success-color); }
.ic-chg-r            { font-size:.75rem; font-weight:600; color:var(--danger-color); }

/* ─── STATUS DOTS ────────────────────────────────────────────────────────────── */
.live-dot    { display:inline-block; width:8px; height:8px; background:#22c55e; border-radius:50%; animation:liveBlip 1.5s ease infinite; box-shadow:0 0 0 3px rgba(34,197,94,.22); }
.preopen-dot { display:inline-block; width:8px; height:8px; background:#f59e0b; border-radius:50%; animation:liveBlip 2s ease infinite; box-shadow:0 0 0 3px rgba(245,158,11,.2); }
.closed-dot  { display:inline-block; width:8px; height:8px; background:#64748b; border-radius:50%; }

/* ─── TOAST NOTIFICATION SYSTEM ──────────────────────────────────────────────── */
.toast-container { position:fixed !important; top:20px !important; right:24px !important; z-index:100000 !important; display:flex !important; flex-direction:column !important; gap:10px !important; pointer-events:none !important; max-width:370px !important; }
.toast           { display:flex !important; align-items:flex-start !important; gap:12px !important; padding:14px 18px !important; border-radius:14px !important; font-family:var(--font-family) !important; font-size:.875rem !important; font-weight:500 !important; line-height:1.4 !important; pointer-events:auto !important; animation:toastIn .35s cubic-bezier(.34,1.56,.64,1) forwards !important; backdrop-filter:blur(20px) !important; -webkit-backdrop-filter:blur(20px) !important; border:1px solid transparent !important; box-shadow:0 8px 32px rgba(0,0,0,.18),0 2px 8px rgba(0,0,0,.12) !important; min-width:280px !important; cursor:pointer !important; transition:transform .2s ease,box-shadow .2s ease !important; position:relative !important; overflow:hidden !important; }
.toast:hover     { transform:translateX(-3px) scale(1.01) !important; box-shadow:0 12px 40px rgba(0,0,0,.22) !important; }
.toast-success   { background:rgba(22,163,74,.14) !important; border-color:rgba(22,163,74,.35) !important; }
.toast-error     { background:rgba(220,38,38,.13) !important; border-color:rgba(220,38,38,.3) !important; }
.toast-warning   { background:rgba(245,158,11,.13) !important; border-color:rgba(245,158,11,.3) !important; }
.toast-info      { background:rgba(59,130,246,.12) !important; border-color:rgba(59,130,246,.3) !important; }
.toast-icon      { font-size:1.2rem; flex-shrink:0; margin-top:1px; }
.toast-body      { flex:1; min-width:0; }
.toast-title     { font-weight:700; margin-bottom:2px; font-size:.9rem; color:var(--text-color); }
.toast-msg       { opacity:.82; font-size:.8rem; color:var(--secondary-text); }
.toast-dismiss   { font-size:1.2rem; cursor:pointer; opacity:.45; flex-shrink:0; transition:opacity .15s; line-height:1; }
.toast-dismiss:hover { opacity:1; }
.toast-progress  { position:absolute; bottom:0; left:0; height:3px; border-radius:0 0 14px 14px; animation:toastProgress 3.5s linear forwards; }
.toast-success .toast-progress { background:var(--success-color); }
.toast-error   .toast-progress { background:var(--danger-color); }
.toast-warning .toast-progress { background:var(--warning-color); }
.toast-info    .toast-progress { background:var(--primary-blue); }

/* ─── COMMAND PALETTE ────────────────────────────────────────────────────────── */
.cmd-overlay              { position:fixed !important; inset:0 !important; background:rgba(0,0,0,.56) !important; backdrop-filter:blur(9px) !important; -webkit-backdrop-filter:blur(9px) !important; z-index:99998 !important; display:none; align-items:flex-start !important; justify-content:center !important; padding-top:14vh !important; }
.cmd-overlay.open         { display:flex !important; }
.cmd-modal                { background:var(--card-bg) !important; backdrop-filter:blur(40px) !important; -webkit-backdrop-filter:blur(40px) !important; border:1px solid var(--border-color) !important; border-radius:20px !important; width:min(620px,92vw) !important; max-height:72vh !important; overflow:hidden !important; box-shadow:0 40px 100px rgba(0,0,0,.5) !important; animation:scaleIn .2s cubic-bezier(.34,1.56,.64,1) !important; display:flex !important; flex-direction:column !important; }
.cmd-search-row           { display:flex !important; align-items:center !important; gap:12px !important; padding:18px 20px !important; border-bottom:1px solid var(--border-color) !important; }
.cmd-search-icon          { font-size:1.1rem; color:var(--secondary-text); flex-shrink:0; }
.cmd-input                { flex:1 !important; background:transparent !important; border:none !important; outline:none !important; font-size:1.05rem !important; font-weight:500 !important; color:var(--text-color) !important; font-family:var(--font-family) !important; caret-color:var(--primary-blue) !important; }
.cmd-input::placeholder   { color:var(--muted-text); opacity:.7; }
.cmd-kbd                  { font-size:.68rem !important; color:var(--secondary-text) !important; background:var(--tab-list-bg) !important; border:1px solid var(--border-color) !important; border-radius:5px !important; padding:2px 7px !important; font-family:monospace !important; flex-shrink:0 !important; }
.cmd-results              { overflow-y:auto !important; padding:8px !important; scroll-behavior:smooth !important; }
.cmd-section-label        { font-size:.63rem !important; font-weight:800 !important; text-transform:uppercase !important; letter-spacing:.12em !important; color:var(--muted-text) !important; padding:10px 12px 6px !important; }
.cmd-item                 { display:flex !important; align-items:center !important; gap:12px !important; padding:10px 12px !important; border-radius:10px !important; cursor:pointer !important; transition:background .12s ease !important; font-family:var(--font-family) !important; }
.cmd-item:hover,
.cmd-item.selected        { background:var(--hover-bg) !important; }
.cmd-item-icon            { font-size:1.1rem; width:28px; text-align:center; flex-shrink:0; }
.cmd-item-label           { font-size:.9rem; font-weight:600; color:var(--text-color); }
.cmd-item-desc            { font-size:.74rem; color:var(--secondary-text); margin-top:1px; }
.cmd-item-shortcut        { font-size:.63rem; color:var(--muted-text); font-family:monospace; flex-shrink:0; }
.cmd-footer               { padding:10px 18px !important; border-top:1px solid var(--border-color) !important; display:flex !important; gap:18px !important; flex-wrap:wrap !important; font-size:.66rem !important; color:var(--muted-text) !important; font-family:var(--font-family) !important; }
.cmd-hint                 { display:flex; align-items:center; gap:5px; }
.cmd-hint-key             { background:var(--tab-list-bg); border:1px solid var(--border-color); border-radius:4px; padding:1px 5px; font-family:monospace; font-size:.65rem; color:var(--text-color); }

/* ─── FLOATING ACTION BUTTON ─────────────────────────────────────────────────── */
.fab-container   { position:fixed !important; bottom:90px !important; right:22px !important; z-index:9999 !important; display:flex !important; flex-direction:column !important; align-items:flex-end !important; gap:10px !important; }
.fab-main-btn    { width:50px !important; height:50px !important; border-radius:50% !important; background:var(--accent-gradient) !important; border:none !important; cursor:pointer !important; display:flex !important; align-items:center !important; justify-content:center !important; font-size:1.3rem !important; box-shadow:0 4px 20px rgba(59,130,246,.45),0 2px 8px rgba(0,0,0,.2) !important; transition:all .3s cubic-bezier(.34,1.56,.64,1) !important; color:#fff !important; animation:fabGlow 2.5s ease infinite !important; }
.fab-main-btn:hover { transform:scale(1.12) rotate(90deg) !important; box-shadow:0 8px 32px rgba(59,130,246,.65) !important; animation:none !important; }
.fab-main-btn.fab-open { transform:rotate(45deg) !important; animation:none !important; }
.fab-actions     { display:flex !important; flex-direction:column !important; gap:8px !important; align-items:flex-end !important; }
.fab-actions.fab-hidden { display:none !important; }
.fab-action-row  { display:flex !important; align-items:center !important; gap:10px !important; animation:slideInRight .2s ease !important; }
.fab-action-label { font-size:.73rem !important; font-weight:600 !important; color:var(--text-color) !important; background:var(--card-bg) !important; backdrop-filter:blur(20px) !important; -webkit-backdrop-filter:blur(20px) !important; border:1px solid var(--border-color) !important; border-radius:8px !important; padding:5px 10px !important; box-shadow:0 4px 14px rgba(0,0,0,.12) !important; white-space:nowrap !important; font-family:var(--font-family) !important; }
.fab-action-btn  { width:38px !important; height:38px !important; border-radius:50% !important; background:var(--card-bg) !important; backdrop-filter:blur(20px) !important; -webkit-backdrop-filter:blur(20px) !important; border:1px solid var(--border-color) !important; cursor:pointer !important; display:flex !important; align-items:center !important; justify-content:center !important; font-size:1rem !important; box-shadow:0 4px 14px rgba(0,0,0,.14) !important; transition:all .2s ease !important; flex-shrink:0 !important; }
.fab-action-btn:hover { transform:scale(1.12) !important; border-color:var(--primary-blue) !important; box-shadow:0 6px 20px rgba(0,0,0,.22) !important; }

/* ─── ENHANCED SKELETON LOADERS ──────────────────────────────────────────────── */
.skeleton-line   { height:14px; border-radius:7px; background:linear-gradient(90deg,var(--border-color) 25%,var(--hover-bg) 50%,var(--border-color) 75%); background-size:200% 100%; animation:pulse2 1.6s ease infinite; margin-bottom:8px; }
.skeleton-line.sk-sm { height:10px; width:60%; }
.skeleton-line.sk-lg { height:20px; }
.skeleton-line.sk-xl { height:32px; width:75%; }
.skeleton-circle { border-radius:50%; background:linear-gradient(90deg,var(--border-color) 25%,var(--hover-bg) 50%,var(--border-color) 75%); background-size:200% 100%; animation:pulse2 1.6s ease infinite; }
.skeleton-card   { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:20px; margin-bottom:12px; animation:fadeIn .3s ease; }
.skeleton-chart  { height:220px; border-radius:12px; background:linear-gradient(90deg,var(--border-color) 25%,var(--hover-bg) 50%,var(--border-color) 75%); background-size:200% 100%; animation:pulse2 1.6s ease infinite; margin:8px 0; }

/* ─── PREMIUM EMPTY STATES ───────────────────────────────────────────────────── */
.empty-state  { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:52px 24px; text-align:center; animation:fadeIn .4s ease; }
.empty-icon   { font-size:3.5rem; margin-bottom:16px; animation:bounceIn .6s ease; filter:drop-shadow(0 4px 8px rgba(0,0,0,.15)); }
.empty-title  { font-size:1.1rem; font-weight:700; color:var(--text-color); margin-bottom:8px; font-family:var(--font-family); }
.empty-desc   { font-size:.85rem; color:var(--secondary-text); max-width:300px; line-height:1.55; margin-bottom:22px; font-family:var(--font-family); }

/* ─── BUTTON RIPPLE EFFECT ───────────────────────────────────────────────────── */
[data-testid="stButton"] button { position:relative; overflow:hidden; }
[data-testid="stButton"] button::after { content:""; position:absolute; inset:0; background:radial-gradient(circle at center,rgba(255,255,255,.25) 0%,transparent 65%); opacity:0; transition:opacity .4s ease; pointer-events:none; }
[data-testid="stButton"] button:active::after { opacity:1; transition:opacity 0s; }

/* ─── ACCESSIBILITY FOCUS RINGS ──────────────────────────────────────────────── */
:focus-visible { outline:2.5px solid var(--primary-blue) !important; outline-offset:3px !important; }
[data-testid="stButton"] button:focus-visible { outline:2.5px solid var(--primary-blue) !important; outline-offset:3px !important; box-shadow:0 0 0 5px rgba(59,130,246,.18) !important; }

/* ─── PREMIUM PROGRESS BAR ───────────────────────────────────────────────────── */
.premium-progress      { background:var(--border-color); border-radius:999px; height:6px; overflow:hidden; margin:8px 0; }
.premium-progress-fill { height:100%; border-radius:999px; background:var(--accent-gradient); transition:width .8s cubic-bezier(.4,0,.2,1); }

/* ─── LOADING SPINNER ────────────────────────────────────────────────────────── */
.premium-spinner { width:32px; height:32px; border:3px solid var(--border-color); border-top-color:var(--primary-blue); border-radius:50%; animation:spin .75s linear infinite; margin:0 auto; }

/* ─── ENHANCED CARD HOVERS ───────────────────────────────────────────────────── */
.port-card:hover, .order-card:hover, .timeline-card:hover { box-shadow:0 20px 60px rgba(59,130,246,.07),0 4px 16px rgba(0,0,0,.06) !important; }

/* ─── TICKER ITEM HOVER ──────────────────────────────────────────────────────── */
.ticker-item { cursor:pointer; transition:background .2s ease; border-radius:6px; }
.ticker-item:hover { background:rgba(59,130,246,.08); }

/* ─── PREMIUM TABLE ROW HIGHLIGHT ────────────────────────────────────────────── */
.premium-table tr:hover td:first-child { border-left:2.5px solid var(--primary-blue); padding-left:14px; transition:all .15s ease; }

/* ─── STAGGERED METRIC ANIMATION ─────────────────────────────────────────────── */
[data-testid="metric-container"]                   { animation:slideInUp .4s ease both; }
[data-testid="metric-container"]:nth-child(2)      { animation-delay:.05s; }
[data-testid="metric-container"]:nth-child(3)      { animation-delay:.10s; }
[data-testid="metric-container"]:nth-child(4)      { animation-delay:.15s; }

/* ─── COUNTDOWN URGENT PULSE ─────────────────────────────────────────────────── */
.countdown-urgent { color:#f97316 !important; animation:liveBlip .8s ease infinite; font-weight:700; }

/* ─── PREMIUM DIVIDER ────────────────────────────────────────────────────────── */
.premium-divider { height:1px; background:linear-gradient(90deg,transparent,var(--border-color),transparent); margin:20px 0; border:none; }

/* ─── SIDEBAR ACTIVE ITEM SHIMMER ────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] { position:relative; overflow:hidden; }
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]::before { content:""; position:absolute; inset:0; background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.12) 50%,transparent 100%); transform:translateX(-100%); animation:shimmer 2.5s ease infinite; }

/* ─── SELECT HOVER ENHANCEMENT ───────────────────────────────────────────────── */
div[data-testid="stSelectbox"] > div:hover { border-color:var(--primary-blue) !important; }

/* ─── PLOTLY CHART BORDER ON HOVER ───────────────────────────────────────────── */
div[data-testid="stPlotlyChart"]:hover { border-color:var(--primary-blue) !important; box-shadow:0 12px 40px rgba(59,130,246,.1) !important; }

/* ─── GLASS UTILITY CARD ─────────────────────────────────────────────────────── */
.glass-card { background:var(--card-bg); backdrop-filter:var(--backdrop-blur); -webkit-backdrop-filter:var(--backdrop-blur); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:var(--card-padding); box-shadow:var(--box-shadow); transition:all .3s cubic-bezier(.4,0,.2,1); }
.glass-card:hover { transform:var(--card-hover-transform); box-shadow:var(--box-shadow-hover); border-color:var(--primary-blue); }

/* ─── MOBILE RESPONSIVE IMPROVEMENTS ────────────────────────────────────────── */
@media (max-width: 768px) {
    .top-nav-bar { padding:0 .75rem !important; }
    .nav-center  { display:none !important; }
    .ticker-wrap { left:0 !important; }
    .block-container { padding-left:.75rem !important; padding-right:.75rem !important; padding-top:112px !important; }
    .fab-container { bottom:78px !important; right:14px !important; }
    .db-grid { grid-template-columns:repeat(2,1fr) !important; }
    .cmd-modal { width:96vw !important; }
    [data-testid="stSidebar"] { width:220px !important; }
    [data-testid="stSidebar"] > div:first-child { width:220px !important; }
}
@media (max-width: 480px) {
    .db-grid { grid-template-columns:1fr !important; }
    .toast-container { top:auto !important; bottom:100px !important; right:12px !important; left:12px !important; max-width:100% !important; }
    .toast { min-width:auto !important; }
    .bottom-nav .nav-item { padding:6px 8px !important; font-size:.6rem !important; }
    .fab-main-btn { width:44px !important; height:44px !important; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 12 — JS ENHANCEMENTS (Command Palette, FAB, Keyboard Shortcuts, Toasts)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<script>
(function() {
    'use strict';

    /* ── TOAST SYSTEM ──────────────────────────────────────────────────────── */
    function getToastContainer() {
        var c = document.getElementById('ftc-toasts');
        if (!c) {
            c = document.createElement('div');
            c.id = 'ftc-toasts';
            c.className = 'toast-container';
            document.body.appendChild(c);
        }
        return c;
    }
    window.showPremiumToast = function(title, message, type, duration) {
        type = type || 'info'; duration = duration || 3500;
        var icons = { success:'✅', error:'❌', warning:'⚠️', info:'💡' };
        var c = getToastContainer();
        var t = document.createElement('div');
        t.className = 'toast toast-' + type;
        t.innerHTML = '<span class="toast-icon">' + (icons[type]||'💡') + '</span>'
            + '<div class="toast-body"><div class="toast-title">' + title + '</div>'
            + (message ? '<div class="toast-msg">' + message + '</div>' : '')
            + '</div><span class="toast-dismiss" onclick="this.parentElement.remove()">&#215;</span>'
            + '<div class="toast-progress"></div>';
        t.onclick = function(e) {
            if (!e.target.classList.contains('toast-dismiss')) {
                t.style.animation = 'toastOut .3s ease forwards';
                setTimeout(function(){ if(t.parentNode) t.remove(); }, 300);
            }
        };
        c.appendChild(t);
        setTimeout(function(){
            if(t.parentNode){ t.style.animation='toastOut .3s ease forwards'; setTimeout(function(){ if(t.parentNode) t.remove(); }, 300); }
        }, duration);
    };

    /* ── NAVIGATION HELPER ─────────────────────────────────────────────────── */
    function navigateTo(label) {
        var sb = document.querySelector('[data-testid="stSidebar"]');
        if (!sb) {
            var toggle = document.querySelector('[data-testid="collapsedControl"]');
            if (toggle) { toggle.click(); setTimeout(function(){ navigateTo(label); }, 450); }
            return;
        }
        var btns = sb.querySelectorAll('[data-testid="stButton"] button');
        var target = label.trim();
        for (var i=0; i<btns.length; i++) {
            if (btns[i].innerText.trim() === target) { btns[i].click(); return; }
        }
        // fallback: first 5 chars
        var short = target.substring(0,5);
        for (var j=0; j<btns.length; j++) {
            if (btns[j].innerText.trim().startsWith(short)) { btns[j].click(); return; }
        }
    }
    window._ftcNav = navigateTo;

    /* ── COMMAND PALETTE ───────────────────────────────────────────────────── */
    var PAGES = [
        {icon:'📊',label:'Dashboard',  desc:'Overview & portfolio summary',  sc:'Alt+H', nav:'📊 Dashboard'},
        {icon:'⭐',label:'Watchlist',  desc:'Monitor your tracked stocks',   sc:'Alt+W', nav:'⭐ Watchlist'},
        {icon:'💼',label:'Portfolio',  desc:'Holdings, P&L & performance',   sc:'Alt+P', nav:'💼 Portfolio'},
        {icon:'📋',label:'Orders',     desc:'Trade history & open orders',    sc:'Alt+O', nav:'📋 Orders'},
        {icon:'💰',label:'Balance',    desc:'Cash balance & funds',           sc:'',      nav:'💰 Balance'},
        {icon:'📈',label:'Market',     desc:'Market overview & indices',      sc:'Alt+M', nav:'📈 Market'},

        {icon:'📰',label:'News',       desc:'Latest financial headlines',     sc:'Alt+N', nav:'📰 News'},
        {icon:'📅',label:'Calendar',   desc:'Market events & earnings dates', sc:'',      nav:'📅 Calendar'},
        {icon:'🔍',label:'Screener',   desc:'Stock screener & filters',       sc:'',      nav:'🔍 Screener'},
        {icon:'🏭',label:'Sectors',    desc:'Sector analysis & trends',       sc:'',      nav:'🏭 Sectors'},
        {icon:'⚙️',label:'Settings',   desc:'App preferences & theme',       sc:'',      nav:'⚙️ Settings'},
    ];
    var cmdIdx=0, cmdFiltered=PAGES.slice();

    function renderCmdResults(filter) {
        var el = document.getElementById('ftc-cmd-results');
        if (!el) return;
        filter = (filter||'').toLowerCase().trim();
        cmdFiltered = filter ? PAGES.filter(function(p){
            return p.label.toLowerCase().indexOf(filter)!==-1 || p.desc.toLowerCase().indexOf(filter)!==-1;
        }) : PAGES.slice();
        if (!cmdFiltered.length) {
            el.innerHTML='<div style="padding:28px;text-align:center;font-size:.87rem;color:var(--secondary-text)">🔍 No results found</div>';
            return;
        }
        var html='<div class="cmd-section-label">&#x1F4F1;&nbsp; NAVIGATE TO</div>';
        cmdFiltered.forEach(function(p,i){
            html+='<div class="cmd-item'+(i===cmdIdx?' selected':'')
                +'" data-nav="'+p.nav+'" role="option" aria-selected="'+(i===cmdIdx)+'"'
                +' onclick="window._ftcCmdSel(this)">'
                +'<span class="cmd-item-icon">'+p.icon+'</span>'
                +'<div style="flex:1;min-width:0">'
                +'<div class="cmd-item-label">'+p.label+'</div>'
                +'<div class="cmd-item-desc">'+p.desc+'</div>'
                +'</div>'
                +(p.sc?'<span class="cmd-item-shortcut">'+p.sc+'</span>':'')
                +'</div>';
        });
        el.innerHTML=html;
    }
    window._ftcCmdSel = function(el) {
        var nav=el.getAttribute('data-nav');
        closePalette();
        setTimeout(function(){ navigateTo(nav); }, 160);
    };

    function moveCmdSel(dir) {
        cmdIdx = Math.max(0, Math.min(cmdFiltered.length-1, cmdIdx+dir));
        var items=document.querySelectorAll('#ftc-cmd-results .cmd-item');
        items.forEach(function(el,i){
            el.classList.toggle('selected',i===cmdIdx);
            el.setAttribute('aria-selected',i===cmdIdx);
        });
        if(items[cmdIdx]) items[cmdIdx].scrollIntoView({block:'nearest',behavior:'smooth'});
    }

    function createPalette() {
        if (document.getElementById('ftc-cmd')) return;
        var o=document.createElement('div');
        o.id='ftc-cmd'; o.className='cmd-overlay';
        o.setAttribute('role','dialog'); o.setAttribute('aria-modal','true'); o.setAttribute('aria-label','Command palette');
        o.innerHTML='<div class="cmd-modal">'
            +'<div class="cmd-search-row">'
            +'<span class="cmd-search-icon">🔍</span>'
            +'<input class="cmd-input" id="ftc-cmd-input" type="text" placeholder="Search pages or actions..." autocomplete="off" aria-label="Search commands"/>'
            +'<span class="cmd-kbd">ESC</span>'
            +'</div>'
            +'<div class="cmd-results" id="ftc-cmd-results" role="listbox"></div>'
            +'<div class="cmd-footer">'
            +'<span class="cmd-hint"><span class="cmd-hint-key">↑↓</span> navigate</span>'
            +'<span class="cmd-hint"><span class="cmd-hint-key">↵</span> select</span>'
            +'<span class="cmd-hint"><span class="cmd-hint-key">Esc</span> close</span>'
            +'<span class="cmd-hint" style="margin-left:auto;opacity:.55">Ctrl+K</span>'
            +'</div>'
            +'</div>';
        document.body.appendChild(o);
        o.addEventListener('click',function(e){ if(e.target===o) closePalette(); });
        document.getElementById('ftc-cmd-input').addEventListener('input',function(){
            cmdIdx=0; renderCmdResults(this.value);
        });
        renderCmdResults('');
    }

    function openPalette() {
        createPalette();
        var o=document.getElementById('ftc-cmd'); if(!o) return;
        o.classList.add('open'); cmdIdx=0;
        var inp=document.getElementById('ftc-cmd-input');
        if(inp){ inp.value=''; inp.focus(); }
        renderCmdResults('');
    }
    function closePalette() {
        var o=document.getElementById('ftc-cmd'); if(o) o.classList.remove('open');
    }
    window._ftcOpenPalette=openPalette; window._ftcClosePalette=closePalette;

    /* ── FLOATING ACTION BUTTON ────────────────────────────────────────────── */
    function createFAB() {
        if (document.getElementById('ftc-fab')) return;
        var f=document.createElement('div'); f.id='ftc-fab'; f.className='fab-container';
        f.innerHTML='<div class="fab-actions fab-hidden" id="ftc-fab-actions">'
            +'<div class="fab-action-row"><span class="fab-action-label">⌨️ Ctrl+K &mdash; Commands</span>'
            +'<button class="fab-action-btn" onclick="window._ftcOpenPalette()" aria-label="Open command palette">🔍</button></div>'
            +'<div class="fab-action-row"><span class="fab-action-label">📊 Dashboard</span>'
            +'<button class="fab-action-btn" onclick="window._ftcFabClose();window._ftcNav(\'📊 Dashboard\')" aria-label="Dashboard">📊</button></div>'
            +'<div class="fab-action-row"><span class="fab-action-label">💼 Portfolio</span>'
            +'<button class="fab-action-btn" onclick="window._ftcFabClose();window._ftcNav(\'💼 Portfolio\')" aria-label="Portfolio">💼</button></div>'
            +'<div class="fab-action-row"><span class="fab-action-label">⭐ Watchlist</span>'
            +'<button class="fab-action-btn" onclick="window._ftcFabClose();window._ftcNav(\'⭐ Watchlist\')" aria-label="Watchlist">⭐</button></div>'
            +'<div class="fab-action-row"><span class="fab-action-label">📈 Market</span>'
            +'<button class="fab-action-btn" onclick="window._ftcFabClose();window._ftcNav(\'📈 Market\')" aria-label="Market">📈</button></div>'
            +'</div>'
            +'<button class="fab-main-btn" id="ftc-fab-btn" onclick="window._ftcFabToggle()" title="Quick Actions" aria-label="Quick Actions (⚡)">⚡</button>';
        document.body.appendChild(f);
        document.addEventListener('click',function(e){
            var el=document.getElementById('ftc-fab');
            if(el && !el.contains(e.target)) window._ftcFabClose();
        });
    }
    window._ftcFabToggle=function(){
        var a=document.getElementById('ftc-fab-actions'),b=document.getElementById('ftc-fab-btn');
        if(!a) return;
        if(a.classList.contains('fab-hidden')){ a.classList.remove('fab-hidden'); if(b) b.classList.add('fab-open'); }
        else { a.classList.add('fab-hidden'); if(b) b.classList.remove('fab-open'); }
    };
    window._ftcFabClose=function(){
        var a=document.getElementById('ftc-fab-actions'),b=document.getElementById('ftc-fab-btn');
        if(a) a.classList.add('fab-hidden'); if(b) b.classList.remove('fab-open');
    };

    /* ── KEYBOARD SHORTCUTS ────────────────────────────────────────────────── */
    function setupKbd() {
        document.addEventListener('keydown',function(e){
            var tag=(document.activeElement&&document.activeElement.tagName)||'';
            var inInput=['INPUT','TEXTAREA','SELECT'].indexOf(tag)!==-1;

            // Ctrl+K or Cmd+K → Command Palette (always fires)
            if((e.ctrlKey||e.metaKey)&&e.key==='k'){ e.preventDefault(); openPalette(); return; }
            // Escape → close overlays
            if(e.key==='Escape'){ closePalette(); window._ftcFabClose&&window._ftcFabClose(); return; }

            // Palette arrow navigation
            var overlay=document.getElementById('ftc-cmd');
            if(overlay&&overlay.classList.contains('open')){
                if(e.key==='ArrowDown'){ e.preventDefault(); moveCmdSel(1); }
                else if(e.key==='ArrowUp'){ e.preventDefault(); moveCmdSel(-1); }
                else if(e.key==='Enter'){
                    e.preventDefault();
                    var items=document.querySelectorAll('#ftc-cmd-results .cmd-item');
                    if(items[cmdIdx]) items[cmdIdx].click();
                }
                return;
            }

            // Alt+letter shortcuts (only outside inputs)
            if(inInput) return;
            if(e.altKey&&!e.ctrlKey&&!e.metaKey){
                var map={'h':'📊 Dashboard','w':'⭐ Watchlist','p':'💼 Portfolio',
                         'o':'📋 Orders','n':'📰 News','m':'📈 Market'};
                var dest=map[e.key.toLowerCase()];
                if(dest){ e.preventDefault(); navigateTo(dest); }
            }
        });
    }

    /* ── INIT ──────────────────────────────────────────────────────────────── */
    function init(){
        createPalette();
        createFAB();
        setupKbd();
        getToastContainer();
    }
    if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded',init); }
    else { init(); }

    /* ── PROFILE DROPDOWN ──────────────────────────────────────────────────── */
    window._ftcToggleProfileMenu = function() {
        var el = document.getElementById('ftc-profile-dropdown');
        if (el) el.classList.toggle('open');
    };
    window._ftcCloseProfileMenu = function() {
        var el = document.getElementById('ftc-profile-dropdown');
        if (el) el.classList.remove('open');
    };
    document.addEventListener('click', function(e) {
        var el = document.getElementById('ftc-profile-dropdown');
        var avatar = document.querySelector('.profile-avatar');
        if (el && !el.contains(e.target) && e.target !== avatar) {
            el.classList.remove('open');
        }
    });

    // Re-attach after Streamlit rerenders (DOM mutation)
    var _obs=new MutationObserver(function(){
        if(!document.getElementById('ftc-cmd')) createPalette();
        if(!document.getElementById('ftc-fab')) createFAB();
        if(!document.getElementById('ftc-toasts')) getToastContainer();
    });
    _obs.observe(document.body,{childList:true});
})();
</script>
""", unsafe_allow_html=True)

# ── Portfolio persistence — JSON file mein save hoga, refresh pe nahi jayega ──
import json, os

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio_data.json")

def save_portfolio():
    data = {
        "pt_cash":     st.session_state.pt_cash,
        "pt_holdings": st.session_state.pt_holdings,
        "pt_history":  st.session_state.pt_history,
        "pt_targets":  st.session_state.get("pt_targets", []),
    }
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass  # Cloud pe file write fail ho toh crash mat karo

def load_portfolio():
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

# ── Session state defaults ─────────────────────────────────────────────────────
default_landing = st.session_state.get("pref_landing", "home")
if "active_tab"   not in st.session_state: st.session_state.active_tab   = default_landing
if "show_balance" not in st.session_state: st.session_state.show_balance = False
if "order_ticker" not in st.session_state: st.session_state.order_ticker = "RELIANCE.NS"
if "order_action" not in st.session_state: st.session_state.order_action = "BUY"
if "expanded_stock" not in st.session_state: st.session_state.expanded_stock = None
if "dark_mode"    not in st.session_state: st.session_state.dark_mode    = False
if "wl_search"    not in st.session_state: st.session_state.wl_search    = ""
if "cancelled_orders_count" not in st.session_state: st.session_state.cancelled_orders_count = 0
# ── SECTOR WATCHLISTS — 13 sectors, har ek mein achhe/liquid NSE stocks ────────
# (Sector Gap tab ke SECTOR_SUGGESTIONS se hi consistent rakha gaya hai, bas
#  yahan thoda fuller list hai taaki har sector watchlist mein 6-8 stocks ho)
SECTOR_WATCHLISTS = {
    "Defence":        [("HAL.NS","Hindustan Aeronautics"), ("BEL.NS","Bharat Electronics"),
                        ("MAZDOCK.NS","Mazagon Dock"), ("BDL.NS","Bharat Dynamics"),
                        ("GRSE.NS","GRSE"), ("COCHINSHIP.NS","Cochin Shipyard"),
                        ("ZENTEC.NS","Zen Technologies"), ("PARAS.NS","Paras Defence")],
    "IT":             [("TCS.NS","TCS"), ("INFY.NS","Infosys"),
                        ("HCLTECH.NS","HCL Tech"), ("PERSISTENT.NS","Persistent Systems"),
                        ("WIPRO.NS","Wipro"), ("TECHM.NS","Tech Mahindra"),
                        ("LTIM.NS","LTIMindtree"), ("KPITTECH.NS","KPIT Technologies")],
    "Banking":        [("HDFCBANK.NS","HDFC Bank"), ("ICICIBANK.NS","ICICI Bank"),
                        ("KOTAKBANK.NS","Kotak Bank"), ("SBIN.NS","SBI"),
                        ("AXISBANK.NS","Axis Bank"), ("INDUSINDBK.NS","IndusInd Bank"),
                        ("BANKBARODA.NS","Bank of Baroda"), ("PNB.NS","Punjab National Bank")],
    "Pharma":         [("SUNPHARMA.NS","Sun Pharma"), ("DIVISLAB.NS","Divi's Labs"),
                        ("CIPLA.NS","Cipla"), ("TORNTPHARM.NS","Torrent Pharma"),
                        ("DRREDDY.NS","Dr Reddy's"), ("AUROPHARMA.NS","Aurobindo Pharma"),
                        ("LUPIN.NS","Lupin"), ("BIOCON.NS","Biocon")],
    "Auto":           [("MARUTI.NS","Maruti Suzuki"), ("M&M.NS","Mahindra & Mahindra"),
                        ("EICHERMOT.NS","Eicher Motors"), ("TVSMOTOR.NS","TVS Motor"),
                        ("TMPV.NS","Tata Motors"), ("BAJAJ-AUTO.NS","Bajaj Auto"),
                        ("HEROMOTOCO.NS","Hero MotoCorp"), ("ASHOKLEY.NS","Ashok Leyland")],
    "FMCG":           [("HINDUNILVR.NS","Hindustan Unilever"), ("NESTLEIND.NS","Nestle India"),
                        ("BRITANNIA.NS","Britannia"), ("TATACONSUM.NS","Tata Consumer"),
                        ("ITC.NS","ITC"), ("DABUR.NS","Dabur India"),
                        ("GODREJCP.NS","Godrej Consumer"), ("MARICO.NS","Marico")],
    "Energy":         [("RELIANCE.NS","Reliance Industries"), ("NTPC.NS","NTPC"),
                        ("POWERGRID.NS","Power Grid"), ("COALINDIA.NS","Coal India"),
                        ("ONGC.NS","ONGC"), ("BPCL.NS","BPCL"),
                        ("IOC.NS","Indian Oil"), ("GAIL.NS","GAIL India")],
    "Renewable":      [("TATAPOWER.NS","Tata Power"), ("ADANIGREEN.NS","Adani Green"),
                        ("SUZLON.NS","Suzlon Energy"), ("INOXWIND.NS","Inox Wind"),
                        ("WAAREEENER.NS","Waaree Energies"), ("VIKRAMSOLR.NS","Vikram Solar")],
    "Realty":         [("GODREJPROP.NS","Godrej Properties"), ("DLF.NS","DLF"),
                        ("OBEROIRLTY.NS","Oberoi Realty"), ("PRESTIGE.NS","Prestige Estates"),
                        ("PHOENIXLTD.NS","Phoenix Mills"), ("BRIGADE.NS","Brigade Enterprises")],
    "Metal":          [("TATASTEEL.NS","Tata Steel"), ("JSWSTEEL.NS","JSW Steel"),
                        ("HINDALCO.NS","Hindalco"), ("JINDALSTEL.NS","Jindal Steel"),
                        ("VEDL.NS","Vedanta"), ("SAIL.NS","SAIL"), ("NMDC.NS","NMDC")],
    "Infrastructure": [("LT.NS","Larsen & Toubro"), ("ADANIPORTS.NS","Adani Ports"),
                        ("KEC.NS","KEC International"), ("IRB.NS","IRB Infra"),
                        ("GMRINFRA.NS","GMR Infra"), ("NBCC.NS","NBCC India")],
    "Chemicals":      [("PIDILITIND.NS","Pidilite Industries"), ("SRF.NS","SRF Ltd"),
                        ("UPL.NS","UPL Ltd"), ("DEEPAKNTR.NS","Deepak Nitrite"),
                        ("AARTIIND.NS","Aarti Industries")],
    "EV & Tech":      [("TATAELXSI.NS","Tata Elxsi"), ("OLECTRA.NS","Olectra Greentech"),
                        ("EXIDEIND.NS","Exide Industries"), ("NETWEB.NS","Netweb Technologies"),
                        ("AMARAJABAT.NS","Amara Raja Batteries")],
}

if "watchlist_groups" not in st.session_state:
    st.session_state.watchlist_groups = {
        "Watchlist 1": [
            ("MAZDOCK.NS","Mazagon Dock"),
            ("HAL.NS","HAL"),
            ("GRSE.NS","GRSE"),
            ("COCHINSHIP.NS","Cochin Shipyard"),
            ("DATAPATTNS.NS","Data Patterns"),
            ("ZENTEC.NS","Zen Technologies"),
            ("PARAS.NS","Paras Defence"),
            ("UNIMECH.NS","Unimech Aerospace"),
            ("IDEAFORGE.NS","Ideaforge Tech"),
            ("KRISHNADEF.NS","Krishna Defence"),
        ],
        "Watchlist 2": [
            ("WAAREEENER.NS","Waaree Energies"),
            ("HEROMOTOCO.NS","Hero MotoCorp"),
            ("ANANTRAJ.NS","Anant Raj"),
            ("ORIENTTECH.NS","Orient Technologies"),
            ("EDELWEISS.NS","Edelweiss Financial"),
            ("VEDL.NS","Vedanta"),
            ("IRFC.NS","IRFC"),
            ("5PAISA.NS","5paisa Capital"),
            ("VIKRAMSOLR.NS","Vikram Solar"),
            ("THYROCARE.NS","Thyrocare Tech"),
            ("KEC.NS","KEC International"),
        ],
        "Watchlist 3": [
            ("BSE.NS","BSE Ltd"),
            ("ANGELONE.NS","Angel One"),
            ("KPITTECH.NS","KPIT Technologies"),
            ("JAINREC.NS","Jain Irrigation"),
            ("NETWEB.NS","Netweb Technologies"),
        ],
    }
    # ── 13 sector watchlists auto-create karo, pehli baar app load hote hi ────
    for _sec_name, _sec_stocks in SECTOR_WATCHLISTS.items():
        st.session_state.watchlist_groups[_sec_name] = list(_sec_stocks)
if "active_watchlist_group" not in st.session_state:
    st.session_state.active_watchlist_group = "Watchlist 1"

# ── Backfill: agar koi sector watchlist missing hai (purana session/pehle se ──
# ── chal rahi app) to use bhi add kar do, taaki sab 13 sector watchlists ──────
# ── hamesha dikhein, bina kisi button click ke ────────────────────────────────
for _sec_name, _sec_stocks in SECTOR_WATCHLISTS.items():
    if _sec_name not in st.session_state.watchlist_groups:
        st.session_state.watchlist_groups[_sec_name] = list(_sec_stocks)

# custom_watchlist hamesha currently-active group ko point karta hai
# (taaki neeche ka sara purana code bina change kiye kaam karta rahe)
st.session_state.custom_watchlist = st.session_state.watchlist_groups[st.session_state.active_watchlist_group]
if "portfolio_loaded" not in st.session_state:
    # Pehli baar — file se load karo
    saved = load_portfolio()
    if saved:
        st.session_state.pt_cash     = saved["pt_cash"]
        st.session_state.pt_holdings = saved["pt_holdings"]
        st.session_state.pt_history  = saved["pt_history"]
        st.session_state.pt_targets  = saved.get("pt_targets", [])
    else:
        st.session_state.pt_cash     = 10_000_000.0
        st.session_state.pt_holdings = {}
        st.session_state.pt_history  = []
        st.session_state.pt_targets  = []

    # Recovery and sync: if pt_holdings is empty but holdings.json has data, restore them!
    if not st.session_state.pt_holdings:
        try:
            holdings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdings.json")
            if os.path.exists(holdings_file):
                with open(holdings_file, "r") as f:
                    recovered_holdings = json.load(f)
                if recovered_holdings:
                    st.session_state.pt_holdings = recovered_holdings
                    # Standardize cash: if cash is too low or was reset, make sure it is at least ₹1 Crore (10,000,000.0)
                    if st.session_state.pt_cash < 10_000_000.0:
                        st.session_state.pt_cash = 10_000_000.0
                    
                    # Ensure trade history (Buy Orders) is synchronized
                    for tkr, h in recovered_holdings.items():
                        has_buy = any(
                            t.get("Ticker") == tkr and t.get("Action") == "BUY"
                            for t in st.session_state.pt_history
                        )
                        if not has_buy:
                            buy_date = h.get("first_buy_date", "2026-06-11")
                            try:
                                buy_time = datetime.strptime(buy_date, "%Y-%m-%d").strftime("%d %b %Y %I:%M %p")
                            except Exception:
                                buy_time = ist_now().strftime("%d %b %Y %I:%M %p")
                            
                            st.session_state.pt_history.append({
                                "Action": "BUY",
                                "Ticker": tkr,
                                "Name": tkr.replace(".NS", ""),
                                "Shares": h.get("shares", 0),
                                "Price": h.get("avg_price", 0.0),
                                "Value": round(h.get("shares", 0) * h.get("avg_price", 0.0), 2),
                                "P&L": None,
                                "Time": buy_time,
                            })
                    save_portfolio()
        except Exception:
            pass

    # ── Backfill: purani holdings jinme first_buy_date nahi hai, unke liye ──────
    # ── trade history se sabse pehli BUY ki date nikal ke set karo ───────────────
    _needs_backfill = any(
        "first_buy_date" not in h for h in st.session_state.pt_holdings.values()
    )
    if _needs_backfill:
        earliest_buy = {}
        for t in st.session_state.pt_history:
            if t.get("Action") != "BUY":
                continue
            tkr = t.get("Ticker")
            try:
                t_dt = datetime.strptime(t["Time"], "%d %b %Y %I:%M %p")
            except Exception:
                continue
            if tkr not in earliest_buy or t_dt < earliest_buy[tkr]:
                earliest_buy[tkr] = t_dt
        for tkr, h in st.session_state.pt_holdings.items():
            if "first_buy_date" not in h:
                if tkr in earliest_buy:
                    h["first_buy_date"] = earliest_buy[tkr].strftime("%Y-%m-%d")
                else:
                    # History mein bhi nahi mili — aaj ki date fallback (best effort)
                    h["first_buy_date"] = ist_now().strftime("%Y-%m-%d")
        save_portfolio()

    st.session_state.portfolio_loaded = True

# ── Cached data functions ──────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def get_trend_history(ticker, period="1mo"):
    """Cached + retrying historical price fetch, taaki har rerun pe Yahoo ko
    bombard na karna pade (jo 429 / blank-data errors deta hai).
    Returns (hist_df_or_None, last_error_str_or_None) for debugging."""
    import yfinance as yf, time
    last_err = None
    for attempt_period in [period, "5d", "1mo"]:
        for attempt in range(2):
            try:
                hist = yf.Ticker(ticker).history(period=attempt_period, interval="1d")
                if hist is not None and not hist.empty and len(hist) >= 2:
                    return hist, None
                elif hist is not None and hist.empty:
                    last_err = f"{ticker}: empty data (period={attempt_period})"
            except Exception as e:
                last_err = f"{ticker}: {type(e).__name__}: {e}"
            time.sleep(0.4)
    return None, last_err

@st.cache_data(ttl=120)  # Fixed safe TTL — cleared manually on refresh buttons
def get_index_quote(ticker):
    import yfinance as yf, math
    try:
        info = yf.Ticker(ticker).fast_info
        cur  = float(info.last_price)
        prev = float(info.previous_close)
        if math.isnan(cur) or math.isnan(prev) or prev == 0:
            raise ValueError("nan")
        chg  = cur - prev
        pct  = (chg / prev) * 100
        return cur, prev, chg, pct
    except Exception:
        try:
            hist = yf.Ticker(ticker).history(period="5d", interval="1d").dropna(subset=["Close"])
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                cur  = float(hist["Close"].iloc[-1])
                return cur, prev, cur-prev, ((cur-prev)/prev)*100
        except Exception:
            pass
        return None

@st.cache_data(ttl=120)  # Fixed safe TTL — cleared manually on refresh buttons
def get_indices_batch(tickers_tuple):
    """
    Multiple indices (ya stocks) ek hi yf.download() call mein fetch karo —
    teen alag-alag network round-trips ki jagah ek hi round-trip.
    Return: {ticker: (cur, prev, chg, pct) ya None}
    Top header (NIFTY/BANK NIFTY/SENSEX) jaisi jagah use hota hai jahan
    yeh har tab-switch pe chalta hai — yahan speed sबसे zyada matter karti hai.
    """
    import yfinance as yf, math
    results = {tkr: None for tkr in tickers_tuple}
    try:
        df = yf.download(" ".join(tickers_tuple), period="2d", interval="1d",
                         group_by="ticker", auto_adjust=True, progress=False, threads=True)
        for tkr in tickers_tuple:
            try:
                sub = df[tkr] if len(tickers_tuple) > 1 else df
                sub = sub.dropna(subset=["Close"])
                if len(sub) < 2:
                    continue
                prev = float(sub["Close"].iloc[-2])
                cur  = float(sub["Close"].iloc[-1])
                if math.isnan(cur) or math.isnan(prev) or prev == 0:
                    continue
                chg = cur - prev
                pct = (chg / prev) * 100
                results[tkr] = (cur, prev, chg, pct)
            except Exception:
                continue
    except Exception:
        pass

    # Koi ticker fail ho gaya batch mein (data missing) — usी ke liye fallback
    for tkr in tickers_tuple:
        if results[tkr] is None:
            results[tkr] = get_index_quote(tkr)
    return results

@st.cache_data(ttl=21600)   # 6 ghante cache — earnings date din mein 1-2 baar hi check karna kaafi hai
def get_holdings_results_today(tickers_tuple):
    """
    Har holding ke liye yfinance se earnings/result date try karte hain.
    NSE smallcap stocks ke liye yeh data zyादातar available NAHI hota
    (Yahoo Finance ka Indian coverage weak hai) — agar na mile to
    silently skip karte hain, koi error/crash nahi.
    Return: set of tickers jinka result AAJ hi hai (exact date match).
    """
    import yfinance as yf
    today = ist_now().date()
    result_today = set()
    for tkr in tickers_tuple:
        try:
            cal = yf.Ticker(tkr).calendar
            if not cal:
                continue
            earnings_dates = cal.get("Earnings Date")
            if not earnings_dates:
                continue
            for ed in earnings_dates:
                ed_date = ed.date() if hasattr(ed, "date") else ed
                if ed_date == today:
                    result_today.add(tkr)
                    break
        except Exception:
            continue  # data nahi mila ya format alag tha — skip, crash nahi
    return result_today

@st.cache_data(ttl=120)  # Fixed safe TTL — cleared manually on refresh buttons
def get_batch_quotes(tickers_tuple):
    import yfinance as yf
    import math
    results = {}
    if not tickers_tuple:
        return results

    # PERFORMANCE: Use batch download (1 HTTP req) instead of per-ticker fast_info calls
    try:
        df = yf.download(
            " ".join(tickers_tuple), period="2d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True
        )
        for tkr in tickers_tuple:
            try:
                sub = df[tkr] if len(tickers_tuple) > 1 else df
                sub = sub.dropna(subset=["Close"])
                if len(sub) < 2:
                    continue
                prev = float(sub["Close"].iloc[-2])
                cur  = float(sub["Close"].iloc[-1])
                if math.isnan(cur) or math.isnan(prev) or prev == 0:
                    continue
                chg = cur - prev
                pct = (chg / prev) * 100
                results[tkr] = (cur, prev, chg, pct)
            except Exception:
                continue
    except Exception:
        pass

    # Fallback: fast_info per-ticker for any that failed in batch
    missing = [t for t in tickers_tuple if t not in results]
    for tkr in missing:
        try:
            fi  = yf.Ticker(tkr).fast_info
            cur  = float(fi.last_price)
            prev = float(fi.previous_close)
            if math.isnan(cur) or math.isnan(prev) or prev == 0:
                raise ValueError("nan")
            chg = cur - prev
            pct = (chg / prev) * 100
            results[tkr] = (cur, prev, chg, pct)
        except Exception:
            continue
    return results

# ── PERMANENT FIX: Portfolio + Home tab dono pehle har render pe alag-alag, ────
# ── bina caching ke, har holding ke liye yf.Ticker().info call karte the — ─────
# ── isliye Portfolio (aur Home) tab khulne mein bahut time lagta tha. Ab ye ────
# ── ek shared, CACHED function hai (60s TTL market hours mein) — Portfolio ─────
# ── aur Home dono isi ek function ko call karte hain, isliye: ──────────────────
# ── (1) Pehli baar fetch hone ke baad 60 second tak instant load hota hai ──────
# ── (2) Portfolio aur Home do alag network calls nahi karte same data ke liye ──
@st.cache_data(ttl=120)  # Fixed safe TTL — fast_info first for speed
def get_holdings_live_prices(holdings_tuple):
    """holdings_tuple = ((ticker, shares, avg_price), ...) — hashable, cache key ban sake.
    PERFORMANCE: Uses fast_info (fastest yfinance API) as primary method.
    """
    import yfinance as _yf
    import math
    results = {}
    for tkr, _shares, _avg in holdings_tuple:
        try:
            # fast_info is MUCH faster than .info — use as primary fetch
            t = _yf.Ticker(tkr)
            fi = t.fast_info
            prev_c = fi.previous_close
            live_c = fi.last_price or prev_c
            if prev_c is None or live_c is None or math.isnan(float(prev_c)):
                raise ValueError("Incomplete fast_info")
            results[tkr] = {"prev_close": float(prev_c), "live_price": float(live_c)}
        except Exception:
            try:
                hist = t.history(period="5d", interval="1d").dropna(subset=["Close"])
                if len(hist) >= 2:
                    prev_c = float(hist["Close"].iloc[-2])
                    live_c = float(hist["Close"].iloc[-1])
                    results[tkr] = {"prev_close": prev_c, "live_price": live_c}
                else:
                    results[tkr] = {"prev_close": None, "live_price": None}
            except Exception:
                results[tkr] = {"prev_close": None, "live_price": None}
    return results

@st.cache_data(ttl=7200)
def get_stock_info(ticker):
    """52W high/low, P/E, Market Cap, sector ek call mein."""
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info
        return {
            "w52_high":   info.get("fiftyTwoWeekHigh"),
            "w52_low":    info.get("fiftyTwoWeekLow"),
            "pe":         info.get("trailingPE"),
            "mktcap":     info.get("marketCap"),
            "sector":     info.get("sector", ""),
            "industry":   info.get("industry", ""),
            "div_yield":  info.get("dividendYield"),
        }
    except Exception:
        try:
            t = yf.Ticker(ticker)
            fi = t.fast_info
            return {
                "w52_high":   fi.year_high,
                "w52_low":    fi.year_low,
                "pe":         None,
                "mktcap":     fi.market_cap,
                "sector":     "",
                "industry":   "",
                "div_yield":  None,
            }
        except Exception:
            return {}

@st.cache_data(ttl=1800)
def get_rsi_ma_signal(ticker: str):
    """RSI(14) + 20-day MA signal. Returns signal dict or None."""
    import yfinance as yf, numpy as np
    try:
        hist = yf.Ticker(ticker).history(period="60d", interval="1d").dropna(subset=["Close"])
        if len(hist) < 22:
            return None
        closes = hist["Close"].values.astype(float)
        price  = closes[-1]
        # RSI(14)
        deltas   = np.diff(closes)
        gains    = np.where(deltas > 0, deltas, 0.0)
        losses   = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = gains[:14].mean()
        avg_loss = losses[:14].mean()
        for i in range(14, len(gains)):
            avg_gain = (avg_gain * 13 + gains[i]) / 14
            avg_loss = (avg_loss * 13 + losses[i]) / 14
        rs  = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = round(100 - (100 / (1 + rs)), 1)
        # 20-day MA
        ma20     = round(float(np.mean(closes[-20:])), 2)
        price    = round(price, 2)
        above_ma = price > ma20
        ma_dist  = round((price - ma20) / ma20 * 100, 1)
        # Signal logic
        if rsi < 30:
            signal,label,color = "STRONG BUY","🟢 STRONG BUY","#00c853"
            detail = f"RSI {rsi} — Bahut oversold! Strong bounce possible"
        elif rsi < 42 and above_ma:
            signal,label,color = "BUY","🟢 BUY","#27ae60"
            detail = f"RSI {rsi} + MA se upar — Entry consider karo"
        elif rsi < 42:
            signal,label,color = "WEAK BUY","🟡 WEAK BUY","#84cc16"
            detail = f"RSI {rsi} oversold but MA se neeche — wait karo"
        elif rsi < 55 and above_ma:
            signal,label,color = "NEUTRAL","⚪ NEUTRAL","#8b90a0"
            detail = f"RSI {rsi} — Normal zone, koi strong signal nahi"
        elif rsi < 55:
            signal,label,color = "WEAK SELL","🟡 CAUTION","#f59e0b"
            detail = f"RSI {rsi} + MA se neeche — momentum weak"
        elif rsi < 70:
            signal,label,color = "CAUTION","🟠 CAUTION","#f97316"
            detail = f"RSI {rsi} — Overbought aa raha hai, SL tight rakho"
        else:
            signal,label,color = "OVERBOUGHT","🔴 OVERBOUGHT","#e74c3c"
            detail = f"RSI {rsi} — Bahut overbought! Profit booking consider karo"
        return dict(rsi=rsi, ma20=ma20, price=price, above_ma=above_ma,
                    ma_dist=ma_dist, signal=signal, label=label, color=color, detail=detail)
    except Exception:
        return None

@st.cache_data(ttl=1800)
def get_batch_rsi(tickers_tuple):
    """Saare watchlist stocks ka RSI+MA ek batch mein — fast & cached."""
    import yfinance as yf, numpy as np
    results = {}
    try:
        df = yf.download(
            " ".join(tickers_tuple), period="60d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True
        )
        for tkr in tickers_tuple:
            try:
                sub    = df[tkr]["Close"] if len(tickers_tuple) > 1 else df["Close"]
                closes = sub.dropna().values.astype(float)
                if len(closes) < 22: continue
                deltas = np.diff(closes)
                gains  = np.where(deltas > 0, deltas, 0.0)
                losses = np.where(deltas < 0, -deltas, 0.0)
                ag = gains[:14].mean(); al = losses[:14].mean()
                for i in range(14, len(gains)):
                    ag = (ag*13+gains[i])/14; al = (al*13+losses[i])/14
                rs  = ag/al if al > 0 else 100
                rsi = round(100-(100/(1+rs)), 1)
                ma20     = round(float(np.mean(closes[-20:])), 2)
                price    = round(float(closes[-1]), 2)
                above_ma = price > ma20
                ma_dist  = round((price-ma20)/ma20*100, 1)
                if rsi < 30:
                    label,color = "🟢 STRONG BUY","#00c853"
                    detail = f"RSI {rsi} — Bahut oversold! Strong bounce possible"
                elif rsi < 42 and above_ma:
                    label,color = "🟢 BUY","#27ae60"
                    detail = f"RSI {rsi} + MA se upar — Entry consider karo"
                elif rsi < 42:
                    label,color = "🟡 WEAK BUY","#84cc16"
                    detail = f"RSI {rsi} oversold but MA se neeche — wait karo"
                elif rsi < 55 and above_ma:
                    label,color = "⚪ NEUTRAL","#8b90a0"
                    detail = f"RSI {rsi} — Normal zone"
                elif rsi < 55:
                    label,color = "🟡 CAUTION","#f59e0b"
                    detail = f"RSI {rsi} + MA se neeche — momentum weak"
                elif rsi < 70:
                    label,color = "🟠 CAUTION","#f97316"
                    detail = f"RSI {rsi} — Overbought aa raha hai, SL tight rakho"
                else:
                    label,color = "🔴 OVERBOUGHT","#e74c3c"
                    detail = f"RSI {rsi} — Bahut overbought! Profit booking consider karo"
                results[tkr] = dict(rsi=rsi, ma20=ma20, price=price, above_ma=above_ma,
                                    ma_dist=ma_dist, label=label, color=color, detail=detail)
            except Exception:
                continue
    except Exception:
        pass
    return results

@st.cache_data(ttl=1800)
def get_batch_52w_range(tickers_tuple):
    """
    52-week high/low + current price ka position — "stock apne saal ke range
    mein kahan khada hai" (high ke kareeb = momentum, low ke kareeb = value/risk).
    get_batch_rsi jaisa hi proven batch+cache pattern.
    """
    import yfinance as yf
    results = {}
    try:
        df = yf.download(
            " ".join(tickers_tuple), period="1y", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True
        )
        for tkr in tickers_tuple:
            try:
                sub    = df[tkr]["Close"] if len(tickers_tuple) > 1 else df["Close"]
                closes = sub.dropna().values.astype(float)
                if len(closes) < 5: continue
                w52_high = float(closes.max())
                w52_low  = float(closes.min())
                price    = float(closes[-1])
                if w52_high <= w52_low: continue
                pos_pct = (price - w52_low) / (w52_high - w52_low) * 100  # 0=low, 100=high
                pos_pct = max(0.0, min(100.0, pos_pct))
                from_high_pct = (price - w52_high) / w52_high * 100  # negative ya 0
                results[tkr] = dict(w52_high=round(w52_high, 2), w52_low=round(w52_low, 2),
                                    price=round(price, 2), pos_pct=round(pos_pct, 1),
                                    from_high_pct=round(from_high_pct, 1))
            except Exception:
                continue
    except Exception:
        pass
    return results

@st.cache_data(ttl=300)  # Fixed safe TTL — chart data, 5 min cache is fine
def fetch_stock_data_cached(ticker: str, period: str = "3mo", interval: str = "1d"):
    import yfinance as yf
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        df.reset_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df
    except Exception:
        return None

def get_stock_chart(ticker: str, period: str = "3mo", interval: str = "1d",
                    chart_type="Candlestick", indicators=["Volume"],
                    comparison_tickers=None, show_prediction=False,
                    fullscreen=False):
    df = fetch_stock_data_cached(ticker, period, interval)
    if df is None or df.empty:
        return None

    # Calculate indicators
    df = add_indicators(df)

    # Build prediction if requested
    prediction_df = None
    if show_prediction:
        prediction_df = predict_prices(df)

    # Build comparison dfs if requested
    comparison_df_dict = None
    if comparison_tickers:
        comparison_df_dict = {}
        for comp_tkr in comparison_tickers:
            comp_df = fetch_stock_data_cached(comp_tkr, period, interval)
            if comp_df is not None and not comp_df.empty:
                comparison_df_dict[comp_tkr] = comp_df

    # Render premium chart
    from utils.visualizations import create_premium_chart
    theme_mode = "dark" if st.session_state.dark_mode else "light"
    return create_premium_chart(
        df, ticker, chart_type=chart_type, indicators=indicators,
        prediction_df=prediction_df, comparison_df_dict=comparison_df_dict,
        theme_mode=theme_mode, fullscreen=fullscreen
    )


@st.cache_data(ttl=300)  # Fixed safe TTL — market breadth, 5 min cache
def get_market_breadth():
    """
    Market Breadth — Advance/Decline ratio + Gap movers, ek broad Nifty-representative
    pool (~40 large/liquid stocks) pe based, taaki sirf 1-2 sector ka noise na ho.
    Pro-trader signal: agar index +1% hai par breadth weak hai, matlab sirf
    handful bade stocks index khinch rahe hain — poora market broad-based nahi
    chal raha. Note: yfinance daily close-to-close use hota hai — NSE ke actual
    9:00-9:08 pre-open session ka live indicative price yahan nahi hai, isliye
    "Gap Movers" ko "abhi tak ka biggest move from previous close" maano,
    asli live pre-open gap ke liye broker app dekho.
    """
    import yfinance as yf
    NIFTY_BREADTH_POOL = [
        "RELIANCE.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS","SBIN.NS","TCS.NS",
        "BAJFINANCE.NS","LT.NS","HINDUNILVR.NS","SUNPHARMA.NS","AXISBANK.NS","MARUTI.NS",
        "INFY.NS","ADANIPORTS.NS","KOTAKBANK.NS","ADANIENT.NS","TITAN.NS","M&M.NS",
        "ITC.NS","NTPC.NS","ULTRACEMCO.NS","ONGC.NS","BEL.NS","WIPRO.NS","ASIANPAINT.NS",
        "BAJAJFINSV.NS","HCLTECH.NS","TMPV.NS","TATASTEEL.NS","POWERGRID.NS",
        "COALINDIA.NS","NESTLEIND.NS","GRASIM.NS","JSWSTEEL.NS","HDFCLIFE.NS","SBILIFE.NS",
        "DRREDDY.NS","CIPLA.NS","TECHM.NS","INDUSINDBK.NS","APOLLOHOSP.NS",
    ]
    # ── BUG FIX: bulk yf.download(group_by="ticker") is environment mein kabhi-kabhi ──
    # ── empty/fail ho jaata hai (Portfolio P&L mein bhi yahi issue mil chuka hai). ────
    # ── Isliye per-ticker yfinance.Ticker().info use kar rahe hain — wahi reliable ────
    # ── source jo Day's P&L fix mein kaam kiya tha. ───────────────────────────────────
    try:
        moves = []
        for tkr in NIFTY_BREADTH_POOL:
            try:
                info = yf.Ticker(tkr).info
                prev = info.get("previousClose")
                cur  = info.get("currentPrice") or info.get("regularMarketPrice") or prev
                if not prev or prev <= 0 or not cur:
                    continue
                pct = ((cur - prev) / prev) * 100
                moves.append({"ticker": tkr, "name": tkr.replace(".NS",""),
                             "price": cur, "chg_pct": pct})
            except Exception:
                continue

        advances  = [m for m in moves if m["chg_pct"] > 0.02]
        declines  = [m for m in moves if m["chg_pct"] < -0.02]
        unchanged = len(moves) - len(advances) - len(declines)

        gap_movers = sorted(moves, key=lambda m: abs(m["chg_pct"]), reverse=True)[:8]

        return {
            "advances": len(advances), "declines": len(declines), "unchanged": unchanged,
            "total": len(moves), "gap_movers": gap_movers,
        }
    except Exception:
        return {"advances": 0, "declines": 0, "unchanged": 0, "total": 0, "gap_movers": []}

@st.cache_data(ttl=300)  # Fixed safe TTL — top movers, 5 min cache
def get_nse_top_movers():
    import yfinance as yf
    NSE_POOL = [
        "MAZDOCK.NS","HAL.NS","GRSE.NS","COCHINSHIP.NS","DATAPATTNS.NS","ZENTEC.NS","PARAS.NS","UNIMECH.NS","IDEAFORGE.NS","KRISHNADEF.NS","BSE.NS","ANGELONE.NS","KPITTECH.NS","JAINREC.NS",
    ]
    try:
        df = yf.download(" ".join(NSE_POOL), period="2d", interval="1d",
                         group_by="ticker", auto_adjust=True, progress=False, threads=True)
        movers = []
        for tkr in NSE_POOL:
            try:
                sub  = df[tkr] if len(NSE_POOL) > 1 else df
                if sub is None or len(sub) < 2: continue
                prev = float(sub["Close"].iloc[-2])
                cur  = float(sub["Close"].iloc[-1])
                if prev <= 0: continue
                chg = cur - prev
                pct = (chg / prev) * 100
                movers.append({"ticker": tkr, "name": tkr.replace(".NS",""),
                               "price": cur, "chg": chg, "chg_pct": pct})
            except Exception:
                continue
        movers.sort(key=lambda x: x["chg_pct"], reverse=True)
        return [m for m in movers if m["chg_pct"] > 0][:10], \
               [m for m in movers if m["chg_pct"] < 0][::-1][:10]
    except Exception:
        return [], []

@st.cache_data(ttl=900)
def get_screener_data(holding_tickers: tuple = ()):
    """Fetch detailed info for screener stocks — holdings se auto-merge."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    import pandas as pd
    from utils.analytics import add_indicators

    BASE_POOL = [
        "MAZDOCK.NS","HAL.NS","GRSE.NS","COCHINSHIP.NS","DATAPATTNS.NS","ZENTEC.NS",
        "PARAS.NS","UNIMECH.NS","IDEAFORGE.NS","KRISHNADEF.NS","BSE.NS","ANGELONE.NS",
        "KPITTECH.NS","JAINREC.NS","NETWEB.NS","THYROCARE.NS",
    ]
    SCREENER_POOL = list(dict.fromkeys(BASE_POOL + list(holding_tickers)))
    
    # 1. Batch download 3-month historical data
    try:
        histories = yf.download(SCREENER_POOL, period="3mo", progress=False, group_by="ticker")
    except Exception:
        histories = None

    def get_ticker_history(tkr):
        if histories is None or histories.empty:
            return None
        try:
            if isinstance(histories.columns, pd.MultiIndex):
                if tkr in histories.columns.levels[0]:
                    df = histories[tkr].copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [col[0] if col[1] == "" else col[0] for col in df.columns]
                    return df
            else:
                return histories.copy()
        except Exception:
            pass
        return None

    def fetch_single_ticker(tkr):
        try:
            t = yf.Ticker(tkr)
            info = t.info or {}
            
            ticker_hist = get_ticker_history(tkr)
            
            # Technical Indicators
            rsi_val = None
            sma20_val = None
            sma50_val = None
            macd_val = None
            macd_signal_val = None
            
            if ticker_hist is not None and not ticker_hist.empty:
                try:
                    df_ind = add_indicators(ticker_hist)
                    if not df_ind.empty:
                        last_row = df_ind.iloc[-1]
                        rsi_val = last_row.get("RSI")
                        sma20_val = last_row.get("SMA_20")
                        sma50_val = last_row.get("SMA_50")
                        macd_val = last_row.get("MACD")
                        macd_signal_val = last_row.get("MACD_Signal")
                except Exception:
                    pass

            # Fallbacks using history
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not price and ticker_hist is not None and not ticker_hist.empty:
                price = ticker_hist["Close"].dropna().iloc[-1] if not ticker_hist["Close"].dropna().empty else 0
            price = price or 0

            prev = info.get("previousClose")
            if not prev and ticker_hist is not None and len(ticker_hist) > 1:
                prev = ticker_hist["Close"].dropna().iloc[-2] if len(ticker_hist["Close"].dropna()) > 1 else price
            prev = prev or price

            volume = info.get("volume")
            if not volume and ticker_hist is not None and not ticker_hist.empty:
                volume = ticker_hist["Volume"].dropna().iloc[-1] if not ticker_hist["Volume"].dropna().empty else 0
            volume = volume or 0

            avg_vol = info.get("averageVolume") or info.get("threeMonthAverageVolume")
            if not avg_vol and ticker_hist is not None and not ticker_hist.empty:
                avg_vol = ticker_hist["Volume"].mean()
            avg_vol = avg_vol or volume or 1

            w52h = info.get("fiftyTwoWeekHigh")
            if not w52h and ticker_hist is not None and not ticker_hist.empty:
                w52h = ticker_hist["High"].max()
            w52h = w52h or price

            w52l = info.get("fiftyTwoWeekLow")
            if not w52l and ticker_hist is not None and not ticker_hist.empty:
                w52l = ticker_hist["Low"].min()
            w52l = w52l or price

            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            mktcap = info.get("marketCap") or 0
            sector = info.get("sector") or "—"
            name = info.get("shortName") or tkr.replace(".NS","")
            
            chg_pct = ((price - prev) / prev * 100) if prev else 0
            from_52h = ((price - w52h) / w52h * 100) if w52h else 0
            from_52l = ((price - w52l) / w52l * 100) if w52l else 0
            vol_ratio = (volume / avg_vol) if avg_vol else 1
            
            return {
                "ticker": tkr, 
                "name": name, 
                "sector": sector,
                "price": round(price, 2),
                "chg_pct": round(chg_pct, 2),
                "pe": round(pe, 1) if pe else None,
                "pb": round(pb, 2) if pb else None,
                "w52h": round(w52h, 2), 
                "w52l": round(w52l, 2),
                "from_52h": round(from_52h, 1),
                "from_52l": round(from_52l, 1),
                "volume": int(volume),
                "avg_volume": int(avg_vol),
                "vol_ratio": round(vol_ratio, 2),
                "mktcap": mktcap,
                "rsi": round(rsi_val, 1) if rsi_val is not None and not pd.isna(rsi_val) else None,
                "sma20": round(sma20_val, 2) if sma20_val is not None and not pd.isna(sma20_val) else None,
                "sma50": round(sma50_val, 2) if sma50_val is not None and not pd.isna(sma50_val) else None,
                "macd": round(macd_val, 4) if macd_val is not None and not pd.isna(macd_val) else None,
                "macd_signal": round(macd_signal_val, 4) if macd_signal_val is not None and not pd.isna(macd_signal_val) else None,
            }
        except Exception:
            return None

    # Fetch in parallel with up to 12 workers
    with ThreadPoolExecutor(max_workers=12) as executor:
        raw_results = list(executor.map(fetch_single_ticker, SCREENER_POOL))
        
    results = [r for r in raw_results if r is not None]
    return results

@st.cache_data(ttl=600)  # Single cache decorator — dual stacking was a bug
def fetch_mc_news(query: str, max_items: int = 6) -> list:
    """Fetch news from Moneycontrol via Google News RSS (site:moneycontrol.com filter)."""
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    try:
        q   = urllib.parse.quote(f"site:moneycontrol.com {query}")
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
        root  = ET.fromstring(xml_data)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title   = item.findtext("title", "").strip()
            link    = item.findtext("link",  "").strip()
            pubdate = item.findtext("pubDate","").strip()
            source  = item.findtext("source","Moneycontrol").strip()
            try:
                from datetime import datetime
                dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
                ts = dt.strftime("%d %b, %I:%M %p")
            except Exception:
                ts = pubdate[:16]
            if title and link:
                items.append({"title": title, "link": link, "time": ts, "source": source or "Moneycontrol"})
        return items
    except Exception:
        return []

@st.cache_data(ttl=900)  # 15 min cache — geopolitical news changes fast
def fetch_readiness_news() -> dict:
    """
    Fetch geopolitical/defence news and calculate Defence Readiness Index (0-10).
    Returns: {score, level, color, news_items, keyword_hits, summary}
    """
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    import pytz, re

    IST_TZ = pytz.timezone("Asia/Kolkata")

    # Search queries — geopolitical tension signals
    QUERIES = [
        "India Pakistan border tension military 2025",
        "India China LAC standoff military 2025",
        "India defence alert military strike 2025",
        "India war threat ceasefire violation 2025",
        "India surgical strike airstrike military 2025",
        "India army navy airforce deployment 2025",
        "Pakistan India ceasefire violation LoC 2025",
        "China India border Arunachal Ladakh 2025",
    ]

    # Keyword scoring weights
    CRITICAL_WORDS = {
        # Very high tension (3 points each)
        "war": 3, "strike": 3, "airstrike": 3, "surgical strike": 3,
        "attack": 3, "shelling": 3, "ceasefire violated": 3, "combat": 3,
        "missile": 3, "bomb": 3, "killed": 2.5, "martyred": 2.5,
        # High tension (2 points each)
        "tension": 2, "standoff": 2, "clash": 2, "firing": 2,
        "infiltration": 2, "terrorist": 2, "loc violation": 2,
        "military alert": 2, "high alert": 2, "mobilize": 2,
        "deployment": 1.5, "troops": 1.5, "warship": 1.5,
        # Moderate tension (1 point each)
        "border": 1, "patrol": 1, "exercise": 1, "drill": 1,
        "meeting": 0.5, "talks": 0.5, "diplomatic": 0.5,
    }

    # De-escalation words (reduce score)
    PEACE_WORDS = {
        "peace": -1.5, "ceasefire": -1, "dialogue": -1,
        "bilateral": -0.5, "cooperation": -0.5, "agreement": -0.5,
        "resolved": -1.5, "de-escalation": -2, "withdrawal": -1,
    }

    seen = set()
    all_news = []
    raw_score = 0.0
    keyword_hits = {}

    for query in QUERIES:
        try:
            q   = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                xml_data = r.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item")[:5]:
                title   = item.findtext("title",   "").strip()
                link    = item.findtext("link",    "").strip()
                pubdate = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None and source_el.text else "News"

                if not title or not link:
                    continue
                key = title[:60].lower()
                if key in seen:
                    continue
                seen.add(key)

                tl = title.lower()

                # Score this headline
                item_score = 0.0
                for kw, pts in CRITICAL_WORDS.items():
                    if kw in tl:
                        item_score += pts
                        keyword_hits[kw] = keyword_hits.get(kw, 0) + 1
                for kw, pts in PEACE_WORDS.items():
                    if kw in tl:
                        item_score += pts  # pts are negative

                # Only include relevant news (score > 0 or mentions key countries)
                is_relevant = (
                    item_score > 0 or
                    any(w in tl for w in ["india", "pakistan", "china", "lac", "loc", "border",
                                          "army", "navy", "iaf", "drdo", "defence"])
                )
                if not is_relevant:
                    continue

                raw_score += max(0, item_score)

                # Format time
                try:
                    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
                    dt = dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
                    ts = dt.strftime("%d %b, %I:%M %p")
                    recency_hours = (datetime.now(IST_TZ) - dt).total_seconds() / 3600
                except Exception:
                    ts = "—"; recency_hours = 48

                # Boost score for very recent news (< 6 hours)
                if recency_hours < 6:
                    raw_score += 0.5

                # Clean title
                for sfx in [" - The Hindu", " - NDTV", " - Times of India",
                            " - India Today", " - Hindustan Times", " - ANI"]:
                    if title.endswith(sfx):
                        title = title[:-len(sfx)].strip()

                all_news.append({
                    "title":        title,
                    "link":         link,
                    "time":         ts,
                    "source":       source,
                    "item_score":   round(item_score, 1),
                    "recency_hrs":  round(recency_hours, 1),
                })
        except Exception:
            continue

    # Normalize score to 0-10
    # raw_score > 20 = maximum tension
    normalized = min(10.0, round(raw_score / 2.5, 1))

    # Level classification
    if normalized >= 8:
        level  = "CRITICAL"
        color  = "#dc2626"
        bg     = "#1c0505"
        emoji  = "🔴"
        advice = "Bahut HIGH tension! Defence stocks HOLD karo — major rally possible. Risk high hai."
        stock_signal = "STRONG HOLD / BUY DIP"
    elif normalized >= 6:
        level  = "HIGH"
        color  = "#ea580c"
        bg     = "#1c0a05"
        emoji  = "🟠"
        advice = "Tension elevated hai. Defence stocks bullish bias. Positions add kar sakte ho."
        stock_signal = "BULLISH — Add positions"
    elif normalized >= 4:
        level  = "MODERATE"
        color  = "#ca8a04"
        bg     = "#1a1505"
        emoji  = "🟡"
        advice = "Kuch tension hai par normal range mein. Wait and watch karo."
        stock_signal = "NEUTRAL — Hold current"
    elif normalized >= 2:
        level  = "LOW"
        color  = "#16a34a"
        bg     = "#051a0a"
        emoji  = "🟢"
        advice = "Tension low hai. Defence stocks fundamentals pe chalenge, news pe nahi."
        stock_signal = "NEUTRAL — Fundamentals focus"
    else:
        level  = "MINIMAL"
        color  = "#0891b2"
        bg     = "#051318"
        emoji  = "🔵"
        advice = "Koi significant tension nahi. Markets peaceful hain."
        stock_signal = "NO SIGNAL"

    # Sort news: highest score first, then recency
    all_news.sort(key=lambda x: (-x["item_score"], x["recency_hrs"]))

    return {
        "score":        normalized,
        "raw_score":    round(raw_score, 1),
        "level":        level,
        "color":        color,
        "bg":           bg,
        "emoji":        emoji,
        "advice":       advice,
        "stock_signal": stock_signal,
        "news":         all_news[:20],
        "keyword_hits": keyword_hits,
        "total_articles": len(all_news),
    }

@st.cache_data(ttl=900)
def fetch_sector_index(sector_key: str) -> dict:
    """
    Generic opportunity index for it_tech / solar_energy / capital_markets /
    nbfc_finance / industrials_more / broking / renewable / ev_tech / banking.
    Same scoring approach as fetch_readiness_news but with sector-specific keywords.
    """
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    import pytz
    IST_TZ = pytz.timezone("Asia/Kolkata")

    SECTOR_CONFIGS = {
        "it_tech": {
            "queries": ["India IT services hiring growth 2025",
                        "Orient Technologies KPIT Netweb order deal 2025",
                        "India data center HPC server demand 2025"],
            "pos": ["deal","order","contract","growth","hiring","expansion","record","ai","demand","export"],
            "neg": ["layoff","slowdown","cut","attrition","decline","weak"],
        },
        "solar_energy": {
            "queries": ["India solar manufacturing capacity 2025",
                        "Waaree Vikram Solar order export 2025",
                        "India solar PLI scheme module 2025"],
            "pos": ["solar","capacity","gw","pli","export","order","record","subsidy","expansion"],
            "neg": ["delay","import duty cut","oversupply","china dumping","cancel"],
        },
        "capital_markets": {
            "queries": ["India stock exchange BSE trading volume 2025",
                        "Angel One 5paisa broking growth clients 2025",
                        "India retail investor demat IPO 2025"],
            "pos": ["volume","ipo","record","demat","growth","listing","rally","bull"],
            "neg": ["ban","penalty","fine","crash","bear","slowdown","fraud"],
        },
        "nbfc_finance": {
            "queries": ["India NBFC lending growth 2025",
                        "Edelweiss IRFC railway finance 2025",
                        "India credit growth asset management 2025"],
            "pos": ["growth","credit","profit","record","expansion","disbursement","aum"],
            "neg": ["npa","default","stress","fraud","downgrade","crisis"],
        },
        "industrials_more": {
            "queries": ["India auto 2-wheeler sales Hero MotoCorp 2025",
                        "India realty metals KEC infrastructure order 2025",
                        "India healthcare diagnostics Thyrocare 2025"],
            "pos": ["order","sales","record","growth","contract","expansion","demand"],
            "neg": ["decline","slowdown","weak","cut","loss"],
        },
        "broking": {
            "queries": ["India stock market retail investors demat accounts 2025",
                        "NSE BSE trading volumes record FY26",
                        "India IPO market boom broking revenue 2025"],
            "pos": ["ipo","demat","volume","retail","record","sebi","bull","rally","growth","listing"],
            "neg": ["ban","penalty","fine","crash","bear","slowdown","fraud","scam"],
        },
        "renewable": {
            "queries": ["India solar energy capacity GW record 2025",
                        "India renewable energy policy government 2025",
                        "India green hydrogen solar wind investment 2025"],
            "pos": ["solar","renewable","green","capacity","gw","pli","export","record","investment"],
            "neg": ["delay","import","china","slow","cancel","pollution"],
        },
        "ev_tech": {
            "queries": ["India electric vehicle EV sales record 2025",
                        "India EV policy FAME subsidy government 2025",
                        "KPIT Technologies automotive software revenue 2025"],
            "pos": ["ev","electric","vehicle","fame","charging","battery","record","software","order"],
            "neg": ["slowdown","delay","subsidy cut","recall","accident"],
        },
        "banking": {
            "queries": ["India bank credit growth RBI 2025",
                        "India NPA bad loans banking sector 2025",
                        "RBI monetary policy repo rate India 2025"],
            "pos": ["credit","growth","profit","record","rate cut","npa fall","recovery","lending"],
            "neg": ["npa","stress","default","fraud","rate hike","slowdown","crisis"],
        },
    }

    cfg = SECTOR_CONFIGS.get(sector_key, SECTOR_CONFIGS["industrials_more"])
    seen = set()
    all_news = []
    raw_score = 0.0
    keyword_hits = {}

    for query in cfg["queries"]:
        try:
            q   = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                xml_data = r.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:6]:
                title   = item.findtext("title",   "").strip()
                link    = item.findtext("link",    "").strip()
                pubdate = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None and source_el.text else "News"
                if not title or not link:
                    continue
                key = title[:60].lower()
                if key in seen:
                    continue
                seen.add(key)
                tl = title.lower()
                item_score = 0.0
                for kw in cfg["pos"]:
                    if kw in tl:
                        item_score += 1.5
                        keyword_hits[kw] = keyword_hits.get(kw, 0) + 1
                for kw in cfg["neg"]:
                    if kw in tl:
                        item_score -= 1.5
                raw_score += max(0, item_score)
                try:
                    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
                    dt = dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
                    ts = dt.strftime("%d %b, %I:%M %p")
                except Exception:
                    ts = "—"
                for sfx in [" - Economic Times"," - Mint"," - Moneycontrol"," - Business Standard"]:
                    if title.endswith(sfx):
                        title = title[:-len(sfx)].strip()
                all_news.append({"title": title, "link": link, "time": ts,
                                 "source": source, "item_score": round(item_score, 1)})
        except Exception:
            continue

    normalized = min(10.0, round(raw_score / 2.0, 1))
    if normalized >= 7:
        level, color, emoji = "STRONG", "#27ae60", "🟢"
        advice = "Sector mein strong positive momentum hai! Stocks bullish bias mein."
        signal = "BULLISH — Positive news flow"
        bg = "#051a0a"
    elif normalized >= 4:
        level, color, emoji = "MODERATE", "#f59e0b", "🟡"
        advice = "Mixed signals hain. Fundamentals pe focus rakho."
        signal = "NEUTRAL — Mixed signals"
        bg = "#1a1505"
    else:
        level, color, emoji = "WEAK", "#e74c3c", "🔴"
        advice = "Koi major positive catalyst nahi mila. Wait and watch."
        signal = "CAUTIOUS — Await catalysts"
        bg = "#1c0808"

    all_news.sort(key=lambda x: -x["item_score"])
    return {
        "score": normalized, "level": level, "color": color, "bg": bg,
        "emoji": emoji, "advice": advice, "stock_signal": signal,
        "news": all_news[:15], "keyword_hits": keyword_hits,
        "total_articles": len(all_news),
    }


def render_sector_index(sector_key: str, widget_key: str):
    """Reusable Readiness/Opportunity Index UI — used by all sector tabs."""
    _, _rc = st.columns([4, 1])
    with _rc:
        if st.button("🔄 Refresh", key=f"ri_{widget_key}", width='stretch'):
            fetch_sector_index.clear()
            st.rerun()

    with st.spinner("📡 Sector news scan ho rahi hai..."):
        ri = fetch_sector_index(sector_key)

    sc    = ri["score"]
    color = ri["color"]
    bg    = ri["bg"]
    emoji_level = ri["emoji"]

    segs = ""
    for i in range(10):
        filled = i < int(sc)
        clr = color if filled else "#2a2d3a"
        segs += f'<div style="flex:1;height:12px;background:{clr};border-radius:3px;margin:0 2px;"></div>'

    st.markdown(f"""
    <div style="background:{bg};border:2px solid {color}55;border-radius:16px;
                padding:20px 22px;margin-bottom:14px;">
      <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
        <div style="text-align:center;min-width:90px;">
          <div style="font-size:3.5rem;font-weight:900;color:{color};line-height:1;">{sc}</div>
          <div style="font-size:0.62rem;color:#8b90a0;">OUT OF 10</div>
        </div>
        <div style="flex:1;">
          <div style="font-size:0.95rem;font-weight:900;color:{color};margin-bottom:6px;">
            {emoji_level} {ri["level"]}
          </div>
          <div style="display:flex;gap:2px;margin-bottom:8px;">{segs}</div>
          <div style="font-size:0.8rem;color:#e8eaf0;margin-bottom:8px;">{ri["advice"]}</div>
          <div style="background:{color}22;border:1px solid {color}44;border-radius:8px;
                      padding:5px 12px;display:inline-block;">
            <span style="font-size:0.68rem;font-weight:800;color:{color};">
              📊 SIGNAL: {ri["stock_signal"]}
            </span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if ri["keyword_hits"]:
        kw_html = ""
        for kw, cnt in sorted(ri["keyword_hits"].items(), key=lambda x: -x[1])[:8]:
            kw_html += (f'<span style="background:{color}22;color:{color};'
                        f'border:1px solid {color}44;border-radius:20px;'
                        f'padding:2px 9px;font-size:0.66rem;font-weight:700;margin:2px;">{kw} ×{cnt}</span>')
        st.markdown(f"""
        <div style="margin-bottom:12px;">
          <div style="font-size:0.63rem;color:#8b90a0;font-weight:700;
                      letter-spacing:0.1em;margin-bottom:5px;">🔍 DETECTED KEYWORDS</div>
          <div style="display:flex;flex-wrap:wrap;gap:3px;">{kw_html}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f'''<div style="font-size:0.66rem;font-weight:800;color:#8b90a0;
                letter-spacing:0.1em;margin:12px 0 8px;">
      📰 LIVE NEWS ({ri["total_articles"]} articles scanned)</div>''', unsafe_allow_html=True)

    if ri["news"]:
        for n in ri["news"][:12]:
            ns = n["item_score"]
            nc = color if ns >= 1.5 else ("#f59e0b" if ns > 0 else "#8b90a0")
            badge = (f'<span style="background:{nc}22;color:{nc};border-radius:4px;'
                     f'padding:1px 7px;font-size:0.63rem;font-weight:700;">Score +{ns}</span>') if ns > 0 else ""
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid {"#27ae6033" if ns>=1.5 else "#2a2d3a"};
                        border-radius:10px;padding:10px 14px;margin-bottom:5px;border-left:3px solid {nc};">
              <div style="font-size:0.83rem;font-weight:600;color:#e8eaf0;line-height:1.5;margin-bottom:5px;">
                {n["title"]}
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <div style="display:flex;gap:6px;align-items:center;">
                  {badge}
                  <span style="background:#1a1f30;color:#8b90a0;border-radius:4px;
                               padding:1px 7px;font-size:0.62rem;">{n["source"]}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                  <span style="font-size:0.62rem;color:#5b6380;">🕐 {n["time"]}</span>
                  <a href="{n["link"]}" target="_blank"
                     style="color:#3b82f6;font-size:0.68rem;font-weight:600;text-decoration:none;">Padho →</a>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('''<div style="text-align:center;padding:30px;color:#8b90a0;">
          <div style="font-size:2rem;">📡</div>
          <div style="margin-top:8px;">News load nahi hui — Refresh karo</div>
        </div>''', unsafe_allow_html=True)

    st.markdown('''<div style="text-align:center;margin-top:10px;font-size:0.63rem;color:#2e3347;">
      ⚠️ AI-generated analysis — investment advice nahi. 15 min auto-refresh.
    </div>''', unsafe_allow_html=True)


@st.cache_data(ttl=1800)
def fetch_defence_orders(max_items: int = 30) -> list:
    """Fetch defence order/contract news for Indian defence stocks."""
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    import pytz, re

    IST_TZ = pytz.timezone("Asia/Kolkata")

    # Defence-specific search queries — order/contract related
    queries = [
        "HAL Hindustan Aeronautics order contract defence ministry",
        "Mazagon Dock MAZDOCK warship submarine order contract",
        "GRSE Garden Reach shipbuilder order contract navy",
        "Cochin Shipyard order contract navy defence",
        "Data Patterns DATAPATTNS order contract defence",
        "Zen Technologies ZENTEC order army defence",
        "Paras Defence order contract ministry",
        "Unimech Aerospace order contract defence",
        "BEL Bharat Electronics order contract defence",
        "India defence ministry order contract PSU 2025",
    ]

    # Keywords that indicate a real order/contract (not just general news)
    ORDER_KEYWORDS = [
        "order", "contract", "deal", "supply", "tender", "awarded",
        "procure", "purchase", "delivery", "signed", "worth", "crore",
        "ministry of defence", "mod ", "navy", "army", "air force",
        "iaf", "drdo", "bsf", "coast guard", "paramilitary",
    ]

    # Stock name → ticker mapping for tagging
    STOCK_MAP = {
        "hal": "HAL", "hindustan aeronautics": "HAL",
        "mazagon": "MAZDOCK", "mazdock": "MAZDOCK",
        "grse": "GRSE", "garden reach": "GRSE",
        "cochin shipyard": "COCHINSHIP", "cochinship": "COCHINSHIP",
        "data patterns": "DATAPATTNS", "datapattns": "DATAPATTNS",
        "zen tech": "ZENTEC", "zentec": "ZENTEC", "zen technologies": "ZENTEC",
        "paras defence": "PARAS", "paras": "PARAS",
        "unimech": "UNIMECH",
        "ideaforge": "IDEAFORGE",
        "krishna defence": "KRISHNADEF",
        "bel": "BEL", "bharat electronics": "BEL",
        "kpit": "KPITTECH",
    }

    # Size keywords for badge
    BIG_ORDER_KEYWORDS = ["crore", "cr ", "billion", "lakh crore", "₹"]

    seen = set()
    results = []

    for query in queries:
        if len(results) >= max_items:
            break
        try:
            q   = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            with urllib.request.urlopen(req, timeout=12) as r:
                xml_data = r.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item"):
                if len(results) >= max_items:
                    break
                title   = item.findtext("title",   "").strip()
                link    = item.findtext("link",    "").strip()
                pubdate = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None and source_el.text else "News"

                if not title or not link:
                    continue

                title_key = title[:70].lower()
                if title_key in seen:
                    continue

                title_lower = title.lower()

                # Must contain at least 1 order keyword
                if not any(kw in title_lower for kw in ORDER_KEYWORDS):
                    continue

                seen.add(title_key)

                # Clean title
                for sfx in [" - Moneycontrol", " | Moneycontrol", " - Economic Times",
                            " - Business Standard", " - Mint", " - NDTV Profit"]:
                    if title.endswith(sfx):
                        title = title[:-len(sfx)].strip()

                # IST time
                try:
                    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
                    dt = dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
                    ts = dt.strftime("%d %b %Y, %I:%M %p")
                    date_obj = dt.date()
                except Exception:
                    ts = pubdate[:16] if pubdate else "—"
                    date_obj = None

                # Tag which stock
                tagged_stocks = []
                for keyword, ticker in STOCK_MAP.items():
                    if keyword in title_lower and ticker not in tagged_stocks:
                        tagged_stocks.append(ticker)

                # Is it a big order?
                is_big = any(kw in title_lower for kw in BIG_ORDER_KEYWORDS)

                # Extract order value if mentioned (e.g. "₹500 crore")
                val_match = re.search(
                    r'[₹rs\.]*\s*(\d[\d,]*\.?\d*)\s*(crore|lakh crore|billion|cr)',
                    title_lower
                )
                order_val = None
                if val_match:
                    try:
                        num = float(val_match.group(1).replace(",", ""))
                        unit = val_match.group(2)
                        if "lakh crore" in unit:
                            order_val = f"₹{num:.0f} Lakh Cr"
                        elif "crore" in unit or "cr" in unit:
                            order_val = f"₹{num:,.0f} Cr"
                        elif "billion" in unit:
                            order_val = f"₹{num:.1f}B"
                    except Exception:
                        order_val = None

                results.append({
                    "title":    title,
                    "link":     link,
                    "time":     ts,
                    "source":   source,
                    "stocks":   tagged_stocks,
                    "is_big":   is_big,
                    "order_val": order_val,
                    "date_obj": str(date_obj) if date_obj else None,
                })
        except Exception:
            continue

    # Sort: big orders first, then by recency
    results.sort(key=lambda x: (not x["is_big"], x.get("date_obj") or ""), reverse=False)
    # Reverse date so newest first, big orders still on top
    big    = [r for r in results if r["is_big"]]
    normal = [r for r in results if not r["is_big"]]
    return big + normal

@st.cache_data(ttl=600)
def fetch_mc_market_news(max_items: int = 20) -> list:
    """Fetch top Indian market news from Moneycontrol via Google News RSS."""
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    import pytz
    IST_TZ = pytz.timezone("Asia/Kolkata")
    queries = [
        "site:moneycontrol.com stock market NSE BSE",
        "site:moneycontrol.com Nifty Sensex India",
        "site:moneycontrol.com equity shares IPO",
    ]
    seen_titles = set()
    all_items = []
    for query in queries:
        if len(all_items) >= max_items:
            break
        try:
            q   = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=12) as r:
                xml_data = r.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                if len(all_items) >= max_items:
                    break
                title   = item.findtext("title", "").strip()
                link    = item.findtext("link",  "").strip()
                pubdate = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None and source_el.text else "Moneycontrol"
                title_key = title[:60].lower()
                if not title or not link or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                try:
                    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
                    dt = dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
                    ts = dt.strftime("%d %b, %I:%M %p")
                except Exception:
                    ts = pubdate[:16] if pubdate else "—"
                for suffix in [" - Moneycontrol", " - Money Control", " | Moneycontrol"]:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)].strip()
                all_items.append({"title": title, "link": link, "time": ts, "source": source})
        except Exception:
            continue
    return all_items

@st.cache_data(ttl=600)
def fetch_stock_news(ticker_name: str, max_items: int = 8) -> list:
    """Kisi bhi stock ke liye latest news."""
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    try:
        q   = urllib.parse.quote(f"{ticker_name} NSE stock India")
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
        root  = ET.fromstring(xml_data)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title  = item.findtext("title","").strip()
            link   = item.findtext("link","").strip()
            pub    = item.findtext("pubDate","").strip()
            src    = item.find("source")
            source = src.text.strip() if src is not None and src.text else "News"
            try:
                from datetime import timezone
                dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
                dt = dt.replace(tzinfo=timezone.utc).astimezone(IST)
                ts = dt.strftime("%d %b, %I:%M %p")
            except Exception:
                ts = pub[:16]
            for sfx in [" - Moneycontrol"," - Economic Times"," - Business Standard"," | ET Markets"]:
                title = title.replace(sfx,"")
            if title and link:
                items.append({"title": title.strip(), "link": link, "time": ts, "source": source})
        return items
    except Exception:
        return []

def analyse_sentiment(title: str) -> tuple:
    """Keyword-based sentiment — returns (label, color, score)."""
    t = title.lower()
    pos = sum(1 for w in ["surge","rally","jump","gain","rise","up","bull","high","record",
                           "beat","profit","growth","strong","positive","recover","breakout",
                           "upar","tezi","badha","uchha","fayda","tarakki"] if w in t)
    neg = sum(1 for w in ["fall","drop","crash","loss","down","bear","low","weak","decline",
                           "miss","sell","negative","fear","slump","concern","risk","warning",
                           "niche","girna","nuksan","mandi","kamzor","giravat"] if w in t)
    if pos > neg:   return ("Positive", "#27ae60", pos - neg)
    elif neg > pos: return ("Negative", "#e74c3c", neg - pos)
    else:           return ("Neutral",  "#8b90a0", 0)

# ── Cache pre-warming background worker ──
def pre_warm_cache_bg():
    import threading
    import time
    
    def worker():
        try:
            # Let the page load first
            time.sleep(2.0)
            
            # Pre-warm indices
            tickers_indices = ("^NSEI", "^NSEBANK", "^BSESN")
            get_indices_batch(tickers_indices)
            
            # Pre-warm breadths (NIFTY_BREADTH_POOL)
            get_market_breadth()
            
            # Pre-warm top movers
            get_nse_top_movers()
            
            # Pre-warm watchlist sector quotes
            for sector in ["Defence", "IT", "Banking"]:
                if sector in SECTOR_WATCHLISTS:
                    tkrs = tuple(t for t, n in SECTOR_WATCHLISTS[sector])
                    get_batch_quotes(tkrs)
        except Exception:
            pass

    if "cache_pre_warmed" not in st.session_state:
        st.session_state.cache_pre_warmed = True
        t = threading.Thread(target=worker, daemon=True)
        t.start()

pre_warm_cache_bg()

# Dynamic styling is now handled by the primary style block using CSS variables.

# ── WATCHLIST — dynamic (custom_watchlist se) ─────────────────────────────────
WATCHLIST = st.session_state.custom_watchlist

INDICES = [
    {"name": "NIFTY 50",   "ticker": "^NSEI"},
    {"name": "BANK NIFTY", "ticker": "^NSEBANK"},
    {"name": "SENSEX",     "ticker": "^BSESN"},
]

# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR — Nifty 50 + Bank Nifty + status
# ══════════════════════════════════════════════════════════════════════════════
now_ist  = ist_now()
time_str = now_ist.strftime("%I:%M %p")
mkt_open = is_market_open()

# ── ⏰ Market Countdown — market band/khulne ka exact time bachta hai ──────────
def _market_countdown():
    now = now_ist
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)

    if mkt_open:
        # Market chal raha hai — band hone mein kitna time bacha hai
        delta = market_close - now
        total_min = int(delta.total_seconds() // 60)
        h, m = divmod(max(total_min, 0), 60)
        if total_min <= 15:
            # Last 15 minute — extra alert wala look
            return f"⚠️ {h}h {m}m mein BAND hoga", "#f97316", True
        return f"🔔 {h}h {m}m mein band hoga", "#94a3b8", False
    else:
        # Market band hai — agla open kab hai (weekend/holiday bhi skip karo)
        next_day = now

        # Saturday/Sunday/holiday skip karke agla trading din dhundo
        from datetime import date as _d
        MARKET_HOLIDAYS = {
            _d(2025,8,15),_d(2025,10,2),_d(2025,10,24),_d(2025,11,5),_d(2025,11,15),_d(2025,12,25),
            _d(2026,1,26),_d(2026,3,3),_d(2026,3,26),_d(2026,3,31),_d(2026,4,3),_d(2026,4,14),
            _d(2026,5,1),_d(2026,5,28),_d(2026,6,26),_d(2026,9,14),_d(2026,10,2),_d(2026,10,20),
            _d(2026,11,10),_d(2026,11,24),_d(2026,12,25),
        }

        # Agar aaj abhi tak market khula hi nahi (9:15 se pehle) aur aaj trading din hai,
        # to "aaj" hi next open hai — warna kal (ya agla trading din) dhundo
        if now.time() < market_open.time() and now.weekday() < 5 and now.date() not in MARKET_HOLIDAYS:
            next_open = market_open
        else:
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5 or next_day.date() in MARKET_HOLIDAYS:
                next_day = next_day + timedelta(days=1)
            next_open = next_day.replace(hour=9, minute=15, second=0, microsecond=0)

        delta = next_open - now
        total_min = int(delta.total_seconds() // 60)
        h, m = divmod(max(total_min, 0), 60)
        day_label = "" if next_open.date() == now.date() else (
            "kal " if next_open.date() == (now.date() + timedelta(days=1)) else next_open.strftime("%d %b ")
        )
        if h >= 24:
            d, h = divmod(h, 24)
            return f"💤 {d}d {h}h mein khulega ({day_label.strip()})", "#64748b", False
        return f"💤 {day_label}{h}h {m}m mein khulega", "#64748b", False

_countdown_txt, _countdown_color, _countdown_urgent = _market_countdown()
_countdown_cls = "countdown-urgent" if _countdown_urgent else ""

# Fetch top 3 indices for topbar — ek hi network call mein (fast)
_idx_batch = get_indices_batch(("^NSEI", "^NSEBANK", "^BSESN"))
n50   = _idx_batch["^NSEI"]
bnk   = _idx_batch["^NSEBANK"]
snsx  = _idx_batch["^BSESN"]

def chip_html(label, q):
    if q:
        cur, _, chg, pct = q
        chg_cls = "ic-chg-g" if chg >= 0 else "ic-chg-r"
        arrow   = "▲" if chg >= 0 else "▼"
        return f"""<div class="index-chip">
            <span class="ic-name">{label}</span>
            <span class="ic-val">{cur:,.2f}</span>
            <span class="{chg_cls}">{arrow} {abs(chg):,.2f} ({pct:+.2f}%)</span>
        </div>"""
    return f"""<div class="index-chip">
        <span class="ic-name">{label}</span>
        <span class="ic-val">—</span>
    </div>"""

pre_open = is_pre_open()

status_dot  = (f'<span class="live-dot"></span>' if mkt_open
               else f'<span class="preopen-dot"></span>' if pre_open
               else f'<span class="closed-dot"></span>')
status_txt  = (f"LIVE · {time_str}" if mkt_open
               else f"PRE-OPEN · {time_str}" if pre_open
               else f"CLOSED · {time_str}")

# ── Live Scrolling Ticker — news channel jaisa, page ke bilkul upar ───────────
def ticker_item_html(label, q):
    if q:
        cur, _, chg, pct = q
        cls    = "ti-up" if chg >= 0 else "ti-down"
        arrow  = "▲" if chg >= 0 else "▼"
        return (f'<span class="ticker-item">'
                f'<span class="ti-name">{label}</span>'
                f'<span class="ti-val">{cur:,.2f}</span>'
                f'<span class="{cls}">{arrow} {abs(chg):,.2f} ({pct:+.2f}%)</span>'
                f'</span>')
    return (f'<span class="ticker-item">'
            f'<span class="ti-name">{label}</span>'
            f'<span class="ti-val">—</span>'
            f'</span>')

_ticker_items = (
    ticker_item_html("NIFTY 50", n50)
    + ticker_item_html("SENSEX", snsx)
    + ticker_item_html("BANK NIFTY", bnk)
)
# Content ko 2x duplicate karte hain taaki scroll loop seamless lage (gap na dikhe)
_ticker_track = _ticker_items + _ticker_items

st.markdown(f"""
<div class="ticker-wrap">
  <div class="ticker-track">{_ticker_track}</div>
</div>
""", unsafe_allow_html=True)

tab = st.session_state.active_tab
# Only process target orders during market hours — no price changes when market closed
if is_market_open():
    process_target_orders()

# ── Left Sidebar navigation ──
with st.sidebar:
    st.markdown('<div class="sidebar-logo">💎 FintechHub</div>', unsafe_allow_html=True)
    
    menu_items = [
        ("📊 Dashboard",   "home"),
        ("⭐ Watchlist",   "watchlist"),
        ("💼 Portfolio",   "portfolio"),
        ("📋 Orders",      "orders"),
        ("💰 Balance",     "balance"),
        ("📈 Market",      "market"),
        ("📰 News",        "news"),
        ("📅 Calendar",    "calendar"),
        ("🔍 Screener",    "screener"),
        ("🏭 Sectors",     "sectors"),
        ("⚙️ Settings",     "settings"),
    ]
    
    for label, tab_key in menu_items:
        _sector_tabs = {"defence", "broking", "renewable", "ev_tech", "banking"}
        is_active = (tab == tab_key) or (tab_key == "sectors" and tab in _sector_tabs)
        
        if st.button(label, key=f"side_nav_{tab_key}", width='stretch',
                     type="primary" if is_active else "secondary"):
            if tab_key == "sectors":
                st.session_state.active_tab = st.session_state.get("last_sector_tab", "defence")
            else:
                st.session_state.active_tab = tab_key
            st.rerun()
            
    # Sidebar footer profile & theme toggle
    st.markdown('<div style="flex-grow: 1; height: 50px;"></div>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color: var(--border-color); margin: 12px 0;">', unsafe_allow_html=True)
    
    fcol1, fcol2 = st.columns([3, 1])
    with fcol1:
        st.markdown('<div style="font-weight:600;font-size:0.85rem;color:var(--text-color);line-height:1.2;">Nitin Rajgor</div>'
                    '<div style="font-size:0.69rem;color:var(--secondary-text);">nitin@fintech.com</div>', unsafe_allow_html=True)
    with fcol2:
        pass  # Theme toggle removed — dashboard is fixed to Light Theme

# ── Dynamic Header Title & Breadcrumbs Resolver ──
tab_labels = {
    "home": "Dashboard", "watchlist": "Watchlist", "portfolio": "Portfolio",
    "orders": "Orders", "balance": "Balance", "market": "Market", "breadth": "Breadth",
    "news": "News", "calendar": "Calendar",
    "screener": "Screener", "defence": "Sectors", "broking": "Sectors",
    "renewable": "Sectors", "ev_tech": "Sectors", "banking": "Sectors", "settings": "Settings"
}
current_title = tab_labels.get(tab, "Dashboard")

# Inject fixed top header layout
st.markdown(f"""
<div class="top-nav-bar">
    <div class="nav-left">
        <span class="logo">💎 FintechHub</span>
        <span class="divider">/</span>
        <span class="page-title">{current_title}</span>
    </div>
    <div class="nav-center">
        <div class="search-box">
            <span class="search-icon">🔍</span>
            <input type="text" placeholder="Search stocks, news, indicators..." disabled>
        </div>
    </div>
    <div class="nav-right">
        <div class="market-badge">
            {status_dot}
            <span class="status-text">{status_txt}</span>
        </div>
        <span class="nav-icon">🔔</span>
        <div class="profile-container" style="position: relative; display: inline-block;">
            <div class="profile-avatar" onclick="event.stopPropagation(); window._ftcToggleProfileMenu();">NR</div>
            <div class="profile-dropdown" id="ftc-profile-dropdown">
                <div class="pd-header">
                    <div class="pd-name">Nitin Rajgor</div>
                    <div class="pd-email">nitin@fintech.com</div>
                    <div class="pd-tier-badge">⭐ Enterprise Pro</div>
                </div>
                <div class="pd-divider"></div>
                <div class="pd-item" onclick="window._ftcNav('&#9881;&#65039; Settings'); window._ftcCloseProfileMenu(); setTimeout(function(){{ var btns=document.querySelectorAll('[data-testid=stSidebar] button'); for(var b of btns){{ if(b.innerText.includes('Settings')){{ b.click(); break; }} }} }}, 300);">&#128100; My Profile</div>
                <div class="pd-item" onclick="window._ftcNav('&#9881;&#65039; Settings'); window._ftcCloseProfileMenu();">&#9881;&#65039; Settings</div>
                <div class="pd-item" onclick="window._ftcNav('&#9881;&#65039; Settings'); window._ftcCloseProfileMenu(); setTimeout(function(){{ var el=document.querySelector('button[id*=stab_notifications]'); if(el) el.click(); }}, 300);">&#128276; Notifications</div>
                <div class="pd-item" onclick="window._ftcNav('&#9881;&#65039; Settings'); window._ftcCloseProfileMenu(); setTimeout(function(){{ var el=document.querySelector('button[id*=stab_help]'); if(el) el.click(); }}, 300);">&#10067; Help</div>
                <div class="pd-divider"></div>
                <div class="pd-item pd-item-danger" onclick="window._ftcCloseProfileMenu(); document.querySelector('[data-testid=stSidebar]') && (window.location.href=window.location.origin);">&#x1F6AA; Logout</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Inject dynamic breadcrumbs
st.markdown(f"""
<div class="breadcrumbs">
    <span class="bc-root">Dashboard</span>
    <span class="bc-sep">/</span>
    <span class="bc-active">{current_title if tab != "home" else "Overview"}</span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helper — Watchlist 2/3 ke stocks ke liye lightweight sector dashboard
# ══════════════════════════════════════════════════════════════════════════════
def render_watch_sector(icon, title, tagline, stocks, refresh_key, sector_key=None):
    """stocks = list of (ticker, display_name, about_text). Live price/% se banta hai,
    6 sub-tabs ke saath — Defence tab jaisa full structure."""
    _CARD = CARD_BG; _BORD = BORDER; _TXT = TEXT; _MUT = MUTED
    _GRN  = GREEN; _RED  = RED
    sector_key = sector_key or refresh_key.replace("_refresh", "")

    sh, sr = st.columns([5, 1])
    with sh:
        st.markdown(f'<div class="sec-title">{title.upper()}</div>', unsafe_allow_html=True)
    with sr:
        if st.button("🔄", key=refresh_key, help="Prices refresh karo"):
            get_index_quote.clear(); get_batch_quotes.clear()
            fetch_sector_index.clear()
            st.rerun()

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f1a2a,#1a1200);
                border:1px solid #3b82f655;border-radius:16px;padding:16px 20px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2rem;">{icon}</div>
        <div>
          <div style="font-size:1.05rem;font-weight:900;color:#f0f3ff;">{title}</div>
          <div style="font-size:0.76rem;color:#8b90a0;margin-top:3px;">{tagline}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Pre-fetch all quotes once ─────────────────────────────────────────────
    quotes = {}
    for tkr, name, about in stocks:
        quotes[tkr] = get_index_quote(tkr)

    # ── 4 SUB-TABS — Defence tab jaisa structure ────────────────────────────────
    trend_tab, info_tab, impact_tab, ready_tab = st.tabs([
        "📈 Budget Trend", "🏭 Company Orders", "📊 Stock Impact", "🚨 Readiness Index"
    ])

    # ══ SUB-TAB 2 — COMPANY ORDERS (Company Info) ══════════════════════════════
    with info_tab:
        for tkr, name, about in stocks:
            slot = st.empty()
            info_html = (
                f'<div style="background:{_CARD};border:1px solid {_BORD};border-radius:10px;'
                f'padding:12px 16px;margin-bottom:8px;border-left:3px solid #3b82f6;">'
                f'<span style="font-size:0.92rem;font-weight:700;color:{_TXT};">{name}</span>'
                f'<span style="font-size:0.7rem;color:{_MUT};margin-left:6px;">{tkr.replace(".NS","")}</span>'
                f'<div style="font-size:0.78rem;color:{_MUT};margin-top:6px;">💡 {about}</div>'
                f'</div>'
            )
            slot.markdown(info_html, unsafe_allow_html=True)

    # ══ SUB-TAB 1 — BUDGET TREND (price trend line, improved visuals) ══════════
    with trend_tab:
        import plotly.graph_objects as go
        fig2 = go.Figure()
        colors_cycle = ["#3b82f6", "#f59e0b", "#27ae60", "#a78bfa", "#e74c3c",
                        "#06b6d4", "#84cc16", "#f43f5e", "#fb923c", "#22d3ee"]
        any_plotted = False
        debug_errors = []
        for ci, (tkr, name, about) in enumerate(stocks):
            try:
                hist, err = get_trend_history(tkr, "1mo")
                if err:
                    debug_errors.append(err)
                if hist is not None and not hist.empty and len(hist) >= 2:
                    base = hist["Close"].iloc[0]
                    pct_series = ((hist["Close"] - base) / base * 100)
                    line_color = colors_cycle[ci % len(colors_cycle)]
                    fig2.add_trace(go.Scatter(
                        x=hist.index, y=pct_series, mode="lines",
                        name=name, line=dict(color=line_color, width=3.2, shape="spline", smoothing=0.55),
                        fill="tozeroy", fillcolor=line_color + "1f",
                        hovertemplate=f"<b>{name}</b><br>%{{x|%d %b}}<br>%{{y:+.2f}}%<extra></extra>",
                    ))
                    any_plotted = True
                    # Last point marker + end label (best-effort, never blocks main line)
                    try:
                        last_x, last_y = hist.index[-1], pct_series.iloc[-1]
                        if pd.notna(last_y):
                            fig2.add_trace(go.Scatter(
                                x=[last_x], y=[last_y], mode="markers+text",
                                marker=dict(size=9, color=line_color, line=dict(color="#0f1116", width=2)),
                                text=[f"  {last_y:+.1f}%"], textposition="middle right",
                                textfont=dict(size=10.5, color=line_color, family="Inter, sans-serif"),
                                showlegend=False, hoverinfo="skip",
                            ))
                    except Exception:
                        pass
            except Exception:
                continue
        if any_plotted:
            fig2.add_hline(y=0, line_width=1, line_dash="dot", line_color="#3a3f52")
            fig2.update_layout(
                paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                font=dict(color=_TXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"), height=380,
                margin=dict(l=40, r=60, t=44, b=40),
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.2, font=dict(size=9.5), bgcolor="rgba(0,0,0,0)"),
                title=dict(text="📈 Last 1 mahine ka % trend — sabhi stocks", font=dict(size=13.5, color=_TXT), x=0),
                xaxis=dict(gridcolor=CHART_GRID, showgrid=True, zeroline=False, tickfont=dict(size=10),
                           showline=True, linecolor=CHART_LINE),
                yaxis=dict(gridcolor=CHART_GRID, ticksuffix="%", zeroline=False, tickfont=dict(size=10),
                           showline=False),
                hoverlabel=dict(bgcolor=CARD_BG, bordercolor=BORDER, font=dict(color=_TXT, size=11)),
            )
            st.plotly_chart(fig2, width='stretch', key=f"trend_{refresh_key}",
                             config={"displayModeBar": False})
        else:
            st.info("Trend data load nahi hua — Yahoo Finance se data nahi mil paya. 🔄 Refresh button try karo ya thodi der baad dekho.")
            if debug_errors:
                with st.expander("🔍 Technical reason (debug)"):
                    for e in debug_errors:
                        st.code(e, language=None)

    # ══ SUB-TAB 3 — STOCK IMPACT (relative strength table) ═════════════════════
    with impact_tab:
        st.markdown(f'''<div style="font-size:0.68rem;font-weight:800;color:{_MUT};
                    letter-spacing:0.1em;margin-bottom:10px;">📊 RELATIVE STRENGTH — SECTOR KE ANDAR</div>''',
                    unsafe_allow_html=True)
        impact_rows = []
        for tkr, name, about in stocks:
            q = quotes.get(tkr)
            if q:
                impact_rows.append((name, tkr, q[3]))
        impact_rows.sort(key=lambda x: -x[2])
        if impact_rows:
            max_abs = max(abs(r[2]) for r in impact_rows) or 1
            for name, tkr, pct in impact_rows:
                bar_w = min(100, abs(pct) / max_abs * 100)
                bc = _GRN if pct >= 0 else _RED
                strength = "Strong" if abs(pct) >= 2 else ("Moderate" if abs(pct) >= 0.8 else "Weak")
                st.markdown(f"""
                <div style="background:{_CARD};border:1px solid {_BORD};border-radius:10px;
                            padding:11px 14px;margin-bottom:6px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                    <span style="font-size:0.88rem;font-weight:700;color:{_TXT};">{name}</span>
                    <span style="font-size:0.88rem;font-weight:800;color:{bc};">{pct:+.2f}%</span>
                  </div>
                  <div style="background:#13161f;border-radius:3px;height:5px;margin-bottom:4px;">
                    <div style="background:{bc};width:{bar_w}%;height:5px;border-radius:3px;"></div>
                  </div>
                  <div style="font-size:0.65rem;color:{_MUT};">{strength} move today</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Impact data load nahi hua.")

    # ══ SUB-TAB 4 — READINESS / OPPORTUNITY INDEX ═══════════════════════════════
    with ready_tab:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0a0f1a,#0f1a0a);
                    border:1px solid #ffffff22;border-radius:14px;
                    padding:14px 18px;margin-bottom:14px;">
          <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-size:1.8rem;">{icon}</div>
            <div>
              <div style="font-size:0.95rem;font-weight:900;color:#f0f3ff;">{title} Opportunity Index</div>
              <div style="font-size:0.75rem;color:#8b90a0;margin-top:2px;">
                {", ".join([n for _,n,_ in stocks[:4]])} ke liye live news se calculate
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
        sector_key_resolved = sector_key
        render_sector_index(sector_key_resolved, refresh_key)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — HOME (overview — 5 second mein "aaj kya situation hai" pata chale)
# ══════════════════════════════════════════════════════════════════════════════
if tab == "home":
    # Styling classes for premium cards and elements
    st.markdown("""
    <style>
    .premium-card {
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }
    .premium-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 32px rgba(15,23,42,0.08) !important;
        border-color: var(--primary-blue) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── 1. Calculate Portfolio P&L Summary & Rows ────────────────────────────────
    total_invested = 0.0
    total_current  = 0.0
    day_pnl_home   = 0.0
    prev_total_val_home = 0.0
    movers = []  # (ticker, pct, pnl_value)
    rows = []
    today_date = ist_now().date()

    _now_home = ist_now()
    _market_open_time = _now_home.replace(hour=9, minute=15, second=0, microsecond=0)
    _pre_market = _now_home < _market_open_time

    _holdings_tuple_home = tuple(
        (tkr, h["shares"], h["avg_price"]) for tkr, h in st.session_state.pt_holdings.items()
    )
    _live_prices_home = get_holdings_live_prices(_holdings_tuple_home)

    for tkr, h in st.session_state.pt_holdings.items():
        invested = h["shares"] * h["avg_price"]
        total_invested += invested
        try:
            _live = _live_prices_home.get(tkr, {})
            prev_c = _live.get("prev_close")
            cur_price = _live.get("live_price") or prev_c or h["avg_price"]
            cur_val = h["shares"] * cur_price
            total_current += cur_val

            if _pre_market:
                day_pct_row = 0.0
                day_pnl_row = 0.0
            else:
                day_pct_row = ((cur_price - prev_c) / prev_c * 100) if prev_c else 0.0
                day_pnl_row = (cur_price - prev_c) * h["shares"] if prev_c else 0.0

            day_pnl_home += day_pnl_row
            prev_total_val_home += (prev_c or cur_price) * h["shares"]
            movers.append((tkr, day_pct_row, cur_val - invested))
            
            # Populate rows list for get_aaj_ka_trade_insight compatibility
            fb_date_str = h.get("first_buy_date")
            if fb_date_str:
                try:
                    fb_date = datetime.strptime(fb_date_str, "%Y-%m-%d").date()
                    held_days = (today_date - fb_date).days
                    term_label = "Long Term" if held_days > 365 else "Short Term"
                except Exception:
                    held_days, term_label = None, None
            else:
                held_days, term_label = None, None
                
            name_disp = dict(st.session_state.custom_watchlist).get(tkr, tkr.replace(".NS",""))
            rows.append({
                "ticker": tkr,
                "name": name_disp,
                "shares": h["shares"],
                "avg": h["avg_price"],
                "cur": cur_price,
                "inv": invested,
                "cur_v": cur_val,
                "pnl": cur_val - invested,
                "pnl_p": ((cur_val - invested) / invested * 100) if invested > 0 else 0.0,
                "held_days": held_days,
                "term_label": term_label
            })
        except Exception:
            total_current += invested

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
    day_pnl_pct_home = (day_pnl_home / prev_total_val_home * 100) if prev_total_val_home else 0.0

    # Auto refresh home page only during market hours (no benefit when market closed)
    _home_elapsed = time.time() - st.session_state.get("_ar_home", 0)
    if _home_elapsed >= _AUTO_REFRESH_SECS and is_market_open():
        st.session_state["_ar_home"] = time.time()
        st.rerun()

    # ── 2. Welcome Header Section ──────────────────────────────────────────────
    date_str = now_ist.strftime("%A, %d %B %Y")
    
    # Calculate overall sentiment from moneycontrol news (cached 10 min — shared with AI Insights)
    _home_page_news = []
    overall_sentiment_label = "Neutral"
    overall_sentiment_color = MUTED
    try:
        _home_page_news = fetch_mc_market_news(max_items=15)
        if _home_page_news:
            sentiments = [analyse_sentiment(n["title"]) for n in _home_page_news]
            pos_count  = sum(1 for s in sentiments if s[0] == "Positive")
            neg_count  = sum(1 for s in sentiments if s[0] == "Negative")
            if pos_count > neg_count * 1.3:
                overall_sentiment_label = "Bullish"
                overall_sentiment_color = GREEN
            elif neg_count > pos_count * 1.3:
                overall_sentiment_label = "Bearish"
                overall_sentiment_color = RED
    except Exception:
        pass

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
                backdrop-filter: blur(10px);
                border: 1px solid {BORDER};
                border-radius: 16px;
                padding: 24px 30px;
                margin-bottom: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 16px;">
        <div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {TEXT}; letter-spacing: -0.02em;">
                Welcome back, Nitin Rajgor 👋
            </div>
            <div style="font-size: 0.88rem; color: {MUTED}; margin-top: 4px; font-weight: 500;">
                📅 {date_str} &nbsp;·&nbsp; Market Sentiment is <span style="color: {overall_sentiment_color}; font-weight: 700;">{overall_sentiment_label}</span>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background: {BG_COLOR}; border: 1px solid {BORDER}; border-radius: 20px; padding: 6px 14px; display: inline-flex; align-items: center; gap: 8px;">
                {status_dot}
                <span style="font-size: 0.78rem; font-weight: 700; color: {TEXT}; text-transform: uppercase; letter-spacing: 0.05em;">{status_txt}</span>
            </div>
            <div style="background: {_countdown_color}1a; border: 1px solid {_countdown_color}44; border-radius: 20px; padding: 6px 14px; color: {_countdown_color}; font-size: 0.78rem; font-weight: 700;">
                {_countdown_txt}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. Quick Statistics Row (KPI Cards) ────────────────────────────────────
    kcol1, kcol2, kcol3, kcol4 = st.columns(4)

    with kcol1:
        st.markdown(f"""
        <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; color: {MUTED}; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Portfolio Value</span>
                <span style="font-size: 1.2rem;">💼</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 800; color: {TEXT};">₹{total_current:,.0f}</div>
            <div style="font-size: 0.75rem; color: {MUTED}; margin-top: 6px;">₹{total_invested:,.0f} invested</div>
        </div>
        """, unsafe_allow_html=True)

    with kcol2:
        pnl_c = GREEN if day_pnl_home >= 0 else RED
        arrow = "▲" if day_pnl_home >= 0 else "▼"
        st.markdown(f"""
        <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; color: {MUTED}; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Today's P&L</span>
                <span style="font-size: 1.2rem;">💰</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 800; color: {pnl_c};">{arrow} ₹{abs(day_pnl_home):,.0f}</div>
            <div style="font-size: 0.75rem; color: {pnl_c}; margin-top: 6px; font-weight: 600;">{day_pnl_pct_home:+.2f}% today</div>
        </div>
        """, unsafe_allow_html=True)

    with kcol3:
        st.markdown(f"""
        <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; color: {MUTED}; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Total Holdings</span>
                <span style="font-size: 1.2rem;">📊</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 800; color: {TEXT};">{len(st.session_state.pt_holdings)} / {len(st.session_state.custom_watchlist)}</div>
            <div style="font-size: 0.75rem; color: {MUTED}; margin-top: 6px;">Holdings / Watchlist items</div>
        </div>
        """, unsafe_allow_html=True)

    with kcol4:
        n50_val = n50[0] if n50 else 0
        n50_chg = n50[3] if n50 else 0
        n50_c = GREEN if n50_chg >= 0 else RED
        n50_arrow = "▲" if n50_chg >= 0 else "▼"
        st.markdown(f"""
        <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; color: {MUTED}; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Nifty 50 Index</span>
                <span style="font-size: 1.2rem;">📈</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 800; color: {TEXT};">{n50_val:,.2f}</div>
            <div style="font-size: 0.75rem; color: {n50_c}; margin-top: 6px; font-weight: 600;">{n50_arrow} {n50_chg:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ── 4. Main Two-Column Layout ──────────────────────────────────────────────
    col_main, col_sidebar = st.columns([2, 1])

    with col_main:
        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 16px 0 10px; color: var(--text-color);">📈 MARKET TRENDS</div>', unsafe_allow_html=True)
        
        # centerpiece Index Chart in premium glass container
        chart_container = st.container(border=True)
        with chart_container:
            col_t1, col_t2 = st.columns([1.5, 1])
            with col_t1:
                sel_index = st.radio(
                    "Index Selector",
                    ["NIFTY 50", "BANK NIFTY", "SENSEX"],
                    index=0,
                    horizontal=True,
                    key="home_chart_index_radio",
                    label_visibility="collapsed"
                )
            with col_t2:
                sel_period = st.radio(
                    "Period Selector",
                    ["1mo", "3mo", "6mo", "1y"],
                    index=1,
                    horizontal=True,
                    key="home_chart_period_radio",
                    label_visibility="collapsed"
                )
            
            ticker_map = {
                "NIFTY 50": "^NSEI",
                "BANK NIFTY": "^NSEBANK",
                "SENSEX": "^BSESN"
            }
            tkr_to_fetch = ticker_map[sel_index]
            
            with st.spinner(f"{sel_index} chart load ho raha hai..."):
                index_chart = get_stock_chart(tkr_to_fetch, period=sel_period)
                
            if index_chart:
                index_chart.update_layout(height=400)
                st.plotly_chart(index_chart, width='stretch', key=f"home_index_chart_{sel_index}_{sel_period}")
            else:
                st.info("Chart data available nahi hai.")

        # Market Overview Indices Strip
        ind_c1, ind_c2, ind_c3 = st.columns(3)
        with ind_c1:
            n50_val, n50_chg = (n50[0], n50[3]) if n50 else (0, 0)
            n50_c = GREEN if n50_chg >= 0 else RED
            n50_arr = "▲" if n50_chg >= 0 else "▼"
            st.markdown(f"""
            <div style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8rem; font-weight: 700; color: {TEXT};">Nifty 50</span>
                <div style="text-align: right;">
                    <div style="font-size: 0.88rem; font-weight: 800; color: {TEXT};">{n50_val:,.2f}</div>
                    <div style="font-size: 0.7rem; color: {n50_c}; font-weight: 600;">{n50_arr} {n50_chg:+.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with ind_c2:
            bnk_val, bnk_chg = (bnk[0], bnk[3]) if bnk else (0, 0)
            bnk_c = GREEN if bnk_chg >= 0 else RED
            bnk_arr = "▲" if bnk_chg >= 0 else "▼"
            st.markdown(f"""
            <div style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8rem; font-weight: 700; color: {TEXT};">Bank Nifty</span>
                <div style="text-align: right;">
                    <div style="font-size: 0.88rem; font-weight: 800; color: {TEXT};">{bnk_val:,.2f}</div>
                    <div style="font-size: 0.7rem; color: {bnk_c}; font-weight: 600;">{bnk_arr} {bnk_chg:+.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with ind_c3:
            snsx_val, snsx_chg = (snsx[0], snsx[3]) if snsx else (0, 0)
            snsx_c = GREEN if snsx_chg >= 0 else RED
            snsx_arr = "▲" if snsx_chg >= 0 else "▼"
            st.markdown(f"""
            <div style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8rem; font-weight: 700; color: {TEXT};">Sensex</span>
                <div style="text-align: right;">
                    <div style="font-size: 0.88rem; font-weight: 800; color: {TEXT};">{snsx_val:,.2f}</div>
                    <div style="font-size: 0.7rem; color: {snsx_c}; font-weight: 600;">{snsx_arr} {snsx_chg:+.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 24px 0 12px; color: var(--text-color);">📊 MARKET BREADTH & MOVERS</div>', unsafe_allow_html=True)
        
        # Gainers & Losers Grid
        mov_col1, mov_col2 = st.columns(2)
        gainers, losers = get_nse_top_movers()
        gainers = gainers[:3]
        losers = losers[:3]
        
        with mov_col1:
            st.markdown('<div style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px; color: var(--text-color);">🔥 TOP GAINERS</div>', unsafe_allow_html=True)
            if gainers:
                for g in gainers:
                    st.markdown(f"""
                    <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.9rem; font-weight: 700; color: {TEXT};">{g['name']}</span>
                            <div style="font-size: 0.72rem; color: {MUTED}; margin-top: 2px;">₹{g['price']:,.2f}</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 0.9rem; font-weight: 700; color: {GREEN};">▲ {g['chg_pct']:+.2f}%</span>
                            <div style="font-size: 0.72rem; color: {GREEN}; margin-top: 2px;">+₹{g['chg']:,.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No gainers data available.")

        with mov_col2:
            st.markdown('<div style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px; color: var(--text-color);">❄️ TOP LOSERS</div>', unsafe_allow_html=True)
            if losers:
                for l in losers:
                    st.markdown(f"""
                    <div class="premium-card" style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.9rem; font-weight: 700; color: {TEXT};">{l['name']}</span>
                            <div style="font-size: 0.72rem; color: {MUTED}; margin-top: 2px;">₹{l['price']:,.2f}</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 0.9rem; font-weight: 700; color: {RED};">▼ {l['chg_pct']:+.2f}%</span>
                            <div style="font-size: 0.72rem; color: {RED}; margin-top: 2px;">-₹{abs(l['chg']):,.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No losers data available.")

        # Portfolio Snapshot
        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 24px 0 12px; color: var(--text-color);">💼 PORTFOLIO ALLOCATION</div>', unsafe_allow_html=True)
        if st.session_state.pt_holdings:
            port_container = st.container(border=True)
            with port_container:
                # Recreate/render the heatmap figure
                hm_labels = [dict(st.session_state.custom_watchlist).get(tkr, tkr.replace(".NS","")) for tkr in st.session_state.pt_holdings.keys()]
                hm_values = [max(h["shares"] * h["avg_price"], 1) for h in st.session_state.pt_holdings.values()]
                
                # Color values based on P&L %
                hm_pnl_pct = []
                for tkr, h in st.session_state.pt_holdings.items():
                    _live = _live_prices_home.get(tkr, {})
                    cur_price = _live.get("live_price") or h["avg_price"]
                    inv = h["shares"] * h["avg_price"]
                    cur_val = h["shares"] * cur_price
                    pnl_val = cur_val - inv
                    pnl_p = (pnl_val / inv * 100) if inv else 0
                    hm_pnl_pct.append(pnl_p)
                    
                hm_text = [
                    f"{name}<br>₹{inv:,.0f} invested<br>{pct:+.2f}%"
                    for name, inv, pct in zip(hm_labels, hm_values, hm_pnl_pct)
                ]
                hm_pnl_pct_str = [f"{pct:+.2f}%" for pct in hm_pnl_pct]
                
                heatmap_fig = go.Figure(go.Treemap(
                    labels=hm_labels,
                    parents=[""] * len(hm_labels),
                    values=hm_values,
                    text=hm_text,
                    texttemplate="<b>%{label}</b><br>%{customdata}",
                    customdata=hm_pnl_pct_str,
                    marker=dict(
                        colors=hm_pnl_pct,
                        colorscale=[
                            [0.0, "#7f1d1d"],
                            [0.4, "#e74c3c"],
                            [0.5, "#2a2d3a"],
                            [0.6, "#27ae60"],
                            [1.0, "#0d3320"],
                        ],
                        cmid=0,
                        line=dict(color=BG_COLOR, width=2),
                    ),
                    textfont=dict(color="#ffffff", size=11),
                    pathbar=dict(visible=False),
                ))
                heatmap_fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=4, r=4, t=4, b=4),
                    height=240,
                )
                st.plotly_chart(heatmap_fig, width='stretch', key="home_portfolio_heatmap")
                
                # Streak / Daily Insight
                streak_val, prof_days, total_days = calculate_streak(st.session_state.pt_history)
                insight_txt = get_aaj_ka_trade_insight(rows, st.session_state.pt_history, streak_val)
                
                st.markdown(f"""
                <div style="background: {BG_COLOR}; border: 1px solid {BORDER}; border-radius: 12px; padding: 14px 18px; margin-top: 12px;">
                    <div style="font-size: 0.72rem; color: {MUTED}; font-weight: 700; text-transform: uppercase;">🔥 PROFIT STREAK</div>
                    <div style="font-size: 1.05rem; font-weight: 800; color: {TEXT}; margin-top: 4px;">{streak_val} consecutive profitable trade days</div>
                    <div style="font-size: 0.76rem; color: {MUTED}; margin-top: 6px; font-style: italic;">💡 Insight: {insight_txt[1]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 30px; text-align: center; color: {MUTED}; font-size: 0.9rem;">
                💼 Abhi koi holdings nahi hain. Portfolio tab se shuru karo!
            </div>
            """, unsafe_allow_html=True)

    with col_sidebar:
        # AI Insights Card
        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 16px 0 10px; color: var(--text-color);">🤖 AI INSIGHTS</div>', unsafe_allow_html=True)
        ai_container = st.container(border=True)
        with ai_container:
            try:
                # Reuse already-fetched news from top of page (no second network call)
                news_items = _home_page_news or fetch_mc_market_news(max_items=15)
                if news_items:
                    sentiments = [analyse_sentiment(n["title"]) for n in news_items]
                    pos_count = sum(1 for s in sentiments if s[0] == "Positive")
                    neg_count = sum(1 for s in sentiments if s[0] == "Negative")
                    total = len(sentiments)
                    pos_pct = int(pos_count / total * 100) if total else 50
                    neg_pct = int(neg_count / total * 100) if total else 50
                    
                    if pos_count > neg_count * 1.3:
                        mood = "Bullish"
                        mood_color = GREEN
                    elif neg_count > pos_count * 1.3:
                        mood = "Bearish"
                        mood_color = RED
                    else:
                        mood = "Neutral"
                        mood_color = MUTED
                else:
                    mood = "Neutral"
                    mood_color = MUTED
                    pos_pct, neg_pct = 50, 50
            except Exception:
                mood = "Neutral"
                mood_color = MUTED
                pos_pct, neg_pct = 50, 50
                
            st.markdown(f"""
            <div style="background: {BG_COLOR}; border: 1px solid {BORDER}; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; text-align: center;">
                <div style="font-size: 0.65rem; color: {MUTED}; font-weight: 700; text-transform: uppercase;">AI Market Mood</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: {mood_color}; margin-top: 4px;">{mood}</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: {MUTED}; margin-top: 10px;">
                    <span>🟢 Positive {pos_pct}%</span>
                    <span>🔴 Negative {neg_pct}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="font-size: 0.8rem; color: {TEXT}; line-height: 1.4; font-weight: 500;">
                🤖 <b>Claude AI recommendation:</b> Indian equities are showing {mood.lower()} momentum. Growth sectors like renewable energy and defense continue to attract strong institutional inflows.
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


        # Watchlist Preview Card
        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 24px 0 10px; color: var(--text-color);">⭐ WATCHLIST PREVIEW</div>', unsafe_allow_html=True)
        wl_container = st.container(border=True)
        with wl_container:
            if st.session_state.custom_watchlist:
                preview_stocks = st.session_state.custom_watchlist[:4]
                tkrs = tuple(t for t, _ in preview_stocks)
                quotes = get_batch_quotes(tkrs)
                
                for tkr, name in preview_stocks:
                    q = quotes.get(tkr)
                    if q:
                        cur, prev, chg, pct = q
                        wc = GREEN if pct >= 0 else RED
                        arrow = "▲" if pct >= 0 else "▼"
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid {BORDER};">
                            <div>
                                <div style="font-size: 0.85rem; font-weight: 700; color: {TEXT};">{name}</div>
                                <div style="font-size: 0.68rem; color: {MUTED}; margin-top: 1px;">{tkr.replace('.NS','')}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.85rem; font-weight: 700; color: {TEXT};">₹{cur:,.2f}</div>
                                <div style="font-size: 0.68rem; color: {wc}; font-weight: 600; margin-top: 1px;">{arrow} {pct:+.2f}%</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid {BORDER};">
                            <div>
                                <div style="font-size: 0.85rem; font-weight: 700; color: {TEXT};">{name}</div>
                                <div style="font-size: 0.68rem; color: {MUTED}; margin-top: 1px;">{tkr.replace('.NS','')}</div>
                            </div>
                            <div style="font-size: 0.8rem; color: {MUTED};">Loading...</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size: 0.8rem; color: {MUTED}; text-align: center; padding: 10px 0;">Watchlist empty hai.</div>', unsafe_allow_html=True)
                
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("⭐ View All Watchlist", key="home_wl_btn", width='stretch'):
                st.session_state.active_tab = "watchlist"
                st.rerun()

        # News Preview Card
        st.markdown('<div style="font-size: 1.15rem; font-weight: 800; margin: 24px 0 10px; color: var(--text-color);">📰 MARKET NEWS</div>', unsafe_allow_html=True)
        news_container = st.container(border=True)
        with news_container:
            try:
                latest_news = fetch_mc_market_news(max_items=3)
                if latest_news:
                    for n in latest_news:
                        title = n["title"]
                        lbl, col, _ = analyse_sentiment(title)
                        st.markdown(f"""
                        <div style="padding: 10px 0; border-bottom: 1px solid {BORDER};">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span style="font-size: 0.62rem; background: {col}1a; color: {col}; border: 1px solid {col}44; border-radius: 4px; padding: 2px 6px; font-weight: 700;">{lbl}</span>
                                <span style="font-size: 0.68rem; color: {MUTED};">{n['time']}</span>
                            </div>
                            <a href="{n['link']}" target="_blank" style="text-decoration: none; font-size: 0.82rem; font-weight: 600; color: {TEXT}; line-height: 1.3; display: block;">
                                {title}
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown('<div style="font-size: 0.8rem; color: var(--muted-text); text-align: center; padding: 10px 0;">No news headlines available.</div>', unsafe_allow_html=True)
            except Exception:
                st.markdown('<div style="font-size: 0.8rem; color: var(--muted-text); text-align: center; padding: 10px 0;">No news headlines available.</div>', unsafe_allow_html=True)
                
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("📰 View Full News", key="home_news_btn", width='stretch'):
                st.session_state.active_tab = "news"
                st.rerun()

@st.cache_data(ttl=3600)
def get_ticker_news_sentiment(t_ticker):
    h_lines = fetch_news_headlines(t_ticker, max_items=4)
    if h_lines:
        return analyse_sentiment(t_ticker, h_lines)
    return None

if tab == "watchlist":

    # ══════════════════════════════════════════════════════════════════════════════
    # WATCHLIST PAGE — Premium redesign (Phase 4)
    # All backend calls, session_state, and navigation remain unchanged.
    # Only presentation layer is overhauled.
    # ══════════════════════════════════════════════════════════════════════════════

    # ── Global color tokens ───────────────────────────────────────────────────────
    WL_GREEN  = "#22c55e"
    WL_RED    = "#ef4444"
    WL_BLUE   = "#3b82f6"
    WL_AMBER  = "#f59e0b"
    WL_MUTED  = MUTED
    WL_TEXT   = TEXT
    WL_CARD   = CARD_BG
    WL_BORDER = BORDER

    # ── Per-page micro-animations and card CSS ────────────────────────────────────
    st.markdown(textwrap.dedent("""
    <style>
    .wl-stock-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 0;
        margin-bottom: 12px;
        overflow: hidden;
        transition: transform 0.22s cubic-bezier(.25,.8,.25,1), box-shadow 0.22s;
        position: relative;
    }
    .wl-stock-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.08);
        border-color: var(--primary-blue);
    }
    .wl-card-inner { padding: 14px 18px 12px; }
    .wl-pill {
        display: inline-flex; align-items: center; gap: 4px;
        border-radius: 20px; padding: 2px 10px;
        font-size: 0.68rem; font-weight: 800; letter-spacing: 0.03em;
    }
    .wl-badge {
        display: inline-flex; align-items: center;
        border-radius: 6px; padding: 2px 8px;
        font-size: 0.65rem; font-weight: 700;
    }
    .wl-kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 16px 18px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .wl-kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }
    .wl-filter-pill {
        border-radius: 20px; padding: 4px 14px;
        font-size: 0.75rem; font-weight: 700;
        cursor: pointer; transition: all 0.15s;
        border: 1px solid var(--border-color);
    }
    @keyframes wlFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .wl-animate { animation: wlFadeIn 0.3s ease both; }
    </style>
    """).strip(), unsafe_allow_html=True)

    # ── Watchlist GROUP tabs (multi-watchlist system — unchanged) ─────────────────
    all_group_names    = list(st.session_state.watchlist_groups.keys())
    sector_names_set   = set(SECTOR_WATCHLISTS.keys())
    custom_group_names = [g for g in all_group_names if g not in sector_names_set]
    sector_group_names = [g for g in all_group_names if g in sector_names_set]

    def _render_group_row(names, per_row=4, key_prefix="wlgrp"):
        for start in range(0, len(names), per_row):
            chunk = names[start:start + per_row]
            cols  = st.columns(per_row)
            for ci, gname in enumerate(chunk):
                with cols[ci]:
                    is_active = (gname == st.session_state.active_watchlist_group)
                    if st.button(gname, key=f"{key_prefix}_{gname}", width='stretch',
                                 type="primary" if is_active else "secondary"):
                        st.session_state.active_watchlist_group = gname
                        st.session_state.expanded_stock = None
                        st.rerun()

    # Page header
    st.markdown(textwrap.dedent(f"""
    <div style="margin-bottom: 18px;">
        <div style="font-size: 1.55rem; font-weight: 900; color: {WL_TEXT}; letter-spacing: -0.02em;">⭐ Watchlist</div>
        <div style="font-size: 0.85rem; color: {WL_MUTED}; margin-top: 3px; font-weight: 500;">Track your favourite stocks in one place.</div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # Custom watchlists group row
    if custom_group_names:
        _render_group_row(custom_group_names, per_row=3, key_prefix="wlgrp")

    add_new_col, _spacer = st.columns([1, 3])
    with add_new_col:
        if st.button("➕ New Watchlist", key="wlgrp_new_toggle", width='stretch',
                     help="Create a new watchlist group"):
            st.session_state.show_new_group = not st.session_state.get("show_new_group", False)
            st.rerun()

    if sector_group_names:
        st.markdown(f'<div style="font-size: 0.72rem; font-weight: 800; color: {WL_MUTED}; letter-spacing: 0.06em; text-transform: uppercase; margin: 14px 0 6px;">🧭 Sector Watchlists</div>', unsafe_allow_html=True)
        _render_group_row(sector_group_names, per_row=4, key_prefix="wlsec")

    # ── New group creation panel ───────────────────────────────────────────────
    if st.session_state.get("show_new_group", False):
        ng1, ng2 = st.columns([3, 1])
        with ng1:
            new_group_name = st.text_input(
                "New group name", key="new_group_name_input",
                placeholder="e.g. Tech Watchlist", label_visibility="collapsed"
            ).strip()
        with ng2:
            if st.button("✅ Create", key="confirm_new_group", width='stretch'):
                if not new_group_name:
                    st.error("Please enter a name!")
                elif new_group_name in st.session_state.watchlist_groups:
                    st.warning(f"'{new_group_name}' already exists!")
                else:
                    st.session_state.watchlist_groups[new_group_name] = []
                    st.session_state.active_watchlist_group = new_group_name
                    st.session_state.custom_watchlist = st.session_state.watchlist_groups[new_group_name]
                    st.session_state.show_new_group = False
                    st.rerun()

    st.markdown("<hr style='border:none; border-top:1px solid var(--border-color); margin:14px 0;'>", unsafe_allow_html=True)

    # ── Header: Search + Add + Refresh ────────────────────────────────────────
    hdr_search, hdr_add, hdr_refresh = st.columns([4, 1, 0.6])
    with hdr_search:
        search_query = st.text_input(
            "Search Watchlist", placeholder="🔍  Search by name or ticker… (e.g. Reliance, HDFC, HAL)",
            key="wl_search_input", label_visibility="collapsed"
        ).strip().lower()
    with hdr_add:
        if st.button("➕ Add Stock", key="wl_add_btn", width='stretch', type="primary"):
            st.session_state.show_add_stock = not st.session_state.get("show_add_stock", False)
            st.rerun()
    with hdr_refresh:
        if st.button("🔄", key="wl_refresh", width='stretch', help="Refresh prices"):
            get_batch_quotes.clear()
            get_index_quote.clear()
            st.session_state["_ar_watchlist"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh only during market hours ────────────
    _wl_elapsed = time.time() - st.session_state.get("_ar_watchlist", 0)
    if _wl_elapsed >= _AUTO_REFRESH_SECS and is_market_open():
        get_batch_quotes.clear()
        get_index_quote.clear()
        st.session_state["_ar_watchlist"] = time.time()
        st.rerun()

    # ── Add Stock Panel (improved styling, same logic) ─────────────────────────
    if st.session_state.get("show_add_stock", False):
        st.markdown(textwrap.dedent(f"""
        <div style="background: {WL_GREEN}0d; border: 1px solid {WL_GREEN}55; border-radius: 12px;
             padding: 14px 18px; margin-bottom: 12px;">
            <div style="font-size: 0.78rem; font-weight: 800; color: {WL_GREEN}; letter-spacing: 0.05em; text-transform: uppercase;">
                ➕ Add Stock to Watchlist
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)
        a1, a2, a3 = st.columns([2, 2, 1])
        with a1:
            new_ticker = st.text_input("NSE Ticker (e.g. MARUTI.NS)", key="new_stock_ticker",
                                       placeholder="RELIANCE.NS").upper().strip()
        with a2:
            new_name = st.text_input("Display Name", key="new_stock_name",
                                     placeholder="Reliance Industries")
        with a3:
            st.markdown("")
            if st.button("✅ Add", key="confirm_add", width='stretch'):
                if new_ticker and new_name:
                    existing = [t for t, _ in st.session_state.custom_watchlist]
                    if new_ticker in existing:
                        st.warning(f"⚠️ {new_ticker} is already in your watchlist!")
                    else:
                        st.session_state.custom_watchlist.append((new_ticker, new_name))
                        st.session_state.show_add_stock = False
                        st.success(f"✅ {new_name} added to watchlist!")
                        st.rerun()
                else:
                    st.error("Please enter both ticker and name!")

    # ── Filter the watchlist by search query ──────────────────────────────────
    filtered_wl = [
        (tkr, name) for tkr, name in st.session_state.custom_watchlist
        if (search_query == "" or search_query in name.lower() or search_query in tkr.lower())
    ]

    # ── Fetch all quotes in ONE batch call ─────────────────────────────────────
    all_tickers = tuple(t for t, _ in filtered_wl) if filtered_wl else ()
    if all_tickers:
        with st.spinner("Loading live prices…"):
            batch     = get_batch_quotes(all_tickers)
            batch_rsi = get_batch_rsi(all_tickers)
            batch_52w = get_batch_52w_range(all_tickers)
    else:
        batch = {}; batch_rsi = {}; batch_52w = {}

    # ── KPI Summary Cards ─────────────────────────────────────────────────────
    if filtered_wl and batch:
        kpi_gainers = sum(1 for tkr, _ in filtered_wl if tkr in batch and batch[tkr][3] >= 0)
        kpi_losers  = sum(1 for tkr, _ in filtered_wl if tkr in batch and batch[tkr][3] < 0)
        pcts = [batch[tkr][3] for tkr, _ in filtered_wl if tkr in batch]
        kpi_avg_chg = (sum(pcts) / len(pcts)) if pcts else 0.0
        avg_color   = WL_GREEN if kpi_avg_chg >= 0 else WL_RED
        avg_arrow   = "▲" if kpi_avg_chg >= 0 else "▼"

        k1, k2, k3, k4 = st.columns(4)
        kpi_cards = [
            (k1, "⭐", "Total Stocks", str(len(filtered_wl)), WL_BLUE, None),
            (k2, "📈", "Gainers Today", str(kpi_gainers), WL_GREEN, None),
            (k3, "📉", "Losers Today",  str(kpi_losers),  WL_RED,   None),
            (k4, "💰", "Avg Daily Change", f"{avg_arrow} {abs(kpi_avg_chg):.2f}%", avg_color, None),
        ]
        for col, icon, label, val, color, _ in kpi_cards:
            with col:
                st.markdown(textwrap.dedent(f"""
                <div class="wl-kpi-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-size:0.68rem; color:{WL_MUTED}; font-weight:700; text-transform:uppercase; letter-spacing:0.05em;">{label}</span>
                        <span style="font-size:1.1rem;">{icon}</span>
                    </div>
                    <div style="font-size:1.5rem; font-weight:900; color:{color};">{val}</div>
                </div>
                """).strip(), unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Sort + Filter Toolbar ─────────────────────────────────────────────────
    sort_key = st.session_state.get("wl_sort_key", "Default")
    filter_mode = st.session_state.get("wl_filter_mode", "All")

    toolbar_c1, toolbar_c2 = st.columns([2, 3])
    with toolbar_c1:
        new_sort = st.selectbox(
            "Sort by", ["Default", "Price ▲", "Price ▼", "Change % ▲", "Change % ▼", "A–Z"],
            index=["Default", "Price ▲", "Price ▼", "Change % ▲", "Change % ▼", "A–Z"].index(sort_key),
            key="wl_sort_select", label_visibility="collapsed"
        )
        if new_sort != sort_key:
            st.session_state.wl_sort_key = new_sort
            st.rerun()
    with toolbar_c2:
        f1, f2, f3 = st.columns(3)
        for fc, fmode in [(f1, "All"), (f2, "Gainers"), (f3, "Losers")]:
            with fc:
                if st.button(fmode, key=f"wl_filter_{fmode}", width='stretch',
                             type="primary" if filter_mode == fmode else "secondary"):
                    st.session_state.wl_filter_mode = fmode
                    st.rerun()

    # Apply filter
    if filter_mode == "Gainers":
        filtered_wl = [(t, n) for t, n in filtered_wl if t in batch and batch[t][3] >= 0]
    elif filter_mode == "Losers":
        filtered_wl = [(t, n) for t, n in filtered_wl if t in batch and batch[t][3] < 0]

    # Apply sort
    def _sort_val(item):
        tkr, name = item
        q = batch.get(tkr)
        if sort_key == "Price ▲":  return q[0] if q else 0
        if sort_key == "Price ▼":  return -(q[0] if q else 0)
        if sort_key == "Change % ▲": return q[3] if q else 0
        if sort_key == "Change % ▼": return -(q[3] if q else 0)
        if sort_key == "A–Z":      return name.lower()
        return 0
    if sort_key != "Default":
        filtered_wl = sorted(filtered_wl, key=_sort_val)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Empty States ──────────────────────────────────────────────────────────
    if not st.session_state.custom_watchlist:
        st.markdown(textwrap.dedent(f"""
        <div class="wl-animate" style="background:{WL_CARD}; border:1px solid {WL_BORDER}; border-radius:20px;
             padding:48px 24px; text-align:center; margin:16px 0;">
            <div style="font-size:3rem; margin-bottom:14px;">⭐</div>
            <div style="font-size:1.2rem; font-weight:800; color:{WL_TEXT}; margin-bottom:6px;">Your watchlist is empty</div>
            <div style="font-size:0.88rem; color:{WL_MUTED}; margin-bottom:20px;">Add your favourite stocks to start tracking them in real-time.</div>
        </div>
        """).strip(), unsafe_allow_html=True)
        if st.button("➕ Add Your First Stock", key="wl_empty_add", type="primary"):
            st.session_state.show_add_stock = True
            st.rerun()
        st.stop()

    if not filtered_wl and search_query:
        st.markdown(textwrap.dedent(f"""
        <div class="wl-animate" style="background:{WL_CARD}; border:1px dashed {WL_BORDER}; border-radius:16px;
             padding:36px 24px; text-align:center; margin:16px 0;">
            <div style="font-size:2rem; margin-bottom:10px;">🔍</div>
            <div style="font-size:1.05rem; font-weight:700; color:{WL_TEXT}; margin-bottom:6px;">No results for "{search_query}"</div>
            <div style="font-size:0.82rem; color:{WL_MUTED};">Try a different name or ticker symbol.</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    elif not filtered_wl and filter_mode != "All":
        st.markdown(textwrap.dedent(f"""
        <div class="wl-animate" style="background:{WL_CARD}; border:1px dashed {WL_BORDER}; border-radius:16px;
             padding:36px 24px; text-align:center; margin:16px 0;">
            <div style="font-size:2rem; margin-bottom:10px;">{'📈' if filter_mode=='Gainers' else '📉'}</div>
            <div style="font-size:1.05rem; font-weight:700; color:{WL_TEXT}; margin-bottom:6px;">No {filter_mode} right now</div>
            <div style="font-size:0.82rem; color:{WL_MUTED};">Switch the filter to see all stocks.</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    # ── Premium Stock Cards ────────────────────────────────────────────────────
    for i, (tkr, name) in enumerate(filtered_wl):
        q            = batch.get(tkr)
        owned_shares = st.session_state.pt_holdings.get(tkr, {}).get("shares", 0)
        is_expanded  = st.session_state.expanded_stock == tkr

        # Determine color theme for this card
        if q:
            cur, _, chg, pct = q
            accent_color = WL_GREEN if pct >= 0 else WL_RED
            arrow        = "▲" if pct >= 0 else "▼"
            price_str    = f"₹{cur:,.2f}"
            chg_str      = f"{arrow} {abs(pct):.2f}%"
            chg_abs_str  = f"{'+ ' if chg>=0 else '- '}₹{abs(chg):.2f}"
            has_data     = True
        else:
            accent_color = WL_MUTED
            price_str    = "Loading…"
            chg_str      = "—"
            chg_abs_str  = ""
            has_data     = False
            cur = pct = 0

        # RSI signal
        sig = batch_rsi.get(tkr) if batch_rsi else None
        rsi_html = ""
        if sig:
            sc = sig["color"]
            ma_arrow = "▲" if sig["above_ma"] else "▼"
            ma_clr   = WL_GREEN if sig["above_ma"] else WL_RED
            rsi_html = (
                f'<span class="wl-pill" style="background:{sc}18; color:{sc}; border:1px solid {sc}44;">'
                f'{sig["label"]}</span>'
                f'&nbsp;<span style="font-size:0.65rem; color:{WL_MUTED};">RSI <b style="color:{sc};">{sig["rsi"]}</b></span>'
                f'&nbsp;<span style="font-size:0.65rem; color:{WL_MUTED};">MA20 <b style="color:{ma_clr};">{ma_arrow}{abs(sig["ma_dist"])}%</b></span>'
                f'&nbsp;<span style="font-size:0.62rem; color:#5b6380; font-style:italic;">{sig["detail"]}</span>'
            )

        # 52W range bar
        w52 = batch_52w.get(tkr) if batch_52w else None
        w52_html = ""
        if w52:
            pos = w52["pos_pct"]
            if pos >= 90:    bar_c, bar_note = WL_RED,   "Near 52W High"
            elif pos >= 70:  bar_c, bar_note = "#f97316","Momentum zone"
            elif pos <= 10:  bar_c, bar_note = "#06b6d4","Near 52W Low"
            elif pos <= 30:  bar_c, bar_note = "#84cc16","Value zone"
            else:            bar_c, bar_note = WL_MUTED, "Mid-range"
            w52_html = (
                f'<div style="margin-top:8px;">'
                f'<div style="display:flex; justify-content:space-between; font-size:0.6rem; color:#5b6380; margin-bottom:3px;">'
                f'<span>₹{w52["w52_low"]:,.0f}</span>'
                f'<span style="color:{bar_c}; font-weight:700;">{bar_note} ({w52["from_high_pct"]:+.1f}% from high)</span>'
                f'<span>₹{w52["w52_high"]:,.0f}</span></div>'
                f'<div style="position:relative; height:5px; background:{WL_BORDER}; border-radius:4px;">'
                f'<div style="position:absolute; left:{pos}%; top:-2px; width:3px; height:9px; background:{bar_c}; border-radius:2px;"></div>'
                f'</div></div>'
            )

        owned_badge = ""
        if owned_shares > 0:
            owned_badge = (
                f'&nbsp;<span class="wl-badge" style="background:{WL_BLUE}18; color:{WL_BLUE}; border:1px solid {WL_BLUE}33;">'
                f'{owned_shares} owned</span>'
            )

        expand_icon = "▾" if is_expanded else "▸"

        # Main card HTML
        # NOTE: Streamlit's markdown renderer treats a block indented by 4+ spaces
        # at the very start of the string as an INDENTED CODE BLOCK (CommonMark
        # rule), not as raw HTML — even with unsafe_allow_html=True. Because this
        # f-string previously opened with 8 leading spaces on every line (to match
        # the surrounding Python indentation inside the for-loop), the parser
        # printed the tags as literal text instead of rendering them. Building the
        # fragment with textwrap.dedent() + strip() guarantees the first line (and
        # therefore the whole fragment) starts at column 0, so it's recognized as
        # an HTML block and rendered normally.
        card_html = textwrap.dedent(f"""\
            <div class="wl-stock-card wl-animate" style="border-left: 3px solid {accent_color}; animation-delay: {i*0.04:.2f}s;">
                <div class="wl-card-inner">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                                <span style="width:8px; height:8px; border-radius:50%; background:{accent_color}; display:inline-block; flex-shrink:0;"></span>
                                <span style="font-size:1rem; font-weight:900; color:{WL_TEXT};">{name}</span>
                                <span style="font-size:0.72rem; color:{WL_MUTED}; font-weight:600;">{tkr.replace('.NS','')}</span>
                                {owned_badge}
                                <span style="font-size:0.68rem; color:{WL_MUTED}; cursor:pointer;">{expand_icon}</span>
                            </div>
                            <div style="margin-top:6px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                                {rsi_html}
                            </div>
                            {w52_html}
                        </div>
                        <div style="text-align:right; flex-shrink:0;">
                            <div style="font-size:1.3rem; font-weight:900; color:{WL_TEXT};">{price_str}</div>
                            <div style="margin-top:4px;">
                                <span class="wl-pill" style="background:{accent_color}18; color:{accent_color}; border:1px solid {accent_color}44;">
                                    {chg_str}
                                </span>
                            </div>
                            <div style="font-size:0.68rem; color:{WL_MUTED}; margin-top:3px;">{chg_abs_str}</div>
                        </div>
                    </div>
                </div>
            </div>
        """).strip()
        card_html = "\n".join(line.strip() for line in card_html.splitlines())
        st.markdown(card_html, unsafe_allow_html=True)

        # ── Action buttons row (below each card) ──────────────────────────────
        btn_chart, btn_buy, btn_sell, btn_del = st.columns([1.2, 1.2, 1.2, 0.7])
        with btn_chart:
            if st.button("📊 Chart" if not is_expanded else "✕ Close",
                         key=f"wlexp_{tkr}", width='stretch'):
                st.session_state.expanded_stock = None if is_expanded else tkr
                st.rerun()
        with btn_buy:
            if st.button("🟢 Buy", key=f"wlb_{tkr}", width='stretch', type="primary"):
                st.session_state.order_ticker = tkr
                st.session_state.order_action = "BUY"
                st.session_state.active_tab   = "orders"
                st.rerun()
        with btn_sell:
            if st.button("🔴 Sell", key=f"wls_{tkr}", width='stretch', type="secondary"):
                st.session_state.order_ticker = tkr
                st.session_state.order_action = "SELL"
                st.session_state.active_tab   = "orders"
                st.rerun()
        with btn_del:
            if st.button("🗑", key=f"wldel_{tkr}", width='stretch', help="Remove from watchlist"):
                st.session_state.custom_watchlist = [
                    (t, n) for t, n in st.session_state.custom_watchlist if t != tkr
                ]
                st.session_state.watchlist_groups[st.session_state.active_watchlist_group] = \
                    st.session_state.custom_watchlist
                if st.session_state.expanded_stock == tkr:
                    st.session_state.expanded_stock = None
                st.rerun()

        # ── Expanded Detail Panel (unchanged backend logic) ───────────────────
        if is_expanded:
            # Pivot levels helper
            def get_support_resistance(df_in):
                if df_in is None or df_in.empty or len(df_in) < 15:
                    return None, None
                # simple local min/max over 10-day windows
                highs = df_in["High"].rolling(window=10, center=True).max().dropna()
                lows = df_in["Low"].rolling(window=10, center=True).min().dropna()
                if len(highs) > 0 and len(lows) > 0:
                    support = float(lows.iloc[-1])
                    resistance = float(highs.iloc[-1])
                    return support, resistance
                return None, None

            # Create a placeholder for the skeleton loading effect
            loader = st.empty()
            with loader.container():
                st.markdown(textwrap.dedent("""
                <style>
                @keyframes pulse {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                .skeleton-container {
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: 16px;
                    padding: 20px;
                    margin: 10px 0;
                    animation: wlFadeIn 0.3s ease;
                }
                .skeleton-pulse {
                    background: linear-gradient(-90deg, rgba(148, 163, 184, 0.08) 0%, rgba(148, 163, 184, 0.18) 50%, rgba(148, 163, 184, 0.08) 100%);
                    background-size: 400% 400%;
                    animation: pulse 1.5s ease infinite;
                    border-radius: 6px;
                }
                </style>
                <div class="skeleton-container">
                    <div class="skeleton-pulse" style="width: 25%; height: 26px; margin-bottom: 15px;"></div>
                    <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                        <div class="skeleton-pulse" style="flex: 1; min-width: 90px; height: 50px;"></div>
                        <div class="skeleton-pulse" style="flex: 1; min-width: 90px; height: 50px;"></div>
                        <div class="skeleton-pulse" style="flex: 1; min-width: 90px; height: 50px;"></div>
                        <div class="skeleton-pulse" style="flex: 1; min-width: 90px; height: 50px;"></div>
                    </div>
                    <div class="skeleton-pulse" style="width: 100%; height: 450px;"></div>
                </div>
                """).strip(), unsafe_allow_html=True)

            # Perform the data load operations
            info = get_stock_info(tkr)
            rsi_ma_signal = get_rsi_ma_signal(tkr)
            
            # Fetch 5d data for high/low/open/close metrics
            today_df = fetch_stock_data_cached(tkr, period="5d", interval="1d")
            
            # Clear skeleton loading state
            loader.empty()

            # Format info parameters
            w52h = f"₹{info['w52_high']:,.2f}"  if info.get("w52_high")  else "—"
            w52l = f"₹{info['w52_low']:,.2f}"   if info.get("w52_low")   else "—"
            mcap = info.get("mktcap")
            if mcap:
                if mcap >= 1e12:   mcap_str = f"₹{mcap/1e12:.2f}T"
                elif mcap >= 1e9:  mcap_str = f"₹{mcap/1e9:.2f}B"
                else:              mcap_str = f"₹{mcap/1e7:.1f}Cr"
            else:
                mcap_str = "—"

            if today_df is not None and not today_df.empty:
                open_price = f"₹{today_df['Open'].iloc[-1]:,.2f}"
                close_price = f"₹{today_df['Close'].iloc[-1]:,.2f}"
                high_price = f"₹{today_df['High'].iloc[-1]:,.2f}"
                low_price = f"₹{today_df['Low'].iloc[-1]:,.2f}"
                volume_val = today_df['Volume'].iloc[-1]
                if volume_val >= 1e7: volume_str = f"{volume_val/1e7:.2f}Cr"
                elif volume_val >= 1e5: volume_str = f"{volume_val/1e5:.2f}L"
                else: volume_str = f"{volume_val:,.0f}"
            else:
                open_price = close_price = high_price = low_price = volume_str = "—"

            # Inject Performance Cards & Custom Container Styles
            st.markdown(textwrap.dedent(f"""
            <style>
            .perf-card-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
                gap: 10px;
                margin-top: 4px;
                margin-bottom: 16px;
                animation: wlFadeIn 0.25s ease;
            }}
            .perf-card {{
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 10px 14px;
                text-align: center;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .perf-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.04);
                border-color: var(--primary-blue);
            }}
            .perf-label {{
                font-size: 0.62rem;
                color: var(--muted-text);
                font-weight: 700;
                letter-spacing: .05em;
                text-transform: uppercase;
            }}
            .perf-val {{
                font-size: 0.88rem;
                font-weight: 800;
                color: var(--text-color);
                margin-top: 4px;
            }}
            .toolbar-container {{
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 12px 16px;
                margin-bottom: 12px;
                animation: wlFadeIn 0.25s ease;
            }}
            </style>
            
            <div class="perf-card-container">
                <div class="perf-card">
                    <div class="perf-label">OPEN</div>
                    <div class="perf-val">{open_price}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">HIGH</div>
                    <div class="perf-val" style="color: {WL_GREEN};">{high_price}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">LOW</div>
                    <div class="perf-val" style="color: {WL_RED};">{low_price}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">PREV CLOSE</div>
                    <div class="perf-val">{close_price}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">VOLUME</div>
                    <div class="perf-val">{volume_str}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">52W HIGH</div>
                    <div class="perf-val" style="color: {WL_GREEN};">{w52h}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">52W LOW</div>
                    <div class="perf-val" style="color: {WL_RED};">{w52l}</div>
                </div>
                <div class="perf-card">
                    <div class="perf-label">MKT CAP</div>
                    <div class="perf-val">{mcap_str}</div>
                </div>
            </div>
            """).strip(), unsafe_allow_html=True)

            # Chart timeframe & indicator options toolbar
            market_open = is_market_open()
            if market_open:
                tf_options = {
                    "1D": ("1d", "1m"), "5D": ("5d", "5m"),
                    "1M": ("1mo", "1d"), "3M": ("3mo", "1d"),
                    "6M": ("6mo", "1d"), "1Y": ("1y", "1d"),
                    "5Y": ("5y", "1wk"), "MAX": ("max", "1mo")
                }
                default_idx = 0
            else:
                tf_options = {
                    "1D": ("1d", "5m"), "5D": ("5d", "15m"),
                    "1M": ("1mo", "1d"), "3M": ("3mo", "1d"),
                    "6M": ("6mo", "1d"), "1Y": ("1y", "1d"),
                    "5Y": ("5y", "1wk"), "MAX": ("max", "1mo")
                }
                default_idx = 2

            # Initialize states if not present
            if f"type_{tkr}" not in st.session_state:
                st.session_state[f"type_{tkr}"] = "Candlestick"
            if f"ind_{tkr}" not in st.session_state:
                st.session_state[f"ind_{tkr}"] = ["Volume"]
            if f"comp_{tkr}" not in st.session_state:
                st.session_state[f"comp_{tkr}"] = []
            if f"ai_pred_{tkr}" not in st.session_state:
                st.session_state[f"ai_pred_{tkr}"] = False
            if f"fs_{tkr}" not in st.session_state:
                st.session_state[f"fs_{tkr}"] = False

            # Toolbar UI Box
            st.markdown('<div style="font-size:0.72rem; font-weight:800; color:var(--muted-text); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">🛠️ Chart Toolbar</div>', unsafe_allow_html=True)
            
            with st.container():
                t1, t2, t3, t4 = st.columns([2.4, 1.2, 2.4, 2.2])
                with t1:
                    sel_tf = st.radio("Timeframe", list(tf_options.keys()), index=default_idx,
                                      horizontal=True, key=f"tf_{tkr}", label_visibility="collapsed")
                with t2:
                    sel_type = st.selectbox("Chart Type", ["Candlestick", "Line", "Area"], 
                                            key=f"type_{tkr}", label_visibility="collapsed")
                with t3:
                    sel_indicators = st.multiselect("Indicators", ["Volume", "SMA 20", "SMA 50", "EMA 20", "Bollinger Bands", "RSI", "MACD"],
                                                    key=f"ind_{tkr}", label_visibility="collapsed")
                with t4:
                    comparison_candidates = [t for t, n in st.session_state.custom_watchlist if t != tkr]
                    sel_compare = st.multiselect("Compare+", comparison_candidates,
                                                    key=f"comp_{tkr}", placeholder="Compare Tickers", label_visibility="collapsed")
                
                # Second toolbar row for toggles & export
                ta1, ta2, ta3, ta4 = st.columns([1.5, 1.5, 1.5, 1.5])
                with ta1:
                    show_ai_forecast = st.checkbox("AI Forecast 🔮", key=f"ai_pred_{tkr}")
                with ta2:
                    fullscreen = st.checkbox("Fullscreen 🖥️", key=f"fs_{tkr}")
                with ta3:
                    # CSV Export
                    sel_period, sel_interval = tf_options[sel_tf]
                    plot_df = fetch_stock_data_cached(tkr, sel_period, sel_interval)
                    if plot_df is not None and not plot_df.empty:
                        csv_data = plot_df.to_csv(index=False).encode('utf-8')
                        st.download_button(label="📥 Export CSV", data=csv_data, 
                                           file_name=f"{tkr.replace('.NS','')}_{sel_tf}.csv", 
                                           mime="text/csv", key=f"csv_{tkr}", use_container_width=True)
                with ta4:
                    if st.button("🔄 Reset", key=f"reset_{tkr}", use_container_width=True):
                        st.session_state[f"type_{tkr}"] = "Candlestick"
                        st.session_state[f"ind_{tkr}"] = ["Volume"]
                        st.session_state[f"comp_{tkr}"] = []
                        st.session_state[f"ai_pred_{tkr}"] = False
                        st.session_state[f"fs_{tkr}"] = False
                        st.rerun()

            # Live vs Closed status pill
            is_intraday = sel_interval in ("1m", "5m", "15m")
            if is_intraday and market_open:
                st.markdown(
                    f'<span class="wl-pill" style="background:{WL_GREEN}18; color:{WL_GREEN}; border:1px solid {WL_GREEN}44; margin-bottom:12px;">'
                    f'🔴 LIVE — Auto data</span>', unsafe_allow_html=True)
            elif is_intraday and not market_open:
                st.markdown(
                    f'<span class="wl-pill" style="background:{WL_AMBER}18; color:{WL_AMBER}; border:1px solid {WL_AMBER}44; margin-bottom:12px;">'
                    f'🕐 Market Closed — Last session data</span>', unsafe_allow_html=True)

            # Split screen layout: Chart on Left (3.2), Technical/AI on Right (1)
            col_chart, col_panel = st.columns([3.2, 1])

            with col_chart:
                # Load chart using parameters
                chart = get_stock_chart(
                    ticker=tkr,
                    period=sel_period,
                    interval=sel_interval,
                    chart_type=sel_type,
                    indicators=sel_indicators,
                    comparison_tickers=sel_compare,
                    show_prediction=show_ai_forecast,
                    fullscreen=fullscreen
                )

                if chart:
                    st.plotly_chart(chart, use_container_width=True, key=f"chart_fig_{tkr}_{sel_tf}_{sel_type}")
                else:
                    st.markdown(textwrap.dedent(f"""
                    <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 16px; padding: 40px; text-align: center; margin: 15px 0;">
                        <div style="font-size: 3rem; margin-bottom: 12px;">📈</div>
                        <h4 style="font-size: 1.1rem; font-weight: 700; margin: 0 0 8px 0; color:var(--text-color);">Chart Data Unavailable</h4>
                        <p style="font-size: 0.82rem; color: var(--muted-text); margin: 0; line-height: 1.4;">
                            yf.download was unable to fetch historical data for {tkr} in the {sel_tf} range.<br>
                            Please try switching the timeframe or check if the market is currently active.
                        </p>
                    </div>
                    """).strip(), unsafe_allow_html=True)

            with col_panel:
                st.markdown(textwrap.dedent(f"""
                <div style="font-size: 0.72rem; font-weight: 800; color: var(--muted-text); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">📊 Technical Metrics</div>
                """).strip(), unsafe_allow_html=True)
                
                # RSI Indicator Card
                if rsi_ma_signal:
                    rsi_val = rsi_ma_signal.get("rsi")
                    rsi_color = rsi_ma_signal.get("color", "#8b90a0")
                    ma_dist = rsi_ma_signal.get("ma_dist", 0.0)
                    st.markdown(textwrap.dedent(f"""
                    <div style="margin-bottom: 14px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-size:0.75rem; font-weight:600; color:var(--text-color);">RSI (14)</span>
                            <span style="font-size:0.7rem; font-weight:700; color:{rsi_color}; background:{rsi_color}18; padding:1px 6px; border-radius:4px;">{rsi_val}</span>
                        </div>
                        <div style="font-size:0.68rem; color:var(--secondary-text);">{rsi_ma_signal.get("detail", "")}</div>
                    </div>
                    <div style="margin-bottom: 14px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-size:0.75rem; font-weight:600; color:var(--text-color);">MA Trend (20d)</span>
                            <span style="font-size:0.7rem; font-weight:700; color:{WL_GREEN if ma_dist >= 0 else WL_RED};">{ma_dist:+.1f}% from MA</span>
                        </div>
                        <div style="font-size:0.68rem; color:var(--secondary-text);">
                            Price is trading <b>{'above' if rsi_ma_signal.get('above_ma') else 'below'}</b> 20-day Simple Moving Average (₹{rsi_ma_signal.get('ma20', 0):,.2f}).
                        </div>
                    </div>
                    """).strip(), unsafe_allow_html=True)
                else:
                    st.markdown("<div style='font-size:0.72rem; color:var(--muted-text); margin-bottom:14px;'>Technical indicators unavailable.</div>", unsafe_allow_html=True)

                # Support & Resistance pivots
                support, resistance = get_support_resistance(plot_df)
                if support and resistance:
                    st.markdown(textwrap.dedent(f"""
                    <div style="margin-bottom: 16px; border-top: 1px solid var(--border-color); padding-top: 12px;">
                        <div style="font-size: 0.72rem; font-weight: 800; color: var(--muted-text); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">🎯 Pivot Levels</div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.72rem; margin-bottom: 4px; color:var(--text-color);">
                            <span style="color: var(--secondary-text);">Resistance:</span>
                            <b style="color: {WL_RED};">₹{resistance:,.2f}</b>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color:var(--text-color);">
                            <span style="color: var(--secondary-text);">Support:</span>
                            <b style="color: {WL_GREEN};">₹{support:,.2f}</b>
                        </div>
                    </div>
                    """).strip(), unsafe_allow_html=True)

                # AI Overlay - News Sentiment Analysis
                st.markdown(textwrap.dedent("""
                <div style="margin-bottom: 8px; border-top: 1px solid var(--border-color); padding-top: 12px;">
                    <div style="font-size: 0.72rem; font-weight: 800; color: var(--muted-text); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">🔮 AI Trend Analysis</div>
                </div>
                """).strip(), unsafe_allow_html=True)

                sentiment_data = get_ticker_news_sentiment(tkr)

                if sentiment_data:
                    s_overall = sentiment_data.get("overall", "Neutral")
                    s_score = sentiment_data.get("score", 0)
                    s_summary = sentiment_data.get("summary", "No summary.")

                    if s_overall == "Bullish": s_color = WL_GREEN; s_badge = "BULLISH 🟢"
                    elif s_overall == "Bearish": s_color = WL_RED; s_badge = "BEARISH 🔴"
                    else: s_color = "#f59e0b"; s_badge = "NEUTRAL 🟡"

                    st.markdown(textwrap.dedent(f"""
                    <div style="background: {s_color}08; border: 1px solid {s_color}33; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-weight:700; color:var(--text-color);">
                            <span>Trend Verdict</span>
                            <span style="color:{s_color};">{s_badge}</span>
                        </div>
                        <div style="font-size:0.7rem; color:var(--secondary-text); margin-top:2px;">Sentiment Score: <b>{s_score}</b> / 100</div>
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-color); line-height: 1.4; font-style: italic; background: rgba(148,163,184,0.04); padding: 8px; border-left: 3px solid var(--primary-blue); border-radius: 0 4px 4px 0;">
                        "{s_summary}"
                    </div>
                    """).strip(), unsafe_allow_html=True)
                else:
                    st.markdown("<div style='font-size:0.72rem; color:var(--muted-text);'>No news headlines sentiment found.</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

elif tab == "orders":
    # ── Calculate summary values for Dashboard Overview ──
    o_exec = len(st.session_state.pt_history)
    o_pend = len(st.session_state.pt_targets)
    o_canc = st.session_state.get("cancelled_orders_count", 0)
    o_tot  = o_exec + o_pend + o_canc

    # ── Summary Cards ──
    st.markdown(f"""
    <div class="db-grid">
        <div class="db-card">
            <div class="db-label">📦 Total Orders</div>
            <div class="db-val">{o_tot}</div>
            <div class="db-sub">Lifetime count</div>
        </div>
        <div class="db-card" style="border-bottom: 3px solid var(--success-color);">
            <div class="db-label" style="color: var(--success-color);">✅ Executed Orders</div>
            <div class="db-val" style="color: var(--success-color);">{o_exec}</div>
            <div class="db-sub">Completed trades</div>
        </div>
        <div class="db-card" style="border-bottom: 3px solid var(--primary-blue);">
            <div class="db-label" style="color: var(--primary-blue);">⏳ Pending Orders</div>
            <div class="db-val" style="color: var(--primary-blue);">{o_pend}</div>
            <div class="db-sub">Active GTT targets</div>
        </div>
        <div class="db-card" style="border-bottom: 3px solid var(--danger-color);">
            <div class="db-label" style="color: var(--danger-color);">❌ Cancelled Orders</div>
            <div class="db-val" style="color: var(--danger-color);">{o_canc}</div>
            <div class="db-sub">GTT cancellations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Header with Refresh ──
    ord_h, ord_r = st.columns([5, 1])
    with ord_h:
        st.markdown('<div class="sec-title">PLACE ORDER</div>', unsafe_allow_html=True)
    with ord_r:
        if st.button("🔄", key="orders_refresh", help="Price refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            st.session_state["_ar_orders"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh only during market hours ──
    _ord_elapsed = time.time() - st.session_state.get("_ar_orders", 0)
    if _ord_elapsed >= _AUTO_REFRESH_SECS and is_market_open():
        get_index_quote.clear()
        get_batch_quotes.clear()
        st.session_state["_ar_orders"] = time.time()
        st.rerun()

    # ── Position Sizing Calculator fill quantity ──
    if "_psc_pending_qty" in st.session_state:
        st.session_state.pt_qty = st.session_state.pop("_psc_pending_qty")

    def avg_color_word(change):
        if change is None:
            return ""
        if change < 0:
            return f"₹{abs(change):,.2f} kam hua (accha hai)"
        elif change > 0:
            return f"₹{change:,.2f} zyada hua"
        return "same raha"

    # ── Pre-fill from watchlist click ──
    wl_names   = [name for _, name in WATCHLIST]
    wl_tickers = [tkr  for tkr, _ in WATCHLIST]
    try:
        def_idx = wl_tickers.index(st.session_state.get("order_ticker", wl_tickers[0]))
    except ValueError:
        def_idx = 0

    # ── Order form wrap in glassmorphic card container ──
    st.markdown('<div class="table-container" style="padding: 20px; border-bottom: 2px solid var(--primary-blue);">', unsafe_allow_html=True)
    
    sel_col, qty_col = st.columns([3, 1])
    with sel_col:
        chosen_name   = st.selectbox("Stock", options=wl_names, index=def_idx, key="order_stock_select")
        chosen_ticker = wl_tickers[wl_names.index(chosen_name)]
    with qty_col:
        pt_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="pt_qty")

    pt_quote = get_index_quote(chosen_ticker)
    if pt_quote:
        pt_price  = pt_quote[0]
        total_val = round(pt_price * pt_qty, 2)
        chg_c  = "var(--success-color)" if pt_quote[2] >= 0 else "var(--danger-color)"
        arrow  = "▲" if pt_quote[2] >= 0 else "▼"
        owned  = st.session_state.pt_holdings.get(chosen_ticker, {}).get("shares", 0)
        st.markdown(f"""
        <div style="background:var(--tab-list-bg); border:1px solid var(--border-color); border-radius:10px;
                    padding:12px 18px; margin:12px 0 16px 0;
                    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
          <div>
            <span style="font-size:1.3rem; font-weight:800; color:var(--text-color);">₹{pt_price:,.2f}</span>
            &nbsp;<span style="color:{chg_c}; font-size:0.85rem; font-weight:700;">{arrow} {abs(pt_quote[2]):,.2f} ({pt_quote[3]:+.2f}%)</span>
          </div>
          <div style="font-size:0.8rem; color:var(--secondary-text);">
            Value: <b style="color:var(--text-color);">₹{total_val:,.2f}</b> &nbsp;|&nbsp;
            Cash: <b style="color:var(--primary-blue);">₹{st.session_state.pt_cash:,.0f}</b> &nbsp;|&nbsp;
            Holdings: <b style="color:var(--text-color);">{owned} shares</b>
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        pt_price  = None
        total_val = 0
        st.warning("⚠️ Price fetch nahi hui. Thodi der mein try karo.")

    b_col, s_col = st.columns(2)
    with b_col:
        do_buy  = st.button("🟢 BUY NOW", key="exec_buy", type="primary", use_container_width=True)
    with s_col:
        do_sell = st.button("🔴 SELL NOW", key="exec_sell", type="secondary", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Execute BUY order ──
    if pt_price and do_buy:
        holding = st.session_state.pt_holdings.get(chosen_ticker, {"shares": 0, "avg_price": 0.0})
        if total_val > st.session_state.pt_cash:
            st.error(f"❌ Balance kam hai! Chahiye ₹{total_val:,.2f}, hai ₹{st.session_state.pt_cash:,.0f}")
            st.toast("❌ Order Failed: Insufficient Balance", icon="❌")
        else:
            new_shares = holding["shares"] + pt_qty
            new_avg    = round((holding["shares"] * holding["avg_price"] + total_val) / new_shares, 2)
            first_buy_date = holding.get("first_buy_date") or ist_now().strftime("%Y-%m-%d")
            st.session_state.pt_holdings[chosen_ticker] = {
                "shares": new_shares, "avg_price": new_avg, "first_buy_date": first_buy_date
            }
            st.session_state.pt_cash = round(st.session_state.pt_cash - total_val, 2)
            st.session_state.pt_history.append({
                "Action": "BUY", "Ticker": chosen_ticker, "Name": chosen_name,
                "Shares": pt_qty, "Price": pt_price, "Value": total_val, "P&L": None,
                "Time": ist_now().strftime("%d %b %Y %I:%M %p"),
            })
            save_portfolio()
            st.success(f"✅ {pt_qty} × {chosen_name} BUY @ ₹{pt_price:,.2f} | Cash: ₹{st.session_state.pt_cash:,.0f}")
            st.toast(f"🟢 BUY executed: {pt_qty} shares of {chosen_name}!", icon="✅")
            st.rerun()

    # ── Execute SELL order ──
    if pt_price and do_sell:
        holding = st.session_state.pt_holdings.get(chosen_ticker, {"shares": 0, "avg_price": 0.0})
        if holding["shares"] == 0:
            st.error(f"❌ {chosen_name} ke koi shares nahi hain!")
            st.toast("❌ Order Failed: No shares owned", icon="❌")
        elif holding["shares"] < pt_qty:
            st.error(f"❌ Sirf {holding['shares']} shares hain!")
            st.toast("❌ Order Failed: Exceeds holdings", icon="❌")
        else:
            proceeds  = round(pt_price * pt_qty, 2)
            pnl       = round((pt_price - holding["avg_price"]) * pt_qty, 2)
            remaining = holding["shares"] - pt_qty
            if remaining == 0:
                del st.session_state.pt_holdings[chosen_ticker]
            else:
                st.session_state.pt_holdings[chosen_ticker]["shares"] = remaining
            st.session_state.pt_cash = round(st.session_state.pt_cash + proceeds, 2)
            pnl_str = f"+₹{pnl:,.2f}" if pnl >= 0 else f"-₹{abs(pnl):,.2f}"
            st.session_state.pt_history.append({
                "Action": "SELL", "Ticker": chosen_ticker, "Name": chosen_name,
                "Shares": pt_qty, "Price": pt_price, "Value": proceeds, "P&L": pnl,
                "Time": ist_now().strftime("%d %b %Y %I:%M %p"),
            })
            save_portfolio()
            emoji = "🟢" if pnl >= 0 else "🔴"
            st.success(f"✅ {pt_qty} × {chosen_name} SELL @ ₹{pt_price:,.2f} | P&L: {emoji} {pnl_str}")
            st.toast(f"🔴 SELL executed: {pt_qty} shares of {chosen_name}! P&L: {pnl_str}", icon="✅")
            st.rerun()

    st.markdown("---")

    # ── Position Sizing Calculator expander ──
    with st.expander("🎯 Position Sizing Calculator — kितne shares kharidne chahiye?", expanded=False):
        st.caption("Apna risk tolerance aur stop-loss daalo — calculator batayega sahi quantity, "
                   "taaki stop-loss hit hone par bhi loss aapki limit ke andar rahe.")

        psc_c1, psc_c2 = st.columns(2)
        with psc_c1:
            psc_capital = st.number_input(
                "Total Capital (₹)", min_value=1.0,
                value=round(st.session_state.pt_cash + sum(
                    h["shares"] * h["avg_price"] for h in st.session_state.pt_holdings.values()
                ), 2),
                step=10000.0, key="psc_capital",
                help="Default: net worth (cash + invested)."
            )
        with psc_c2:
            psc_risk_pct = st.slider(
                "Risk per trade (%)", min_value=0.5, max_value=10.0, value=5.0, step=0.5,
                key="psc_risk_pct"
            )

        psc_c3, psc_c4 = st.columns(2)
        with psc_c3:
            psc_entry = st.number_input(
                "Entry Price (₹)", min_value=0.01,
                value=float(pt_price) if pt_price else 100.0,
                step=0.05, key="psc_entry"
            )
        with psc_c4:
            psc_default_sl = round(psc_entry * 0.95, 2) if psc_entry else 95.0
            psc_stoploss = st.number_input(
                "Stop-Loss Price (₹)", min_value=0.01,
                value=psc_default_sl, step=0.05, key="psc_stoploss"
            )

        psc_risk_amount    = psc_capital * (psc_risk_pct / 100)
        psc_risk_per_share = psc_entry - psc_stoploss

        if psc_risk_per_share <= 0:
            st.error("❌ Stop-Loss Entry Price se kam hona chahiye (BUY ke liye).")
        else:
            psc_shares      = int(psc_risk_amount // psc_risk_per_share)
            psc_actual_cost = round(psc_shares * psc_entry, 2)
            psc_actual_risk = round(psc_shares * psc_risk_per_share, 2)
            psc_risk_of_cap = (psc_actual_risk / psc_capital * 100) if psc_capital else 0
            psc_sl_pct      = (psc_risk_per_share / psc_entry * 100) if psc_entry else 0

            if psc_shares == 0:
                st.warning("⚠️ Is risk amount mein 1 share bhi nahi ban raha — risk % badhao.")
            else:
                exceeds_cash = psc_actual_cost > st.session_state.pt_cash
                cash_note = (f'<div style="font-size:0.72rem;color:var(--danger-color);margin-top:8px;">'
                            f'⚠️ Available cash (₹{st.session_state.pt_cash:,.0f}) se zyada cost hai.</div>'
                            if exceeds_cash else "")
                st.markdown(f"""
                <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:14px;
                            padding:18px 20px; margin-top:10px;">
                  <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
                    <div>
                      <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">SHARES KHARIDO</div>
                      <div style="font-size:2.2rem; font-weight:900; color:var(--primary-blue); line-height:1.1;">{psc_shares:,}</div>
                      <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">stop-loss limits</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">TOTAL INVESTMENT</div>
                      <div style="font-size:1.3rem; font-weight:700; color:var(--text-color);">₹{psc_actual_cost:,.0f}</div>
                      <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">{(psc_actual_cost/psc_capital*100 if psc_capital else 0):.1f}% of capital</div>
                    </div>
                  </div>
                  <div style="height:1px; background:var(--row-border); margin:14px 0;"></div>
                  <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
                    <div>
                      <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">MAX RISK AMOUNT</div>
                      <div style="font-size:1.15rem; font-weight:700; color:var(--danger-color);">▼ ₹{psc_actual_risk:,.0f}</div>
                      <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">= {psc_risk_of_cap:.2f}% net worth</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">STOP-LOSS GAP</div>
                      <div style="font-size:1.15rem; font-weight:700; color:var(--text-color);">₹{psc_risk_per_share:,.2f}</div>
                      <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">{psc_sl_pct:.2f}% below entry</div>
                    </div>
                  </div>
                  {cash_note}
                </div>
                """, unsafe_allow_html=True)

                if st.button("📋 Yeh Qty Order Form mein bhar do", key="psc_fill_qty", use_container_width=True):
                    st.session_state._psc_pending_qty = psc_shares
                    st.rerun()

    # ── Averaging Calculator expander ──
    with st.expander("📉 Averaging Calculator — naya average price kya hoga?", expanded=False):
        st.caption("Loss mein chal rahe stock mein aur shares lekar average kam karne ka calculator.")
        _existing = st.session_state.pt_holdings.get(chosen_ticker)

        avg_c1, avg_c2 = st.columns(2)
        with avg_c1:
            avg_old_qty = st.number_input(
                "Purani Qty", min_value=0,
                value=int(_existing["shares"]) if _existing else 0,
                step=1, key="avg_old_qty"
            )
        with avg_c2:
            avg_old_price = st.number_input(
                "Purana Avg Price (₹)", min_value=0.0,
                value=float(_existing["avg_price"]) if _existing else 0.0,
                step=0.05, key="avg_old_price"
            )

        avg_c3, avg_c4 = st.columns(2)
        with avg_c3:
            avg_new_qty = st.number_input("Nayi Qty", min_value=1, value=100, step=1, key="avg_new_qty")
        with avg_c4:
            avg_new_price = st.number_input(
                "Naye Price (₹)", min_value=0.01,
                value=float(pt_price) if pt_price else 100.0,
                step=0.05, key="avg_new_price"
            )

        avg_total_qty = avg_old_qty + avg_new_qty
        avg_old_inv   = avg_old_qty * avg_old_price
        avg_new_inv   = avg_new_qty * avg_new_price
        avg_total_inv = avg_old_inv + avg_new_inv
        avg_new_avg   = (avg_total_inv / avg_total_qty) if avg_total_qty else 0

        avg_change      = avg_new_avg - avg_old_price if avg_old_qty else None
        avg_cur_price   = float(pt_price) if pt_price else avg_new_price
        avg_breakeven_pct = ((avg_new_avg - avg_cur_price) / avg_cur_price * 100) if avg_cur_price else 0

        avg_color = "var(--success-color)" if (avg_change is not None and avg_change < 0) else "var(--danger-color)"
        exceeds_cash_avg = avg_new_inv > st.session_state.pt_cash
        cash_note_avg = (f'<div style="font-size:0.72rem;color:var(--danger-color);margin-top:8px;">'
                        f'⚠️ Available cash (₹{st.session_state.pt_cash:,.0f}) se zyada average cost hai.</div>'
                        if exceeds_cash_avg else "")

        st.markdown(f"""
        <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:14px;
                    padding:18px 20px; margin-top:10px;">
          <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">NAYA AVERAGE PRICE</div>
              <div style="font-size:2.2rem; font-weight:900; color:#a78bfa; line-height:1.1;">₹{avg_new_avg:,.2f}</div>
              <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">
                {f"purana ₹{avg_old_price:,.2f} se {avg_color_word(avg_change)}" if avg_change is not None else "nayi position"}
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">TOTAL QTY (baad mein)</div>
              <div style="font-size:1.3rem; font-weight:700; color:var(--text-color);">{avg_total_qty:,}</div>
              <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">shares</div>
            </div>
          </div>
          <div style="height:1px; background:var(--row-border); margin:14px 0;"></div>
          <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">ADDITIONAL INVESTMENT</div>
              <div style="font-size:1.15rem; font-weight:700; color:var(--text-color);">₹{avg_new_inv:,.0f}</div>
              <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">{avg_new_qty:,} shares @ ₹{avg_new_price:,.2f}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">TOTAL INVESTMENT (baad mein)</div>
              <div style="font-size:1.15rem; font-weight:700; color:var(--text-color);">₹{avg_total_inv:,.0f}</div>
              <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">{avg_total_qty:,} shares @ avg ₹{avg_new_avg:,.2f}</div>
            </div>
          </div>
          <div style="height:1px; background:var(--row-border); margin:14px 0;"></div>
          <div>
            <div style="font-size:0.62rem; color:var(--secondary-text); font-weight:700; letter-spacing:.08em;">BREAKEVEN TAK DISTANCE</div>
            <div style="font-size:1.15rem; font-weight:700; color:{'var(--success-color)' if avg_breakeven_pct<=0 else 'var(--danger-color)'};">
              {'Already in profit' if avg_breakeven_pct<=0 else f'+{avg_breakeven_pct:.2f}%'}
            </div>
            <div style="font-size:0.72rem; color:var(--secondary-text); margin-top:2px;">
              Current price ₹{avg_cur_price:,.2f} se naye average ₹{avg_new_avg:,.2f} tak
            </div>
          </div>
          {cash_note_avg}
        </div>
        """, unsafe_allow_html=True)

    # ── Main Tabs menu ──
    open_tab, exec_tab, gtt_tab, basket_tab = st.tabs(["📋 Open", "✅ Executed", "⏱ GTT", "🧺 Baskets"])

    # ── Tab 1: Open ──
    with open_tab:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:var(--muted-text);
                    background:var(--card-bg); border:1px dashed var(--border-color); border-radius:16px; margin:10px 0;">
          <div style="font-size:3rem; margin-bottom:10px;">📋</div>
          <div style="font-size:1.1rem; font-weight:600; color:var(--text-color);">No pending market orders</div>
          <div style="font-size:0.82rem; margin-top:6px; color:var(--secondary-text);">Paper trading execution is instantaneous. Active limit targets are logged under the GTT tab.</div>
        </div>""", unsafe_allow_html=True)

    # ── Tab 2: Executed ──
    with exec_tab:
        if st.session_state.pt_history:
            # Filters & Search layout row
            sf_c1, sf_c2, sf_c3, sf_c4 = st.columns([1.8, 1.0, 1.0, 1.0])
            with sf_c1:
                search_q = st.text_input("Search Stock", placeholder="Search ticker/name...", key="exec_search_widget", label_visibility="collapsed").strip().lower()
            with sf_c2:
                action_f = st.selectbox("Action Filter", ["ALL", "BUY", "SELL"], key="exec_action_widget", label_visibility="collapsed")
            with sf_c3:
                sort_f = st.selectbox("Sort Ordering", ["Newest first", "Oldest first", "Highest Value", "Lowest Value"], key="exec_sort_widget", label_visibility="collapsed")
            with sf_c4:
                import pandas as pd
                df_history = pd.DataFrame(st.session_state.pt_history)
                csv_bytes = df_history.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export CSV", data=csv_bytes, file_name="transaction_ledger.csv", mime="text/csv", key="exec_csv_export", use_container_width=True)

            # Apply filters
            filtered_history = []
            for t in st.session_state.pt_history:
                name_match = search_q in t.get("Name", "").lower() or search_q in t.get("Ticker", "").lower()
                action_match = (action_f == "ALL" or t["Action"] == action_f)
                if name_match and action_match:
                    filtered_history.append(t)

            # Apply sorting
            if sort_f == "Newest first":
                filtered_history = list(reversed(filtered_history))
            elif sort_f == "Oldest first":
                pass
            elif sort_f == "Highest Value":
                filtered_history = sorted(filtered_history, key=lambda x: x.get("Value", 0), reverse=True)
            elif sort_f == "Lowest Value":
                filtered_history = sorted(filtered_history, key=lambda x: x.get("Value", 0))

            if not filtered_history:
                st.markdown("""
                <div style="text-align:center; padding:40px; color:var(--muted-text);">
                  <div style="font-size:2.5rem; margin-bottom:8px;">🔍</div>
                  <div style="font-weight:600; color:var(--text-color);">No matching executions found</div>
                  <div style="font-size:0.8rem;">Change your filters or search keyword</div>
                </div>""", unsafe_allow_html=True)
            else:
                # Pagination
                import math
                orders_per_page = 10
                total_pages = math.ceil(len(filtered_history) / orders_per_page)
                if "exec_page_idx" not in st.session_state:
                    st.session_state.exec_page_idx = 1
                if st.session_state.exec_page_idx > total_pages:
                    st.session_state.exec_page_idx = 1

                start_idx = (st.session_state.exec_page_idx - 1) * orders_per_page
                end_idx = start_idx + orders_per_page
                page_history = filtered_history[start_idx:end_idx]

                # Side-by-side: Table (left) and Timeline (right)
                tab_col, time_col = st.columns([2.1, 1.0])

                with tab_col:
                    table_rows = ""
                    for t in page_history:
                        action_badge = f'<span class="badge-buy">BUY</span>' if t["Action"] == "BUY" else f'<span class="badge-sell">SELL</span>'
                        pnl_td = ""
                        if t.get("P&L") is not None:
                            p_color = "var(--success-color)" if t["P&L"] >= 0 else "var(--danger-color)"
                            pnl_td = f'<span style="color:{p_color}; font-weight:700;">₹{t["P&L"]:+,.2f}</span>'
                        else:
                            pnl_td = '<span style="color:var(--muted-text);">—</span>'
                        
                        ticker_clean = t['Ticker'].replace('.NS','')
                        table_rows += f"""<tr>
<td><b style="color:var(--text-color);">{t.get('Name', ticker_clean)}</b><br><span style="font-size:0.7rem; color:var(--secondary-text);">{ticker_clean}</span></td>
<td>{action_badge}</td>
<td>{t['Shares']}</td>
<td>₹{t['Price']:,.2f}</td>
<td>₹{t['Value']:,.2f}</td>
<td>{pnl_td}</td>
<td style="font-size:0.75rem; color:var(--secondary-text);">{t['Time']}</td>
</tr>"""

                    st.markdown(f"""<div class="table-container">
<table class="premium-table">
<thead>
<tr>
<th>Stock</th>
<th>Action</th>
<th>Shares</th>
<th>Price</th>
<th>Value</th>
<th>Realised P&L</th>
<th>Execution Time</th>
</tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>""", unsafe_allow_html=True)

                    # Pagination Controls
                    if total_pages > 1:
                        p1, p2, p3 = st.columns([1, 2, 1])
                        with p1:
                            if st.button("⬅️ Previous Page", disabled=(st.session_state.exec_page_idx == 1), key="prev_exec_btn", use_container_width=True):
                                st.session_state.exec_page_idx -= 1
                                st.rerun()
                        with p2:
                            st.markdown(f"<div style='text-align:center; font-size:0.8rem; color:var(--secondary-text); margin-top:8px;'>Page {st.session_state.exec_page_idx} of {total_pages}</div>", unsafe_allow_html=True)
                        with p3:
                            if st.button("Next Page ➡️", disabled=(st.session_state.exec_page_idx == total_pages), key="next_exec_btn", use_container_width=True):
                                st.session_state.exec_page_idx += 1
                                st.rerun()

                with time_col:
                    timeline_nodes = ""
                    for t in page_history[:8]:
                        dot_color = "var(--success-color)" if t["Action"] == "BUY" else "var(--danger-color)"
                        pnl_detail = ""
                        if t.get("P&L") is not None:
                            p_color = "var(--success-color)" if t["P&L"] >= 0 else "var(--danger-color)"
                            pnl_detail = f'<div style="font-size:0.72rem; color:{p_color}; font-weight:700; margin-top:3px;">P&L: ₹{t["P&L"]:+,.2f}</div>'
                        
                        timeline_nodes += f"""<div class="timeline-node">
<div class="timeline-dot" style="background:{dot_color};"></div>
<div class="timeline-card">
<div style="display:flex; justify-content:space-between; align-items:flex-start;">
<span style="font-size:0.78rem; font-weight:800; color:var(--text-color);">{t.get('Name', t['Ticker'].replace('.NS',''))}</span>
<span style="font-size:0.65rem; font-weight:700; color:{dot_color}; background:{dot_color}12; padding:1px 6px; border-radius:4px;">{t['Action']}</span>
</div>
<div style="font-size:0.7rem; color:var(--secondary-text); margin-top:4px;">
{t['Shares']} shares @ ₹{t['Price']:,.2f}
</div>
<div style="font-size:0.62rem; color:var(--muted-text); margin-top:2px;">🕐 {t['Time']}</div>
{pnl_detail}
</div>
</div>"""

                    st.markdown(f"""<div style="font-size:0.72rem; font-weight:800; color:var(--muted-text); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px; margin-top:2px;">🕒 Transaction Audit</div>
<div class="timeline-wrap">
{timeline_nodes}
</div>""", unsafe_allow_html=True)

            # Clear History Action
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Clear History", key="clear_hist", type="secondary", use_container_width=True):
                st.session_state.pt_history = []
                st.toast("🗑️ Transaction history has been reset.", icon="ℹ️")
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center; padding:60px 20px; color:var(--muted-text);
                        background:var(--card-bg); border:1px dashed var(--border-color); border-radius:16px; margin:10px 0;">
              <div style="font-size:3.5rem; margin-bottom:10px;">✅</div>
              <div style="font-size:1.1rem; font-weight:600; color:var(--text-color);">No executed orders</div>
              <div style="font-size:0.82rem; margin-top:6px; color:var(--secondary-text);">Completed trades will appear here as a premium timeline audit.</div>
            </div>""", unsafe_allow_html=True)

    # ── Tab 3: GTT ──
    with gtt_tab:
        st.caption("Target laga do — price hit hone par automatically BUY/SELL ho jayega. "
                   "Aaj 3:30 PM tak hit nahi hua to target khud cancel ho jayega.")

        if not is_market_open():
            st.warning("⏱ Market band hai. Naya target sirf market open hours (9:15 AM – 3:30 PM, Mon–Fri) mein laga sakte ho.")
        else:
            with st.form("place_target_form", clear_on_submit=True):
                gtt_name = st.selectbox("Stock", options=wl_names, index=def_idx, key="gtt_stock_select")
                gtt_ticker = wl_tickers[wl_names.index(gtt_name)]

                gc1, gc2, gc3 = st.columns(3)
                with gc1:
                    gtt_action = st.selectbox("Action", ["BUY", "SELL"], key="gtt_action")
                with gc2:
                    gtt_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="gtt_qty")
                with gc3:
                    gtt_target_price = st.number_input("Target Price (₹)", min_value=0.01, value=100.0, step=0.05, key="gtt_target_price")

                gtt_submit = st.form_submit_button("⏱ Place Target Order", type="primary", use_container_width=True)

            if gtt_submit:
                gq = get_index_quote(gtt_ticker)
                cur_p = gq[0] if gq else None
                if gtt_action == "SELL":
                    owned = st.session_state.pt_holdings.get(gtt_ticker, {}).get("shares", 0)
                    if owned < gtt_qty:
                        st.error(f"❌ {gtt_name} ke sirf {owned} shares hain, {gtt_qty} sell target nahi laga sakte.")
                        st.toast("❌ Target Placement Failed", icon="❌")
                    else:
                        st.session_state.pt_targets.append({
                            "ticker": gtt_ticker, "name": gtt_name, "action": "SELL",
                            "qty": gtt_qty, "target_price": gtt_target_price,
                            "placed_date": ist_now().strftime("%Y-%m-%d"),
                            "placed_time": ist_now().strftime("%I:%M %p"),
                        })
                        save_portfolio()
                        st.success(f"✅ SELL target lag gaya: {gtt_qty} × {gtt_name} @ ₹{gtt_target_price:,.2f}")
                        st.toast(f"⏱ GTT SELL Target placed for {gtt_name}!", icon="✅")
                        st.rerun()
                else:  # BUY
                    est_cost = gtt_target_price * gtt_qty
                    if est_cost > st.session_state.pt_cash:
                        st.error(f"❌ Balance kam hai! Target hit hone par chahiye ₹{est_cost:,.2f}, hai ₹{st.session_state.pt_cash:,.0f}")
                        st.toast("❌ Target Placement Failed: Insufficient cash", icon="❌")
                    else:
                        st.session_state.pt_targets.append({
                            "ticker": gtt_ticker, "name": gtt_name, "action": "BUY",
                            "qty": gtt_qty, "target_price": gtt_target_price,
                            "placed_date": ist_now().strftime("%Y-%m-%d"),
                            "placed_time": ist_now().strftime("%I:%M %p"),
                        })
                        save_portfolio()
                        st.success(f"✅ BUY target lag gaya: {gtt_qty} × {gtt_name} @ ₹{gtt_target_price:,.2f}")
                        st.toast(f"⏱ GTT BUY Target placed for {gtt_name}!", icon="✅")
                        st.rerun()

        st.markdown("---")

        # ── Pending targets list ──
        today_targets = [t for t in st.session_state.pt_targets
                          if t["placed_date"] == ist_now().strftime("%Y-%m-%d")]

        if today_targets:
            st.markdown('<div class="sec-title">PENDING TARGET ORDERS (aaj ke liye)</div>', unsafe_allow_html=True)
            
            # Use clean layout table structure
            for idx, t in enumerate(today_targets):
                gq = get_index_quote(t["ticker"])
                live_p = gq[0] if gq else None
                live_str = f"₹{live_p:,.2f}" if live_p is not None else "—"
                badge_style = "background:rgba(22,163,74,0.12); color:var(--success-color); border:1px solid rgba(22,163,74,0.2);" if t["action"] == "BUY" else "background:rgba(220,38,38,0.1); color:var(--danger-color); border:1px solid rgba(220,38,38,0.2);"
                
                tr_col1, tr_col2, tr_col3 = st.columns([4, 2, 1])
                with tr_col1:
                    st.markdown(f"""
                    <div style="padding:10px 0;">
                        <span style="font-size:0.65rem; font-weight:700; border-radius:4px; padding:2px 6px; {badge_style}">{t['action']}</span>
                        &nbsp; <b style="font-size:0.9rem; color:var(--text-color);">{t['name']}</b>
                        <div style="font-size:0.75rem; color:var(--secondary-text); margin-top:3px;">
                            {t['qty']} shares · Target price: ₹{t['target_price']:,.2f} · Placed at {t['placed_time']}
                        </div>
                    </div>""", unsafe_allow_html=True)
                with tr_col2:
                    st.markdown(f"""
                    <div style="padding:10px 0; text-align:right;">
                        <span style="font-size:0.75rem; color:var(--muted-text);">Live Price</span>
                        <div style="font-size:0.9rem; font-weight:700; color:var(--text-color);">{live_str}</div>
                    </div>""", unsafe_allow_html=True)
                with tr_col3:
                    st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
                    if st.button("❌ Cancel", key=f"cancel_gtt_{idx}", use_container_width=True):
                        st.session_state.pt_targets.remove(t)
                        st.session_state.cancelled_orders_count = st.session_state.get("cancelled_orders_count", 0) + 1
                        save_portfolio()
                        st.toast(f"❌ Cancelled GTT target: {t['name']}", icon="ℹ️")
                        st.rerun()
                        
            st.caption("Auto-refresh ON — har 30 second mein price check hoga jab tak market open hai.")

            if is_market_open():
                _gtt_elapsed = time.time() - st.session_state.get("_ar_gtt", 0)
                if _gtt_elapsed >= 30:
                    st.session_state["_ar_gtt"] = time.time()
                    get_index_quote.clear()
                    st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center; padding:60px 20px; color:var(--muted-text);
                        background:var(--card-bg); border:1px dashed var(--border-color); border-radius:16px; margin:10px 0;">
              <div style="font-size:3rem; margin-bottom:10px;">⏱</div>
              <div style="font-size:1.1rem; font-weight:600; color:var(--text-color);">No GTT orders</div>
              <div style="font-size:0.82rem; margin-top:6px; color:var(--secondary-text);">Good Till Triggered targets will appear here.</div>
            </div>""", unsafe_allow_html=True)

    # ── Tab 4: Baskets ──
    with basket_tab:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:var(--muted-text);
                    background:var(--card-bg); border:1px dashed var(--border-color); border-radius:16px; margin:10px 0;">
          <div style="font-size:3rem; margin-bottom:10px;">🧺</div>
          <div style="font-size:1.1rem; font-weight:600; color:var(--text-color);">No active baskets</div>
          <div style="font-size:0.82rem; margin-top:6px; color:var(--secondary-text);">Multi-stock trading bundles can be created in Phase 11.</div>
        </div>""", unsafe_allow_html=True)

    # ── Position Calculator (Task 3) ──
    st.markdown("---")
    st.markdown('<div class="sec-title">🎯 POSITION CALCULATOR (P&L & CHARGES)</div>', unsafe_allow_html=True)
    st.caption("Calculate exact trade charges, net realization, and break-even targets before entering a position. This calculator does not impact your portfolio or cash balance.")

    calc_c1, calc_c2, calc_c3, calc_c4 = st.columns(4)
    with calc_c1:
        calc_buy = st.number_input("Buy Price (₹)", min_value=0.01, value=100.0, step=1.0, key="calc_buy_price")
    with calc_c2:
        calc_sell = st.number_input("Sell Price (₹)", min_value=0.01, value=110.0, step=1.0, key="calc_sell_price")
    with calc_c3:
        calc_qty = st.number_input("Quantity", min_value=1, value=100, step=10, key="calc_qty_shares")
    with calc_c4:
        calc_brokerage = st.number_input("Brokerage (₹)", min_value=0.0, value=0.0, step=1.0, key="calc_brokerage_val", help="Total brokerage (buy + sell sides combined)")

    # Computations
    buy_val = calc_buy * calc_qty
    sell_val = calc_sell * calc_qty
    
    # Buy side charges
    buy_stt = buy_val * 0.001
    buy_exch = buy_val * 0.0000345
    buy_sebi = buy_val * 0.000001
    buy_stamp = buy_val * 0.00015
    buy_brokerage = calc_brokerage / 2
    buy_gst = (buy_exch + buy_sebi + buy_brokerage) * 0.18
    buy_charges = buy_stt + buy_exch + buy_sebi + buy_stamp + buy_gst + buy_brokerage
    total_investment = buy_val + buy_charges

    # Sell side charges
    sell_stt = sell_val * 0.001
    sell_exch = sell_val * 0.0000345
    sell_sebi = sell_val * 0.000001
    sell_brokerage = calc_brokerage / 2
    sell_gst = (sell_exch + sell_sebi + sell_brokerage) * 0.18
    sell_dp = 15.93 if sell_val > 0 else 0.0
    sell_charges = sell_stt + sell_exch + sell_sebi + sell_gst + sell_dp + sell_brokerage

    # Summed charges
    brokerage = calc_brokerage
    stt = buy_stt + sell_stt
    exch = buy_exch + sell_exch
    sebi = buy_sebi + sell_sebi
    gst = buy_gst + sell_gst
    stamp = buy_stamp
    dp = sell_dp
    total_charges = buy_charges + sell_charges

    gross_pnl = (calc_sell - calc_buy) * calc_qty
    net_pnl = gross_pnl - total_charges
    roi = (net_pnl / total_investment * 100) if total_investment else 0.0
    break_even = calc_buy + (total_charges / calc_qty) if calc_qty else calc_buy

    # Styling colors
    pnl_color = "var(--success-color)" if gross_pnl >= 0 else "var(--danger-color)"
    pnl_sign = "+" if gross_pnl >= 0 else ""
    net_pnl_color = "var(--success-color)" if net_pnl >= 0 else "var(--danger-color)"
    net_pnl_sign = "+" if net_pnl >= 0 else ""

    st.markdown(f"""<div class="table-container" style="padding: 20px; border-top: 3px solid var(--primary-blue); margin-top: 15px;">
<div style="display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap;">
<!-- Left: Charges Table -->
<div style="flex: 1.2; min-width: 300px;">
<h4 style="margin-top: 0; color: var(--text-color); font-size: 0.95rem;">🧾 Charges Breakdown</h4>
<table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-color);">
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">Brokerage</td>
<td style="text-align: right; font-weight: 700;">₹{brokerage:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">STT (Securities Transaction Tax)</td>
<td style="text-align: right; font-weight: 700;">₹{stt:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">Exchange Transaction Charges</td>
<td style="text-align: right; font-weight: 700;">₹{exch:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">GST (18% on transaction + sebi)</td>
<td style="text-align: right; font-weight: 700;">₹{gst:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">SEBI Turnover Fees</td>
<td style="text-align: right; font-weight: 700;">₹{sebi:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">Stamp Duty (Buy side)</td>
<td style="text-align: right; font-weight: 700;">₹{stamp:,.2f}</td>
</tr>
<tr style="border-bottom: 1px solid var(--border-color); height: 32px;">
<td style="color: var(--secondary-text);">DP Charges (Sell side)</td>
<td style="text-align: right; font-weight: 700;">₹{dp:,.2f}</td>
</tr>
<tr style="height: 36px; font-weight: 800; border-top: 2px solid var(--border-color);">
<td style="color: var(--text-color);">Total Charges</td>
<td style="text-align: right; color: var(--danger-color);">₹{total_charges:,.2f}</td>
</tr>
</table>
</div>
<!-- Right: Metrics Cards -->
<div style="flex: 1; min-width: 280px; display: flex; flex-direction: column; gap: 12px;">
<div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; text-align: center;">
<div style="font-size: 0.68rem; color: var(--secondary-text); font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Total Investment</div>
<div style="font-size: 1.4rem; font-weight: 900; color: var(--text-color); margin-top: 4px;">₹{total_investment:,.2f}</div>
</div>

<div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; text-align: center; border-left: 4px solid {pnl_color};">
<div style="font-size: 0.68rem; color: var(--secondary-text); font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Gross Profit / Loss</div>
<div style="font-size: 1.4rem; font-weight: 900; color: {pnl_color}; margin-top: 4px;">{pnl_sign}₹{abs(gross_pnl):,.2f}</div>
</div>

<div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; text-align: center; border-left: 4px solid {net_pnl_color};">
<div style="font-size: 0.68rem; color: var(--secondary-text); font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Net Profit / Loss (after charges)</div>
<div style="font-size: 1.4rem; font-weight: 900; color: {net_pnl_color}; margin-top: 4px;">{net_pnl_sign}₹{abs(net_pnl):,.2f}</div>
<div style="font-size: 0.72rem; color: var(--secondary-text); margin-top: 4px;">ROI: <b style="color: {net_pnl_color};">{roi:+.2f}%</b></div>
</div>

<div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px; text-align: center;">
<div style="font-size: 0.68rem; color: var(--secondary-text); font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">Break Even Price</div>
<div style="font-size: 1.25rem; font-weight: 800; color: var(--primary-blue); margin-top: 4px;">₹{break_even:,.2f}</div>
<div style="font-size: 0.65rem; color: var(--muted-text); margin-top: 2px;">Required to cover total charges</div>
</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "portfolio":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    DARK_BG   = BG_COLOR
    # Using global theme variables for CARD_BG, BORDER, GREEN, RED, BLUE, TEXT, MUTED
    PIE_COLS  = [BLUE,"#a78bfa","#f59e0b","#10b981","#f43f5e",
                 "#06b6d4","#84cc16","#fb923c","#e879f9","#38bdf8"]

    # ── Header with Refresh ───────────────────────────────────────────────────
    pf_h, pf_r = st.columns([5, 1])
    with pf_h:
        st.markdown('<div class="sec-title">MY PORTFOLIO</div>', unsafe_allow_html=True)
    with pf_r:
        if st.button("🔄", key="portfolio_refresh", help="Prices refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            get_holdings_live_prices.clear()
            st.session_state["_ar_portfolio"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh only during market hours ────────────
    _pf_elapsed = time.time() - st.session_state.get("_ar_portfolio", 0)
    if _pf_elapsed >= _AUTO_REFRESH_SECS and is_market_open():
        get_index_quote.clear()
        get_batch_quotes.clear()
        get_holdings_live_prices.clear()
        st.session_state["_ar_portfolio"] = time.time()
        st.rerun()

    port_tab1, port_tab2, port_tab3 = st.tabs([
        "📋  Positions", "📈  Performance", "🛠️  Tools"
    ])

    # ── Build holdings data ───────────────────────────────────────────────────
    total_invested = sum(h["shares"] * h["avg_price"]
                         for h in st.session_state.pt_holdings.values())
    total_cur_val  = 0
    rows = []
    today_date = ist_now().date()

    # ── PERFORMANCE FIX: pehle sabhi holdings ka price EK HI batch call mein ────
    # ── le lo (yf.download se), taaki har holding ke liye alag-alag sequential ──
    # ── network call na lagani pade — yahi Portfolio tab ke load hone mein ──────
    # ── sabse bada slowdown tha (10 holdings = 10 separate calls pehle) ─────────
    _holding_tickers = tuple(st.session_state.pt_holdings.keys())
    _price_batch = get_indices_batch(_holding_tickers) if _holding_tickers else {}

    for tkr, h in st.session_state.pt_holdings.items():
        q     = _price_batch.get(tkr)
        cur_p = q[0] if q else h["avg_price"]
        inv   = h["shares"] * h["avg_price"]
        cur_v = h["shares"] * cur_p
        pnl   = cur_v - inv
        pnl_p = (pnl / inv * 100) if inv else 0
        total_cur_val += cur_v
        name_disp = dict(st.session_state.custom_watchlist).get(tkr, tkr.replace(".NS",""))

        # ── Holding period — buy date se aaj tak ke din, LTCG/STCG ke liye ──────
        fb_date_str = h.get("first_buy_date")
        if fb_date_str:
            try:
                fb_date    = datetime.strptime(fb_date_str, "%Y-%m-%d").date()
                held_days  = (today_date - fb_date).days
                term_label = "Long Term" if held_days > 365 else "Short Term"
            except Exception:
                held_days, term_label = None, None
        else:
            held_days, term_label = None, None  # purani holding — date track nahi hui thi

        rows.append({"ticker": tkr, "name": name_disp, "shares": h["shares"],
                     "avg": h["avg_price"], "cur": cur_p,
                     "inv": inv, "cur_v": cur_v, "pnl": pnl, "pnl_p": pnl_p,
                     "held_days": held_days, "term_label": term_label})

    total_pnl = total_cur_val - total_invested
    total_pct = (total_pnl / total_invested * 100) if total_invested else 0
    net_worth = st.session_state.pt_cash + total_cur_val
    pnl_color = GREEN if total_pnl >= 0 else RED

    # ── Day's P&L — prev close se calculate ──────────────────────────────────
    # ── PERMANENT PERF FIX: pehle yahan har holding ke liye alag, bina-cache ────
    # ── yfinance.Ticker().info call hoti thi — isliye Portfolio tab khulne mein ─
    # ── bahut time lagta tha. Ab ek shared CACHED function (60s TTL) se ek baar ─
    # ── mein sab holdings ka data aata hai — Home tab bhi isi cache ko reuse ────
    # ── karta hai, isliye dono jagah fast + consistent rehta hai. ──────────────
    # ── 9:15 AM se pehle (market khulne wala hai) — Day's P&L force ₹0 rakho, ───
    # ── kyunki aaj abhi tak koi trading hui hi nahi hai. ──────────────────────────
    _pf_now = ist_now()
    _pf_market_open_time = _pf_now.replace(hour=9, minute=15, second=0, microsecond=0)
    _pf_pre_market = _pf_now < _pf_market_open_time

    _holdings_tuple = tuple(
        (tkr, h["shares"], h["avg_price"]) for tkr, h in st.session_state.pt_holdings.items()
    )
    _live_prices = get_holdings_live_prices(_holdings_tuple)

    day_pnl = 0.0
    prev_total_val = 0.0
    total_cur_val = 0.0
    for r in rows:
        try:
            _live = _live_prices.get(r["ticker"], {})
            prev_c = _live.get("prev_close") or r["cur"]
            live_c = _live.get("live_price") or prev_c or r["cur"]

            # Current price ko reliable source se refresh karo
            r["cur"]   = live_c
            r["cur_v"] = live_c * r["shares"]
            r["pnl"]   = r["cur_v"] - r["inv"]
            r["pnl_p"] = (r["pnl"] / r["inv"] * 100) if r["inv"] else 0

            if _pf_pre_market:
                r["day_pnl"] = 0.0
                r["day_pct"] = 0.0
            else:
                r_day_pnl = (live_c - prev_c) * r["shares"]
                r["day_pnl"] = r_day_pnl
                r["day_pct"] = ((live_c - prev_c) / prev_c * 100) if prev_c else 0
                day_pnl += r_day_pnl
            prev_total_val += prev_c * r["shares"]
        except Exception:
            r["day_pnl"] = 0.0
            r["day_pct"] = 0.0
            prev_total_val += r["cur"] * r["shares"]
        total_cur_val += r["cur_v"]

    # Refreshed cur_v ke hisaab se totals bhi recompute karo
    total_pnl = total_cur_val - total_invested
    total_pct = (total_pnl / total_invested * 100) if total_invested else 0

    # ── Sabse zyada profit wala holding sabse upar — phir descending order mein ─
    rows = sorted(rows, key=lambda r: r["pnl"], reverse=True)

    day_color = GREEN if day_pnl >= 0 else RED
    day_arrow = "▲" if day_pnl >= 0 else "▼"
    tot_arrow = "▲" if total_pnl >= 0 else "▼"
    day_pct   = (day_pnl / prev_total_val * 100) if prev_total_val else 0

    # ── Sort holdings: sabse zyada (overall) profit wala sabse upar, ──────────
    # ── phir profit kam hote hote loss tak neeche ─────────────────────────────
    rows.sort(key=lambda r: r["pnl"], reverse=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 🔥 STREAK TRACKER + ☀️ AAJ KA TRADE CARD — Portfolio ke upar
    # ══════════════════════════════════════════════════════════════════════════

    # ── Streak calculate karo (consecutive profitable trade days) ─────────────

    streak, profitable_days, total_trade_days = calculate_streak(st.session_state.pt_history)

    # ── Streak Emoji ──────────────────────────────────────────────────────────
    if streak >= 10:
        streak_emoji = "🔥🔥🔥"
        streak_color = "#f59e0b"
        streak_bg    = "#1a1200"
        streak_border= "#f59e0b"
        streak_label = "LEGENDARY STREAK"
    elif streak >= 5:
        streak_emoji = "🔥🔥"
        streak_color = "#fb923c"
        streak_bg    = "#1a0e00"
        streak_border= "#fb923c"
        streak_label = "HOT STREAK"
    elif streak >= 2:
        streak_emoji = "🔥"
        streak_color = "#f59e0b"
        streak_bg    = "#1a1200"
        streak_border= "#f59e0b"
        streak_label = "STREAK ON"
    elif streak == 1:
        streak_emoji = "✅"
        streak_color = "#27ae60"
        streak_bg    = "#051a0a"
        streak_border= "#27ae60"
        streak_label = "STREAK START"
    else:
        streak_emoji = "😴"
        streak_color = "#8b90a0"
        streak_bg    = "#1a1d27"
        streak_border= "#2a2d3a"
        streak_label = "NO STREAK YET"

    win_rate_disp = f"{profitable_days}/{total_trade_days} profitable days" if total_trade_days else "Abhi koi trade nahi"

    # ── Aaj Ka Trade card ─────────────────────────────────────────────────────
    if rows or st.session_state.pt_history:
        insight_emoji, insight_text = get_aaj_ka_trade_insight(rows, st.session_state.pt_history, streak)
    else:
        insight_emoji = "💡"
        insight_text  = "Apni pehli trade karo — watchlist se koi stock chunno aur BUY dabao!"

    # Render — only if portfolio tab is active (already inside elif tab == "portfolio")
    col_insight, col_streak = st.columns([3, 2])

    with col_insight:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0d1626,#1a1d27);
                    border:1px solid #3b82f655;border-radius:16px;
                    padding:16px 18px;margin-bottom:14px;position:relative;overflow:hidden;">
          <div style="position:absolute;top:-10px;right:-10px;font-size:5rem;opacity:0.06;">☀️</div>
          <div style="font-size:0.62rem;font-weight:800;color:#3b82f6;letter-spacing:.12em;margin-bottom:8px;">
            ☀️ AAJ KA TRADE INSIGHT
          </div>
          <div style="display:flex;align-items:flex-start;gap:10px;">
            <div style="font-size:1.6rem;line-height:1;">{insight_emoji}</div>
            <div style="font-size:0.9rem;color:#e8eaf0;line-height:1.55;">{insight_text}</div>
          </div>
          <div style="font-size:0.62rem;color:#3a3f52;margin-top:10px;text-align:right;">
            📅 {ist_now().strftime("%d %b %Y")} — roz naya insight!
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_streak:
        st.markdown(f"""
        <div style="background:{streak_bg};border:1.5px solid {streak_border}55;
                    border-radius:16px;padding:16px 18px;margin-bottom:14px;
                    border-top:3px solid {streak_border};text-align:center;">
          <div style="font-size:0.62rem;font-weight:800;color:{streak_color};
                      letter-spacing:.12em;margin-bottom:6px;">{streak_label}</div>
          <div style="font-size:3rem;line-height:1;margin-bottom:4px;">{streak_emoji}</div>
          <div style="font-size:2rem;font-weight:900;color:{streak_color};line-height:1;">
            {streak}
          </div>
          <div style="font-size:0.72rem;color:#8b90a0;margin-top:4px;">
            consecutive profitable days
          </div>
          <div style="font-size:0.68rem;color:{streak_color};margin-top:8px;
                      background:{streak_color}15;border-radius:8px;padding:4px 8px;">
            {win_rate_disp}
          </div>
        </div>
        """, unsafe_allow_html=True)

    if rows:
        # ══════════════════════════════════════════════════════════════════════
        with port_tab1:
            # ══════════════════════════════════════════════════════════════════════
            # 🔔 RESULT TODAY NOTIFICATION — sirf un holdings ke liye jinka
            # result AAJ hi hai (yfinance se exact earnings date try karte hain;
            # zyadatar smallcap stocks ke liye data nahi milega — silently skip)
            # ══════════════════════════════════════════════════════════════════════
            _today_results = get_holdings_results_today(tuple(r["ticker"] for r in rows))
            if _today_results:
                _names_today = [r["name"] for r in rows if r["ticker"] in _today_results]
                st.markdown(f"""
                <div style="background:#0d1f12;border:1px solid #27ae6055;border-left:4px solid #27ae60;
                            border-radius:10px;padding:14px 18px;margin-bottom:16px;
                            display:flex;align-items:flex-start;gap:12px;">
                  <div style="font-size:1.4rem;line-height:1;">🔔</div>
                  <div>
                    <div style="font-size:0.88rem;font-weight:700;color:#e8eaf0;">
                      Aaj result hai: {', '.join(_names_today)}
                    </div>
                    <div style="font-size:0.78rem;color:#8b90a0;margin-top:4px;">
                      Aapki holding mein se is stock ka quarterly result aaj announce ho sakta hai —
                      price movement expect karo.
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # SECTION A — Zerodha Style Holdings List (full width)
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">HOLDINGS</div>', unsafe_allow_html=True)

            # Column headers
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1.8fr 0.6fr 1.1fr 0.9fr 1fr 1fr 1.1fr 1.1fr;
                        gap:8px;padding:8px 14px;
                        background:{DARK_BG};border-radius:8px 8px 0 0;
                        border:1px solid {BORDER};border-bottom:none;margin-bottom:0;">
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">STOCK</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">QTY</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">HELD FOR</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">AVG COST</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">LTP</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">CUR. VAL</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">DAY'S P&L</div>
              <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">TOTAL P&L</div>
            </div>""", unsafe_allow_html=True)

            hold_html = ""
            for i, r in enumerate(rows):
                pnl_c  = GREEN if r["pnl"] >= 0 else RED
                arrow  = "▲" if r["pnl"] >= 0 else "▼"
                day_p  = r.get("day_pnl", 0.0)
                day_pc = r.get("day_pct", 0.0)
                day_c  = GREEN if day_p >= 0 else RED
                day_ar = "▲" if day_p >= 0 else "▼"
                bg     = CARD_BG if i % 2 == 0 else f"rgba(255,255,255,0.02)"
                border_r = "0 0 8px 8px" if i == len(rows)-1 else "0"

                # Holding period badge
                held_days  = r.get("held_days")
                term_label = r.get("term_label")
                if held_days is not None:
                    term_c = "#a78bfa" if term_label == "Long Term" else "#f59e0b"
                    held_html = (f'<div style="font-size:0.82rem;font-weight:600;color:{TEXT};">{held_days}d</div>'
                                 f'<div style="font-size:0.62rem;color:{term_c};margin-top:1px;font-weight:600;">{term_label}</div>')
                else:
                    held_html = f'<div style="font-size:0.78rem;color:{MUTED};">—</div>'

                hold_html += f"""
                <div style="display:grid;grid-template-columns:1.8fr 0.6fr 1.1fr 0.9fr 1fr 1fr 1.1fr 1.1fr;
                            gap:8px;padding:12px 14px;
                            background:{bg};
                            border:1px solid {BORDER};border-top:none;
                            border-radius:{border_r};">
                  <div>
                    <div style="font-size:0.88rem;font-weight:700;color:{TEXT};">{r['name']}</div>
                    <div style="font-size:0.68rem;color:{MUTED};margin-top:2px;">Invested ₹{r['inv']:,.0f}</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">{r['shares']}</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    {held_html}
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;color:{MUTED};">₹{r['avg']:,.2f}</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">₹{r['cur']:,.2f}</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">₹{r['cur_v']:,.0f}</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:700;color:{day_c};">
                      {day_ar} ₹{abs(day_p):,.0f}
                    </div>
                    <div style="font-size:0.7rem;color:{day_c};margin-top:1px;">{day_pc:+.2f}%</div>
                  </div>
                  <div style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:700;color:{pnl_c};">
                      {arrow} ₹{abs(r['pnl']):,.0f}
                    </div>
                    <div style="font-size:0.7rem;color:{pnl_c};margin-top:1px;">{r['pnl_p']:+.2f}%</div>
                  </div>
                </div>"""


            st.markdown(hold_html, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # 📤 SYNC TO TELEGRAM — holdings.json ko GitHub repo mein directly
            # push karo (GitHub API se), taaki Telegram bot turant naye
            # holdings dikhaye. Render khud detect karke redeploy kar dega.
            # ══════════════════════════════════════════════════════════════════════
            def sync_holdings_to_github():
                """
                portfolio_data.json ke pt_holdings se holdings.json banao,
                GitHub API se telegram-portfolio-bot repo mein directly push karo.
                Return: (success: bool, message: str)
                """
                try:
                    gh_token = st.secrets["GITHUB_TOKEN"]
                except Exception:
                    gh_token = ""
                if not gh_token:
                    return False, "❌ GITHUB_TOKEN secrets.toml mein nahi mila."

                repo_owner = "Nitinrajgor07"
                repo_name  = "telegram-portfolio-bot"
                file_path  = "holdings.json"
                api_url    = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"

                headers = {
                    "Authorization": f"Bearer {gh_token}",
                    "Accept": "application/vnd.github+json",
                }

                # Naya holdings.json content banao (sirf relevant fields)
                clean_holdings = {}
                for tkr, h in st.session_state.pt_holdings.items():
                    clean_holdings[tkr] = {
                        "shares": h.get("shares", 0),
                        "avg_price": h.get("avg_price", 0.0),
                        "first_buy_date": h.get("first_buy_date"),
                    }
                new_content_str = json.dumps(clean_holdings, indent=2)
                new_content_b64 = base64.b64encode(new_content_str.encode("utf-8")).decode("utf-8")

                try:
                    # Step 1: Purani file ka SHA leke aao (update ke liye zaroori)
                    get_resp = requests.get(api_url, headers=headers, timeout=15)
                    if get_resp.status_code == 200:
                        sha = get_resp.json().get("sha")
                    elif get_resp.status_code == 404:
                        sha = None   # file abhi exist nahi karti, naya banayenge
                    else:
                        return False, f"❌ GitHub se file padhne mein error: {get_resp.status_code} — {get_resp.text[:200]}"

                    # Step 2: Naya content push karo (PUT request)
                    put_payload = {
                        "message": f"Update holdings via Streamlit sync — {ist_now().strftime('%Y-%m-%d %H:%M')}",
                        "content": new_content_b64,
                    }
                    if sha:
                        put_payload["sha"] = sha

                    put_resp = requests.put(api_url, headers=headers, json=put_payload, timeout=15)
                    if put_resp.status_code in (200, 201):
                        return True, f"✅ holdings.json GitHub pe push ho gaya! ({len(clean_holdings)} holdings) Render 1-2 min mein redeploy kar dega."
                    else:
                        return False, f"❌ GitHub push failed: {put_resp.status_code} — {put_resp.text[:200]}"

                except requests.exceptions.RequestException as e:
                    return False, f"❌ Network error: {e}"

            sync_c1, sync_c2 = st.columns([3, 1])
            with sync_c1:
                st.markdown(f"""
                <div style="font-size:0.78rem;color:{MUTED};padding-top:8px;">
                  📤 Naya BUY/SELL karne ke baad, yeh dabao taaki Telegram bot
                  turant updated holdings dikhaye — koi manual GitHub editing nahi chahiye.
                </div>""", unsafe_allow_html=True)
            with sync_c2:
                if st.button("📤 Sync to Telegram", key="sync_telegram_btn",
                            type="primary", width='stretch'):
                    with st.spinner("GitHub pe push ho raha hai..."):
                        success, msg = sync_holdings_to_github()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # PORTFOLIO ALLOCATION PIE CHART — holdings ke neeche
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">PORTFOLIO ALLOCATION</div>', unsafe_allow_html=True)

            labels = [r["name"] for r in rows]
            values = [round(r["cur_v"], 2) for r in rows]

            pie_fig = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.55,
                marker=dict(colors=PIE_COLS[:len(rows)],
                            line=dict(color=DARK_BG, width=2)),
                textinfo="label+percent",
                textfont=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
                hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
            ))

            nw_str = f"₹{net_worth/1e7:.2f}Cr"
            pie_fig.add_annotation(
                text=f"<b>Net Worth</b><br>{nw_str}",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=13, color=TEXT),
                align="center",
            )
            pie_fig.update_layout(
                paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                font=dict(color=TEXT),
                margin=dict(l=10, r=10, t=10, b=10),
                height=420,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    x=1.02, y=0.5,
                    font=dict(size=11, color=TEXT),
                    bgcolor="rgba(0,0,0,0)",
                ),
            )
            st.plotly_chart(pie_fig, width='stretch', key="port_pie")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── ZERODHA STYLE P&L BANNER + KPI CARDS — animated counters ──────────────
            # NOTE: st.markdown() ke andar <script> tags reliably nahi chalte
            # (yeh Streamlit ka jaana-maana behavior hai — browser innerHTML
            # assignment se inject hue script tags execute nahi karta).
            # Isliye components.v1.html() use kar rahe hain — yeh iframe mein
            # render hota hai jaha JavaScript guaranteed chalta hai.
            _tot_pnl_sign = "+" if total_pnl >= 0 else "-"
            _day_pnl_sign = "+" if day_pnl >= 0 else "-"
            _pnl_sign     = "+" if total_pnl >= 0 else "-"
            _pnl_abs      = abs(total_pnl)
            _cash_val     = st.session_state.pt_cash
            _tot_pnl_bg   = "rgba(39,174,96,0.12)" if total_pnl >= 0 else "rgba(231,76,60,0.12)"
            _day_pnl_bg   = "rgba(39,174,96,0.12)" if day_pnl   >= 0 else "rgba(231,76,60,0.12)"

            _animated_block_html = f"""
<style>
  * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  body {{ margin:0; padding:0; background:transparent; }}
  .banner {{
    background:{CARD_BG}; border:1px solid {BORDER}; border-radius:14px;
    padding:18px 24px; margin-bottom:18px;
    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;
  }}
  .b-label {{ font-size:0.68rem; color:{MUTED}; font-weight:600; letter-spacing:.07em; }}
  .b-sub   {{ font-size:0.75rem; color:{MUTED}; margin-top:4px; }}
  .b-value {{ font-size:1.85rem; font-weight:800; }}
  .b-pct   {{ font-size:1rem; font-weight:600; padding:2px 10px; border-radius:20px; }}
  .b-divider {{ width:1px; height:60px; background:{BORDER}; }}
  .b-row {{ display:flex; align-items:baseline; gap:10px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
  .kpi-card {{
    background:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;
    padding:14px; text-align:center;
  }}
  .kpi-label {{ font-size:0.68rem; color:{MUTED}; font-weight:600; letter-spacing:.05em; }}
  .kpi-val   {{ font-size:1.3rem; font-weight:800; margin-top:4px; }}
  .kpi-sub   {{ font-size:0.72rem; color:{MUTED}; margin-top:3px; }}
</style>

<div class="banner">
  <div>
    <div class="b-label">TOTAL P&amp;L (UNREALISED)</div>
    <div class="b-row">
      <span class="anim-counter b-value" data-target="{abs(total_pnl):.0f}"
            data-prefix="{_tot_pnl_sign}₹" style="color:{pnl_color};">{_tot_pnl_sign}₹0</span>
      <span class="b-pct" style="color:{pnl_color};background:{_tot_pnl_bg};">{total_pct:+.2f}%</span>
    </div>
    <div class="b-sub">Invested ₹{total_invested:,.0f} → Current ₹{total_cur_val:,.0f}</div>
  </div>

  <div class="b-divider"></div>

  <div>
    <div class="b-label">DAY'S P&amp;L</div>
    <div class="b-row">
      <span class="anim-counter b-value" data-target="{abs(day_pnl):.0f}"
            data-prefix="{_day_pnl_sign}₹" style="color:{day_color};">{_day_pnl_sign}₹0</span>
      <span class="b-pct" style="color:{day_color};background:{_day_pnl_bg};">{day_pct:+.2f}%</span>
    </div>
    <div class="b-sub">Aaj ke price change se</div>
  </div>

  <div class="b-divider"></div>

  <div>
    <div class="b-label">NET WORTH</div>
    <div class="anim-counter b-value" data-target="{net_worth:.0f}"
         data-prefix="₹" style="color:{TEXT};">₹0</div>
    <div class="b-sub">Cash ₹{st.session_state.pt_cash:,.0f} + Stocks ₹{total_cur_val:,.0f}</div>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">NET WORTH</div>
    <div class="anim-counter kpi-val" data-target="{net_worth:.0f}" data-prefix="₹" style="color:{TEXT};">₹0</div>
    <div class="kpi-sub">Start: ₹1,00,00,000</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">INVESTED</div>
    <div class="anim-counter kpi-val" data-target="{total_invested:.0f}" data-prefix="₹" style="color:{BLUE};">₹0</div>
    <div class="kpi-sub">Stocks: ₹{total_cur_val:,.0f}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">UNREALISED P&amp;L</div>
    <div class="anim-counter kpi-val" data-target="{_pnl_abs:.0f}" data-prefix="{_pnl_sign}₹" style="color:{pnl_color};">₹0</div>
    <div class="kpi-sub" style="color:{pnl_color};">{total_pct:+.2f}%</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">CASH BALANCE</div>
    <div class="anim-counter kpi-val" data-target="{_cash_val:.0f}" data-prefix="₹" style="color:{GREEN};">₹0</div>
    <div class="kpi-sub">{len(rows)} holdings</div>
  </div>
</div>

<script>
(function() {{
  function animateCounter(el) {{
    var target   = parseFloat(el.getAttribute('data-target')) || 0;
    var prefix   = el.getAttribute('data-prefix') || '';
    var duration = 1400;
    var start    = null;

    function easeOutQuart(t) {{ return 1 - Math.pow(1 - t, 4); }}
    function formatNum(n) {{ return Math.round(n).toLocaleString('en-IN'); }}

    function step(ts) {{
      if (!start) start = ts;
      var elapsed  = ts - start;
      var progress = Math.min(elapsed / duration, 1);
      var eased    = easeOutQuart(progress);
      var cur      = target * eased;
      el.textContent = prefix + formatNum(cur);
      if (progress < 1) {{
        requestAnimationFrame(step);
      }} else {{
        el.textContent = prefix + formatNum(target);
      }}
    }}
    requestAnimationFrame(step);
  }}

  document.querySelectorAll('.anim-counter').forEach(function(el) {{
    animateCounter(el);
  }});
}})();
</script>
"""
            st.iframe(_animated_block_html, height=360)

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # PORTFOLIO HEATMAP — Treemap (size = invested, color = P&L%)
            # Sabse last mein — ek nazar mein pura portfolio health
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">PORTFOLIO HEATMAP</div>', unsafe_allow_html=True)
            st.caption("Box size = invested amount  |  Color = profit/loss % (green = profit, red = loss)")

            hm_labels = [r["name"] for r in rows]
            hm_values = [max(r["inv"], 1) for r in rows]   # box size — invested amount
            hm_pnl_pct = [r["pnl_p"] for r in rows]         # color basis — P&L %
            hm_pnl_pct_str = [f"{r['pnl_p']:+.2f}%" for r in rows]

            hm_text = [
                f"{r['name']}<br>₹{r['inv']:,.0f} invested<br>{r['pnl_p']:+.2f}% ({'▲' if r['pnl']>=0 else '▼'} ₹{abs(r['pnl']):,.0f})"
                for r in rows
            ]

            heatmap_fig = go.Figure(go.Treemap(
                labels=hm_labels,
                parents=[""] * len(rows),
                values=hm_values,
                text=hm_text,
                texttemplate="<b>%{label}</b><br>%{customdata}",
                customdata=hm_pnl_pct_str,
                hovertemplate="%{text}<extra></extra>",
                marker=dict(
                    colors=hm_pnl_pct,
                    colorscale=[
                        [0.0, "#7f1d1d"],   # deep red — bahut loss
                        [0.4, "#e74c3c"],   # red — loss
                        [0.5, "#2a2d3a"],   # neutral — breakeven
                        [0.6, "#27ae60"],   # green — profit
                        [1.0, "#0d3320"],   # deep green — bahut profit
                    ],
                    cmid=0,
                    line=dict(color=DARK_BG, width=2),
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="P&L %", font=dict(color=TEXT, size=10)),
                        tickfont=dict(color=TEXT, size=9),
                        thickness=14,
                    ),
                ),
                textfont=dict(color="#ffffff", size=13),
                pathbar=dict(visible=False),
            ))
            heatmap_fig.update_layout(
                paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                margin=dict(l=4, r=4, t=4, b=4),
                height=420,
            )
            st.plotly_chart(heatmap_fig, width='stretch', key="portfolio_heatmap")

            st.markdown("<br>", unsafe_allow_html=True)

        with port_tab2:
            # SECTION B — P&L Graph (cumulative realised P&L over trades)
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">P&L GRAPH — TRADE WISE</div>',
                        unsafe_allow_html=True)

            sell_trades = [t for t in st.session_state.pt_history if t.get("P&L") is not None]

            if sell_trades:
                times      = [t["Time"] for t in sell_trades]
                pnls       = [t["P&L"]  for t in sell_trades]
                cum_pnl    = []
                running    = 0.0
                bar_colors = []
                for p in pnls:
                    running += p
                    cum_pnl.append(round(running, 2))
                    bar_colors.append(GREEN if p >= 0 else RED)

                pnl_fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.65, 0.35], vertical_spacing=0.06,
                    subplot_titles=("Cumulative P&L (₹)", "Per Trade P&L (₹)")
                )

                # Cumulative line + fill
                pnl_fig.add_trace(go.Scatter(
                    x=list(range(1, len(cum_pnl)+1)), y=cum_pnl,
                    mode="lines+markers",
                    fill="tozeroy",
                    fillcolor="rgba(39,174,96,0.12)" if cum_pnl[-1] >= 0 else "rgba(231,76,60,0.12)",
                    line=dict(color=GREEN if cum_pnl[-1] >= 0 else RED, width=2.5),
                    marker=dict(size=6, color=GREEN if cum_pnl[-1] >= 0 else RED),
                    hovertemplate="Trade %{x}<br>Cumulative P&L: ₹%{y:,.2f}<extra></extra>",
                    name="Cumulative",
                ), row=1, col=1)

                # Per-trade bars
                pnl_fig.add_trace(go.Bar(
                    x=list(range(1, len(pnls)+1)), y=pnls,
                    marker_color=bar_colors,
                    hovertemplate="Trade %{x}<br>P&L: ₹%{y:,.2f}<extra></extra>",
                    name="Per Trade",
                ), row=2, col=1)

                pnl_fig.update_layout(
                    paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                    font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=380,
                    showlegend=False,
                    xaxis2=dict(title="Trade #", gridcolor=BORDER),
                    yaxis=dict(gridcolor=BORDER, tickprefix="₹"),
                    yaxis2=dict(gridcolor=BORDER, tickprefix="₹"),
                )
                pnl_fig.update_xaxes(gridcolor=BORDER)
                pnl_fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dash"), row=1, col=1)
                pnl_fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dash"), row=2, col=1)

                st.plotly_chart(pnl_fig, width='stretch', key="pnl_graph")

                # Summary strip
                win_trades  = sum(1 for p in pnls if p > 0)
                loss_trades = sum(1 for p in pnls if p < 0)
                win_rate    = (win_trades / len(pnls) * 100) if pnls else 0
                st.markdown(f"""
                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;">
                  <div style="flex:1;background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">REALISED P&L</div>
                    <div style="font-size:1rem;font-weight:700;color:{'#27ae60' if running>=0 else RED};">₹{running:+,.2f}</div>
                  </div>
                  <div style="flex:1;background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">WIN RATE</div>
                    <div style="font-size:1rem;font-weight:700;color:{GREEN};">{win_rate:.0f}%</div>
                  </div>
                  <div style="flex:1;background:#0d3320;border:1px solid {GREEN};border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">PROFITABLE</div>
                    <div style="font-size:1rem;font-weight:700;color:{GREEN};">{win_trades}</div>
                  </div>
                  <div style="flex:1;background:#330d0d;border:1px solid {RED};border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">LOSS TRADES</div>
                    <div style="font-size:1rem;font-weight:700;color:{RED};">{loss_trades}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ══════════════════════════════════════════════════════════════
                # TRADE-WISE PROFIT & LOSS — sabse zyada profit wala upar,
                # phir profit kam hote hote loss tak neeche
                # ══════════════════════════════════════════════════════════════
                st.markdown('<div class="sec-title">TRADE-WISE PROFIT &amp; LOSS</div>',
                            unsafe_allow_html=True)

                sorted_trades = sorted(sell_trades, key=lambda t: t["P&L"], reverse=True)

                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1.6fr 0.8fr 1fr 1fr 1.2fr 1.6fr;
                            gap:8px;padding:8px 14px;
                            background:{DARK_BG};border-radius:8px 8px 0 0;
                            border:1px solid {BORDER};border-bottom:none;">
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">STOCK</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">QTY</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">BUY AVG</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">SELL PRICE</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">P&L</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">SOLD ON</div>
                </div>""", unsafe_allow_html=True)

                trade_html = ""
                for i, t in enumerate(sorted_trades):
                    t_pnl    = t["P&L"]
                    t_qty    = t["Shares"]
                    t_sell_p = t["Price"]
                    # buy avg back-calculate karo: P&L = (sell_price - buy_avg) * qty
                    t_buy_avg = t_sell_p - (t_pnl / t_qty) if t_qty else 0
                    t_pnl_pct = (t_pnl / (t_buy_avg * t_qty) * 100) if (t_buy_avg and t_qty) else 0
                    t_c     = GREEN if t_pnl >= 0 else RED
                    t_arrow = "▲" if t_pnl >= 0 else "▼"
                    bg      = CARD_BG if i % 2 == 0 else "rgba(255,255,255,0.02)"
                    border_r = "0 0 8px 8px" if i == len(sorted_trades)-1 else "0"
                    trade_html += f"""
                    <div style="display:grid;grid-template-columns:1.6fr 0.8fr 1fr 1fr 1.2fr 1.6fr;
                                gap:8px;padding:11px 14px;
                                background:{bg};
                                border:1px solid {BORDER};border-top:none;
                                border-radius:{border_r};">
                      <div style="font-size:0.85rem;font-weight:700;color:{TEXT};align-self:center;">{t['Name']}</div>
                      <div style="text-align:right;align-self:center;font-size:0.82rem;color:{TEXT};">{t_qty}</div>
                      <div style="text-align:right;align-self:center;font-size:0.82rem;color:{MUTED};">₹{t_buy_avg:,.2f}</div>
                      <div style="text-align:right;align-self:center;font-size:0.82rem;color:{TEXT};">₹{t_sell_p:,.2f}</div>
                      <div style="text-align:right;align-self:center;">
                        <div style="font-size:0.85rem;font-weight:700;color:{t_c};">{t_arrow} ₹{abs(t_pnl):,.2f}</div>
                        <div style="font-size:0.68rem;color:{t_c};margin-top:1px;">{t_pnl_pct:+.2f}%</div>
                      </div>
                      <div style="text-align:right;align-self:center;font-size:0.72rem;color:{MUTED};">{t['Time']}</div>
                    </div>"""

                st.markdown(trade_html, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                # ══════════════════════════════════════════════════════════════

            else:
                st.markdown(f"""
                <div style="text-align:center;padding:30px;color:{MUTED};">
                  <div style="font-size:1.5rem;">📊</div>
                  <div>Koi SELL trade nahi abhi tak — graph tab banega jab pehli sell hogi</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # ZERODHA STYLE P&L CALENDAR + TAX SUMMARY + STOCK TABLE
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">📅 P&L CALENDAR — ZERODHA STYLE</div>',
                        unsafe_allow_html=True)

            # ── Filter Bar ───────────────────────────────────────────────────────
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;
                        padding:14px 16px;margin-bottom:14px;">
              <div style="font-size:0.65rem;font-weight:800;color:{MUTED};
                          letter-spacing:.1em;margin-bottom:10px;">FILTERS</div>
            </div>""", unsafe_allow_html=True)

            # Quick preset buttons
            preset_cols = st.columns(4)
            with preset_cols[0]:
                if st.button("Last 7 days", key="cal_p7", width='stretch'):
                    st.session_state.cal_from = (ist_now() - timedelta(days=7)).date()
                    st.session_state.cal_to   = ist_now().date()
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[1]:
                if st.button("Last 30 days", key="cal_p30", width='stretch'):
                    st.session_state.cal_from = (ist_now() - timedelta(days=30)).date()
                    st.session_state.cal_to   = ist_now().date()
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[2]:
                if st.button("Current FY", key="cal_pfy", width='stretch'):
                    now_d = ist_now().date()
                    fy_start = date(now_d.year if now_d.month >= 4 else now_d.year - 1, 4, 1)
                    st.session_state.cal_from = fy_start
                    st.session_state.cal_to   = now_d
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[3]:
                if st.button("Prev FY", key="cal_ppfy", width='stretch'):
                    now_d = ist_now().date()
                    fy_yr = now_d.year if now_d.month >= 4 else now_d.year - 1
                    st.session_state.cal_from = date(fy_yr - 1, 4, 1)
                    st.session_state.cal_to   = date(fy_yr, 3, 31)
                    st.session_state.cal_has_applied = True
                    st.rerun()

            # Date range + symbol filter
            if "cal_from" not in st.session_state:
                now_d = ist_now().date()
                fy_start = date(now_d.year if now_d.month >= 4 else now_d.year - 1, 4, 1)
                st.session_state.cal_from = fy_start
                st.session_state.cal_to   = now_d
            if "cal_symbol" not in st.session_state:
                st.session_state.cal_symbol = ""
            if "cal_has_applied" not in st.session_state:
                st.session_state.cal_has_applied = False   # jab tak user Apply na daबाये, calendar khali rahe

            fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
            with fc1:
                cal_from = st.date_input("From", value=st.session_state.cal_from,
                                          key="cal_from_input", label_visibility="visible")
            with fc2:
                cal_to = st.date_input("To", value=st.session_state.cal_to,
                                        key="cal_to_input", label_visibility="visible")
            with fc3:
                cal_sym = st.text_input("Symbol (optional)", value=st.session_state.cal_symbol,
                                         placeholder="eg: KPITTECH", key="cal_sym_input",
                                         label_visibility="visible").strip().upper()
            with fc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("→ Apply", key="cal_apply", width='stretch', type="primary"):
                    st.session_state.cal_from   = cal_from
                    st.session_state.cal_to     = cal_to
                    st.session_state.cal_symbol = cal_sym
                    st.session_state.cal_has_applied = True
                    st.rerun()

            # Use applied values
            _cal_from   = st.session_state.cal_from
            _cal_to     = st.session_state.cal_to
            _cal_symbol = st.session_state.cal_symbol

            # ── Build daily P&L from SELL trades in range ─────────────────────
            from collections import defaultdict
            import calendar as _cal_mod

            daily_pnl   = defaultdict(float)   # date → net P&L
            daily_sell  = defaultdict(float)   # date → sell value (for charges)
            daily_buy   = defaultdict(float)   # date → buy value (for stamp)

            all_sell_trades = [t for t in st.session_state.pt_history
                               if t.get("Action") == "SELL" and t.get("P&L") is not None]

            for t in all_sell_trades:
                try:
                    t_date = datetime.strptime(t["Time"], "%d %b %Y %I:%M %p").date()
                except Exception:
                    continue
                if not (_cal_from <= t_date <= _cal_to):
                    continue
                tkr_clean = t.get("Ticker", "").replace(".NS", "")
                if _cal_symbol and _cal_symbol not in tkr_clean:
                    continue
                daily_pnl[t_date]  += t["P&L"]
                daily_sell[t_date] += t["Value"]
                # buy value back-calc
                qty = t.get("Shares", 1)
                sell_p = t.get("Price", 0)
                pnl_v  = t.get("P&L", 0)
                buy_avg = sell_p - (pnl_v / qty) if qty else sell_p
                daily_buy[t_date] += buy_avg * qty

            # ── Zerodha Charges per day ───────────────────────────────────────
            def zerodha_charges(sell_val, buy_val):
                stt        = sell_val * 0.001
                exch       = (sell_val + buy_val) * 0.0000345
                sebi       = (sell_val + buy_val) * 0.000001
                stamp      = buy_val * 0.00015
                dp         = 15.93 if sell_val > 0 else 0
                gst        = (exch + sebi) * 0.18
                return round(stt + exch + sebi + stamp + dp + gst, 2)

            # ── Calendar — GitHub-style compact grid (asli Zerodha jaisa) ──────
            if not st.session_state.cal_has_applied:
                st.markdown(f"""
                <div style="text-align:center;padding:40px 20px;color:{MUTED};
                            background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;">
                  <div style="font-size:1.8rem;">📅</div>
                  <div style="font-size:0.9rem;font-weight:600;color:{TEXT};margin-top:10px;">
                    Date range select karke "→ Apply" dabao
                  </div>
                  <div style="font-size:0.78rem;margin-top:4px;">
                    Calendar yahan dikhega jab aap range confirm karoge
                  </div>
                </div>""", unsafe_allow_html=True)
            elif daily_pnl:
                max_abs = max(abs(v) for v in daily_pnl.values()) or 1

                from datetime import timedelta as _td
                import calendar as _calmod

                all_dates = []
                d = _cal_from
                while d <= _cal_to:
                    all_dates.append(d)
                    d += _td(days=1)

                def _pnl_color(pnl_v, max_abs):
                    """P&L intensity ke hisaab se green/red shade — Zerodha jaisa."""
                    norm = max(-1.0, min(1.0, pnl_v / max_abs))
                    if norm >= 0:
                        t = norm
                        return f"rgba(39,174,96,{0.25 + 0.65*t:.2f})"
                    else:
                        t = abs(norm)
                        return f"rgba(231,76,60,{0.25 + 0.65*t:.2f})"

                st.markdown(f"""
                <div style="font-size:0.65rem;color:{MUTED};text-align:right;margin-bottom:8px;">
                  🕐 {_cal_from.strftime('%Y-%m-%d')} to {_cal_to.strftime('%Y-%m-%d')}
                  {'— ' + _cal_symbol if _cal_symbol else ''}
                </div>""", unsafe_allow_html=True)

                # ── Week-column layout (Mon=row0 .. Sun=row6) ──────────────────────
                start_wd = _cal_from.weekday()   # Mon=0..Sun=6
                squares_by_week = []              # list of weeks; har week = list of 7 (day or None)
                cur_week = [None] * start_wd
                month_starts = {}                 # week_index -> "Jan" label jab mahine ka 1st din us week mein ho

                for d in all_dates:
                    if d.day == 1:
                        month_starts[len(squares_by_week)] = d.strftime("%b")
                    cur_week.append(d)
                    if len(cur_week) == 7:
                        squares_by_week.append(cur_week)
                        cur_week = []
                if cur_week:
                    cur_week += [None] * (7 - len(cur_week))
                    squares_by_week.append(cur_week)

                SQ = 14   # square size px — Zerodha jaisa compact
                GAP = 3

                # ── Grid HTML — har column ek week, month label NEECHE (jaisa Zerodha) ──
                grid_html = f'<div style="display:flex;gap:{GAP}px;overflow-x:auto;padding-bottom:6px;">'

                for wi, week in enumerate(squares_by_week):
                    month_lbl = month_starts.get(wi, "")
                    grid_html += f'<div style="display:flex;flex-direction:column;gap:{GAP}px;">'
                    for d in week:
                        if d is None or d < _cal_from or d > _cal_to:
                            grid_html += (
                                f'<div style="width:{SQ}px;height:{SQ}px;border-radius:3px;'
                                f'background:transparent;"></div>'
                            )
                            continue
                        pnl_v = daily_pnl.get(d)
                        if pnl_v is not None:
                            bg = _pnl_color(pnl_v, max_abs)
                            charges = zerodha_charges(daily_sell.get(d, 0), daily_buy.get(d, 0))
                            net_v = pnl_v - charges
                            grid_html += (
                                f'<div title="{d.strftime("%d %b %Y")} | Net P&amp;L: ₹{net_v:+,.2f}" '
                                f'style="width:{SQ}px;height:{SQ}px;border-radius:3px;background:{bg};'
                                f'cursor:default;border:1px solid rgba(255,255,255,0.08);"></div>'
                            )
                        else:
                            grid_html += (
                                f'<div title="{d.strftime("%d %b %Y")} | No trade" '
                                f'style="width:{SQ}px;height:{SQ}px;border-radius:3px;background:#21242f;'
                                f'cursor:default;border:1px solid rgba(255,255,255,0.04);"></div>'
                            )
                    grid_html += (
                        f'<div style="height:14px;font-size:0.6rem;font-weight:700;color:{MUTED};'
                        f'white-space:nowrap;margin-top:4px;">{month_lbl}</div>'
                        f'</div>'
                    )

                grid_html += '</div>'

                st.markdown(
                    f'<div style="background:{CARD_BG};border:1px solid {BORDER};'
                    f'border-radius:12px;padding:16px 18px;">{grid_html}'
                    f'<div style="display:flex;align-items:center;gap:14px;margin-top:10px;'
                    f'font-size:0.65rem;color:{MUTED};">'
                    f'<span style="display:inline-flex;align-items:center;gap:4px;">'
                    f'<span style="width:{SQ}px;height:{SQ}px;border-radius:3px;background:rgba(231,76,60,0.7);'
                    f'display:inline-block;"></span> Loss</span>'
                    f'<span style="display:inline-flex;align-items:center;gap:4px;">'
                    f'<span style="width:{SQ}px;height:{SQ}px;border-radius:3px;background:#21242f;'
                    f'display:inline-block;"></span> No trade</span>'
                    f'<span style="display:inline-flex;align-items:center;gap:4px;">'
                    f'<span style="width:{SQ}px;height:{SQ}px;border-radius:3px;background:rgba(39,174,96,0.7);'
                    f'display:inline-block;"></span> Profit</span>'
                    f'</div></div>', unsafe_allow_html=True)

                # ── Stats row — Zerodha Console style ────────────────────────
                total_realised  = sum(daily_pnl.values())
                total_charges   = sum(zerodha_charges(daily_sell[d], daily_buy[d])
                                      for d in daily_pnl)
                net_realised    = total_realised - total_charges
                unrealised_pnl  = total_pnl   # from holdings above

                # Longest streak
                streak_days = sorted(daily_pnl.keys())
                best_streak = 0
                best_streak_start = best_streak_end = None
                cur_streak = 0
                cur_start  = None
                prev_d     = None
                for sd in streak_days:
                    if daily_pnl[sd] > 0:
                        if prev_d is None or (sd - prev_d).days > 3:
                            cur_streak = 1
                            cur_start  = sd
                        else:
                            cur_streak += 1
                        if cur_streak > best_streak:
                            best_streak = cur_streak
                            best_streak_start = cur_start
                            best_streak_end   = sd
                    else:
                        cur_streak = 0
                        cur_start  = None
                    prev_d = sd

                # Most profitable day
                if daily_pnl:
                    best_day  = max(daily_pnl, key=daily_pnl.get)
                    best_day_pnl = daily_pnl[best_day]
                else:
                    best_day = best_day_pnl = None

                r_color  = GREEN if total_realised >= 0 else RED
                net_color= GREEN if net_realised >= 0 else RED
                ur_color = GREEN if unrealised_pnl >= 0 else RED

                st.markdown(f"""
                <div style="display:grid;grid-template-columns:repeat(5,1fr);
                            gap:10px;margin:14px 0;">

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:12px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">REALISED P&L</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{r_color};">
                      {'+'if total_realised>=0 else ''}₹{abs(total_realised):,.2f}
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:12px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">CHARGES & TAXES</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{RED};">
                      -₹{total_charges:,.2f}
                    </div>
                    <div style="font-size:0.6rem;color:{MUTED};margin-top:3px;">
                      STT+Exch+SEBI+Stamp+GST
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:12px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">OTHER CREDITS & DEBITS</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{TEXT};">
                      ₹0.00
                    </div>
                    <div style="font-size:0.6rem;color:{MUTED};margin-top:3px;">
                      Paper trading — N/A
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-top:3px solid {net_color};
                              border-radius:12px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">NET REALISED P&L</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{net_color};">
                      {'+'if net_realised>=0 else ''}₹{abs(net_realised):,.2f}
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:12px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">UNREALISED P&L</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{ur_color};">
                      {'+'if unrealised_pnl>=0 else ''}₹{abs(unrealised_pnl):,.2f}
                    </div>
                  </div>

                </div>""", unsafe_allow_html=True)

                # Streak + Best day cards
                if best_streak > 0:
                    s_start_str = best_streak_start.strftime("%d %b %Y") if best_streak_start else "—"
                    s_end_str   = best_streak_end.strftime("%d %b %Y")   if best_streak_end   else "—"
                    bd_str      = best_day.strftime("%d %b %Y")          if best_day          else "—"
                    st.markdown(f"""
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
                      <div style="background:{CARD_BG};border:1px solid {BORDER};
                                  border-radius:12px;padding:14px;display:flex;gap:14px;align-items:center;">
                        <div style="font-size:2.5rem;">🔥</div>
                        <div>
                          <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                      letter-spacing:.08em;">LONGEST PROFIT STREAK</div>
                          <div style="font-size:0.72rem;color:{MUTED};margin-top:3px;">
                            {s_start_str} – {s_end_str}
                          </div>
                          <div style="font-size:1.4rem;font-weight:900;color:{GREEN};">
                            {best_streak} days
                          </div>
                        </div>
                      </div>
                      <div style="background:{CARD_BG};border:1px solid {BORDER};
                                  border-radius:12px;padding:14px;display:flex;gap:14px;align-items:center;">
                        <div style="font-size:2.5rem;">💰</div>
                        <div>
                          <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                      letter-spacing:.08em;">MOST PROFITABLE DAY</div>
                          <div style="font-size:0.72rem;color:{MUTED};margin-top:3px;">{bd_str}</div>
                          <div style="font-size:1.4rem;font-weight:900;color:{GREEN};">
                            +₹{best_day_pnl:,.2f}
                          </div>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div style="text-align:center;padding:40px;color:{MUTED};">
                  <div style="font-size:2.5rem;">📅</div>
                  <div style="margin-top:10px;">Is date range mein koi SELL trade nahi mila.</div>
                  <div style="font-size:0.78rem;margin-top:6px;">
                    Date range change karo ya pehle koi trade karo.
                  </div>
                </div>""", unsafe_allow_html=True)

            # ── Next Day Tax Card (aaj ki sells → kal dikhegi) ──────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-title">🧾 NEXT DAY TAX SUMMARY</div>',
                        unsafe_allow_html=True)
            st.caption("Aaj ki SELL trades ka tax breakdown — kal yahan confirm hoga")

            today_str   = ist_now().strftime("%d %b %Y")
            today_sells = [t for t in st.session_state.pt_history
                           if t.get("Action") == "SELL"
                           and t.get("P&L") is not None
                           and today_str in t.get("Time", "")]

            if today_sells:
                stcg_profit = 0.0
                ltcg_profit = 0.0
                stcg_loss   = 0.0
                ltcg_loss   = 0.0
                total_sell_val_today = 0.0
                total_buy_val_today  = 0.0
                tax_rows_html = ""

                for t in today_sells:
                    qty       = t.get("Shares", 1)
                    sell_p    = t.get("Price", 0)
                    pnl_v     = t.get("P&L", 0)
                    sell_val  = t.get("Value", sell_p * qty)
                    buy_avg   = sell_p - (pnl_v / qty) if qty else sell_p
                    buy_val   = buy_avg * qty

                    total_sell_val_today += sell_val
                    total_buy_val_today  += buy_val

                    # LTCG vs STCG — check holding period from history
                    tkr = t.get("Ticker", "")
                    held = st.session_state.pt_holdings.get(tkr, {})
                    fbd  = held.get("first_buy_date")
                    if fbd:
                        try:
                            held_days = (ist_now().date() -
                                         datetime.strptime(fbd, "%Y-%m-%d").date()).days
                        except Exception:
                            held_days = 0
                    else:
                        held_days = 0

                    is_ltcg = held_days > 365

                    if is_ltcg:
                        if pnl_v > 0:
                            ltcg_profit += pnl_v
                        else:
                            ltcg_loss   += abs(pnl_v)
                    else:
                        if pnl_v > 0:
                            stcg_profit += pnl_v
                        else:
                            stcg_loss   += abs(pnl_v)

                    pnl_c = GREEN if pnl_v >= 0 else RED
                    term  = "LTCG" if is_ltcg else "STCG"
                    term_c= "#a78bfa" if is_ltcg else "#f59e0b"
                    charges_t = zerodha_charges(sell_val, buy_val)

                    tax_rows_html += (
                        f'<div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr 1fr 1fr 0.8fr 1fr;'
                        f'gap:8px;padding:10px 14px;background:{CARD_BG};'
                        f'border:1px solid {BORDER};border-top:none;">'
                        f'<div style="font-size:0.83rem;font-weight:700;color:{TEXT};">'
                        f'{t.get("Name", tkr.replace(".NS",""))}</div>'
                        f'<div style="text-align:right;font-size:0.8rem;color:{TEXT};">{qty}</div>'
                        f'<div style="text-align:right;font-size:0.8rem;color:{MUTED};">₹{buy_avg:,.2f}</div>'
                        f'<div style="text-align:right;font-size:0.8rem;color:{TEXT};">₹{sell_p:,.2f}</div>'
                        f'<div style="text-align:right;">'
                        f'<div style="font-size:0.83rem;font-weight:700;color:{pnl_c};">'
                        f'{"+" if pnl_v>=0 else ""}₹{pnl_v:,.2f}</div></div>'
                        f'<div style="text-align:center;">'
                        f'<span style="background:{term_c}22;color:{term_c};'
                        f'border-radius:4px;padding:2px 7px;'
                        f'font-size:0.65rem;font-weight:800;">{term}</span></div>'
                        f'<div style="text-align:right;font-size:0.78rem;color:{RED};">-₹{charges_t:,.2f}</div>'
                        f'</div>'
                    )

                # Tax calculation
                stcg_net = max(0.0, stcg_profit - stcg_loss)
                stcg_tax = stcg_net * 0.15
                ltcg_net = max(0.0, ltcg_profit - ltcg_loss)
                ltcg_taxable = max(0.0, ltcg_net - 125000)   # ₹1.25L exemption
                ltcg_tax = ltcg_taxable * 0.10
                total_tax = stcg_tax + ltcg_tax
                total_charges_today = zerodha_charges(total_sell_val_today, total_buy_val_today)
                total_pnl_today = sum(t.get("P&L", 0) for t in today_sells)
                net_after_tax = total_pnl_today - total_tax - total_charges_today

                # Header
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr 1fr 1fr 0.8fr 1fr;
                            gap:8px;padding:8px 14px;
                            background:{DARK_BG};border-radius:8px 8px 0 0;
                            border:1px solid {BORDER};border-bottom:none;">
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">STOCK</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">QTY</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">BUY AVG</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">SELL PRICE</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">P&L</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:center;">TYPE</div>
                  <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;text-align:right;">CHARGES</div>
                </div>
                {tax_rows_html}
                <div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr 1fr 1fr 0.8fr 1fr;
                            gap:8px;padding:10px 14px;
                            background:{DARK_BG};border:1px solid {BORDER};
                            border-top:2px solid {BORDER};border-radius:0 0 8px 8px;">
                  <div style="font-size:0.75rem;font-weight:800;color:{TEXT};">TOTAL</div>
                  <div></div><div></div><div></div>
                  <div style="text-align:right;font-size:0.85rem;font-weight:800;
                              color:{'#27ae60' if total_pnl_today>=0 else RED};">
                    {'+'if total_pnl_today>=0 else ''}₹{total_pnl_today:,.2f}
                  </div>
                  <div></div>
                  <div style="text-align:right;font-size:0.82rem;font-weight:700;color:{RED};">
                    -₹{total_charges_today:,.2f}
                  </div>
                </div>""", unsafe_allow_html=True)

                # Tax breakdown
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""<div style="background:{CARD_BG};border:1px solid {BORDER};
border-radius:14px;padding:18px 20px;">
<div style="font-size:0.65rem;font-weight:800;color:{MUTED};
letter-spacing:.1em;margin-bottom:12px;">💰 TAX BREAKDOWN (NEXT DAY ESTIMATE)</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px;">

<div style="background:#1a1200;border:1px solid #f59e0b44;
border-radius:10px;padding:12px;text-align:center;">
<div style="font-size:0.62rem;color:{MUTED};font-weight:700;">STCG TAX (15%)</div>
<div style="font-size:1.1rem;font-weight:900;color:#f59e0b;margin-top:4px;">
₹{stcg_tax:,.2f}
</div>
<div style="font-size:0.65rem;color:{MUTED};margin-top:3px;">
Profit ₹{stcg_profit:,.2f} − Loss ₹{stcg_loss:,.2f}
</div>
</div>

<div style="background:#0d1626;border:1px solid #a78bfa44;
border-radius:10px;padding:12px;text-align:center;">
<div style="font-size:0.62rem;color:{MUTED};font-weight:700;">LTCG TAX (10%)</div>
<div style="font-size:1.1rem;font-weight:900;color:#a78bfa;margin-top:4px;">
₹{ltcg_tax:,.2f}
</div>
<div style="font-size:0.65rem;color:{MUTED};margin-top:3px;">
₹1.25L exemption ke baad taxable
</div>
</div>

<div style="background:#1c0808;border:1px solid {RED}44;
border-top:3px solid {RED};
border-radius:10px;padding:12px;text-align:center;">
<div style="font-size:0.62rem;color:{MUTED};font-weight:700;">NET AFTER TAX</div>
<div style="font-size:1.1rem;font-weight:900;
color:{'#27ae60' if net_after_tax>=0 else RED};margin-top:4px;">
{'+'if net_after_tax>=0 else ''}₹{net_after_tax:,.2f}
</div>
<div style="font-size:0.65rem;color:{MUTED};margin-top:3px;">
P&L − Tax − Charges
</div>
</div>

</div>
<div style="font-size:0.65rem;color:#3a3f52;text-align:center;">
⚠️ Estimate only — actual tax CA se confirm karein. STCG = &lt;1 yr, LTCG = &gt;1 yr.
</div>
</div>""", unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {BORDER};
                            border-radius:12px;padding:24px;text-align:center;color:{MUTED};">
                  <div style="font-size:2rem;">🧾</div>
                  <div style="margin-top:8px;font-size:0.9rem;">Aaj koi SELL trade nahi hua.</div>
                  <div style="font-size:0.75rem;margin-top:4px;">
                    Jab bhi aaj sell karoge, kal yahan tax summary dikhegi.
                  </div>
                </div>""", unsafe_allow_html=True)

            # ── Zerodha Console style Stock Table ────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-title">📊 SYMBOL-WISE P&L TABLE</div>',
                        unsafe_allow_html=True)

            # Build per-symbol data from filtered sell trades
            from collections import defaultdict as _dd2
            sym_buy_val  = _dd2(float)
            sym_sell_val = _dd2(float)
            sym_buy_qty  = _dd2(float)
            sym_sell_qty = _dd2(float)
            sym_realised = _dd2(float)
            sym_name_map = {}

            for t in all_sell_trades:
                try:
                    t_date = datetime.strptime(t["Time"], "%d %b %Y %I:%M %p").date()
                except Exception:
                    continue
                if not (_cal_from <= t_date <= _cal_to):
                    continue
                tkr_k = t.get("Ticker", "").replace(".NS", "")
                if _cal_symbol and _cal_symbol not in tkr_k:
                    continue
                qty    = t.get("Shares", 0)
                sell_p = t.get("Price", 0)
                pnl_v  = t.get("P&L", 0)
                buy_avg = sell_p - (pnl_v / qty) if qty else sell_p

                sym_sell_qty[tkr_k]  += qty
                sym_sell_val[tkr_k]  += sell_p * qty
                sym_buy_qty[tkr_k]   += qty
                sym_buy_val[tkr_k]   += buy_avg * qty
                sym_realised[tkr_k]  += pnl_v
                sym_name_map[tkr_k]   = t.get("Name", tkr_k)

            # Current holdings for unrealised
            sym_unrealised = {}
            sym_hold_inv = {}
            for r in rows:
                tkr_k = r["ticker"].replace(".NS", "")
                sym_unrealised[tkr_k] = r["pnl"]
                sym_hold_inv[tkr_k]   = r["inv"]

            all_syms = sorted(set(list(sym_realised.keys()) + list(sym_unrealised.keys())))

            if all_syms:
                # Search box
                _tbl_search = st.text_input(
                    "🔍 Search symbol", value="", key="symtbl_search",
                    placeholder="eg: KPITTECH", label_visibility="collapsed"
                ).strip().upper()
                if _tbl_search:
                    all_syms = [s for s in all_syms if _tbl_search in s]

                # Table header
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            font-size:0.62rem;color:{MUTED};margin-bottom:6px;">
                  <span>Showing {len(all_syms)} symbols ·
                    Date: {_cal_from.strftime('%Y-%m-%d')} ~ {_cal_to.strftime('%Y-%m-%d')}
                    {'· Symbol: ' + _cal_symbol if _cal_symbol else ''}</span>
                  <span>🕐 Last updated: {ist_now().strftime('%Y-%m-%d')}</span>
                </div>
                <div style="display:grid;
                            grid-template-columns:1.4fr 0.6fr 1fr 1fr 1fr 1fr 1.2fr 1.2fr;
                            gap:6px;padding:8px 14px;
                            background:{DARK_BG};border-radius:8px 8px 0 0;
                            border:1px solid {BORDER};border-bottom:none;">
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">SYMBOL</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">QTY</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">BUY AVG</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">BUY VALUE</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">SELL AVG</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">SELL VALUE</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">REALISED P&L</div>
                  <div style="font-size:0.6rem;color:{MUTED};font-weight:700;text-align:right;">UNREALISED P&L</div>
                </div>""", unsafe_allow_html=True)

                tbl_html = ""
                for i, sym in enumerate(all_syms):
                    sq  = sym_sell_qty.get(sym, 0)
                    bq  = sym_buy_qty.get(sym, 0)
                    bv  = sym_buy_val.get(sym, 0)
                    sv  = sym_sell_val.get(sym, 0)
                    bavg = bv / bq if bq else 0
                    savg = sv / sq if sq else 0
                    rp  = sym_realised.get(sym, 0)
                    up  = sym_unrealised.get(sym, None)
                    bg  = CARD_BG if i % 2 == 0 else "rgba(255,255,255,0.02)"
                    br  = "0 0 8px 8px" if i == len(all_syms)-1 else "0"
                    rc  = GREEN if rp >= 0 else RED
                    rp_pct = (rp / bv * 100) if bv else 0

                    up_html = "—"
                    if up is not None:
                        uc = GREEN if up >= 0 else RED
                        hold_inv = sym_hold_inv.get(sym, 0)
                        up_pct = (up / hold_inv * 100) if hold_inv else 0
                        up_html = (f'<div style="font-size:0.8rem;font-weight:700;color:{uc};">'
                                   f'{"+"if up>=0 else ""}₹{up:,.2f}</div>'
                                   f'<div style="font-size:0.65rem;color:{uc};">{up_pct:+.2f}%</div>')

                    tbl_html += (
                        f'<div style="display:grid;'
                        f'grid-template-columns:1.4fr 0.6fr 1fr 1fr 1fr 1fr 1.2fr 1.2fr;'
                        f'gap:6px;padding:10px 14px;'
                        f'background:{bg};border:1px solid {BORDER};'
                        f'border-top:none;border-radius:{br};">'
                        f'<div>'
                        f'<div style="font-size:0.85rem;font-weight:700;color:{TEXT};">{sym}</div>'
                        f'<div style="font-size:0.65rem;color:{MUTED};">{sym_name_map.get(sym,"")}</div>'
                        f'</div>'
                        f'<div style="text-align:right;align-self:center;font-size:0.8rem;color:{TEXT};">'
                        f'{int(sq) if sq else "—"}</div>'
                        f'<div style="text-align:right;align-self:center;font-size:0.78rem;color:{MUTED};">'
                        f'{"₹"+f"{bavg:,.2f}" if bavg else "—"}</div>'
                        f'<div style="text-align:right;align-self:center;font-size:0.78rem;color:{MUTED};">'
                        f'{"₹"+f"{bv:,.2f}" if bv else "—"}</div>'
                        f'<div style="text-align:right;align-self:center;font-size:0.78rem;color:{TEXT};">'
                        f'{"₹"+f"{savg:,.2f}" if savg else "—"}</div>'
                        f'<div style="text-align:right;align-self:center;font-size:0.78rem;color:{TEXT};">'
                        f'{"₹"+f"{sv:,.2f}" if sv else "—"}</div>'
                        f'<div style="text-align:right;align-self:center;">'
                        + (f'<div style="font-size:0.8rem;font-weight:700;color:{rc};">'
                           f'{"+" if rp>=0 else ""}₹{rp:,.2f}</div>'
                           f'<div style="font-size:0.65rem;color:{rc};">{rp_pct:+.2f}%</div>'
                           if sq else
                           f'<div style="font-size:0.78rem;color:{MUTED};">—</div>')
                        + f'</div>'
                        f'<div style="text-align:right;align-self:center;">{up_html}</div>'
                        f'</div>'
                    )

                st.markdown(tbl_html, unsafe_allow_html=True)

                # ── Download button — CSV export ────────────────────────────────
                import io, csv as _csv
                _csv_buf = io.StringIO()
                _writer = _csv.writer(_csv_buf)
                _writer.writerow(["Symbol", "Qty", "Buy Avg", "Buy Value",
                                  "Sell Avg", "Sell Value", "Realised P&L", "Unrealised P&L"])
                for sym in all_syms:
                    sq  = sym_sell_qty.get(sym, 0)
                    bq  = sym_buy_qty.get(sym, 0)
                    bv  = sym_buy_val.get(sym, 0)
                    sv  = sym_sell_val.get(sym, 0)
                    bavg = bv / bq if bq else ""
                    savg = sv / sq if sq else ""
                    rp  = sym_realised.get(sym, "") if sq else ""
                    up  = sym_unrealised.get(sym, "")
                    _writer.writerow([sym, sq or "", bavg, bv or "", savg, sv or "", rp, up])

                st.download_button(
                    "⬇ Download CSV", data=_csv_buf.getvalue(),
                    file_name=f"pnl_{_cal_from}_{_cal_to}.csv",
                    mime="text/csv", key="pnl_table_download"
                )

            else:
                st.markdown(f"""
                <div style="text-align:center;padding:24px;color:{MUTED};">
                  <div>Is date range mein koi trade data nahi mila.</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            # ══════════════════════════════════════════════════════════════════════


        with port_tab3:
            # SECTION C — Brokerage / Tax Calculator
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">🧮 BROKERAGE & TAX CALCULATOR</div>',
                        unsafe_allow_html=True)
            st.caption("Real Indian stock market charges simulate karta hai (Zerodha rates ke hisaab se)")

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                calc_ticker = st.selectbox(
                    "Stock", [r["name"] for r in rows],
                    key="calc_stock"
                )
                calc_tkr = next((r["ticker"] for r in rows if r["name"] == calc_ticker), None)
                calc_price = next((r["cur"] for r in rows if r["name"] == calc_ticker), 100.0)
            with bc2:
                calc_qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="calc_qty")
            with bc3:
                trade_type = st.selectbox("Trade Type",
                    ["Equity Delivery", "Equity Intraday", "Equity F&O Futures", "Equity F&O Options"],
                    key="calc_type")

            order_val = calc_price * calc_qty

            # ── Charge calculation ────────────────────────────────────────────────
            if trade_type == "Equity Delivery":
                brokerage   = 0.0          # Zerodha: FREE for delivery
                stt_buy     = order_val * 0.001
                stt_sell    = order_val * 0.001
                stt         = stt_buy      # per side shown
                exch_txn    = order_val * 0.0000345
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00015  # only on buy
            elif trade_type == "Equity Intraday":
                brokerage   = min(order_val * 0.0003, 20.0)   # 0.03% or ₹20 max
                stt         = order_val * 0.00025              # only on sell side
                exch_txn    = order_val * 0.0000345
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00003
            elif trade_type == "Equity F&O Futures":
                brokerage   = 20.0
                stt         = order_val * 0.0001
                exch_txn    = order_val * 0.000019
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00002
            else:  # Options
                brokerage   = 20.0
                stt         = order_val * 0.0005   # on sell side (premium)
                exch_txn    = order_val * 0.00053
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00003

            gst_on_brok = (brokerage + exch_txn + sebi) * 0.18

            dp_charges  = 15.93 if trade_type == "Equity Delivery" else 0.0
            total_buy_charges  = brokerage + exch_txn + sebi + stamp + gst_on_brok
            total_sell_charges = brokerage + stt + exch_txn + sebi + gst_on_brok
            total_charges      = total_buy_charges + total_sell_charges + dp_charges

            breakeven_up   = calc_price + (total_charges / calc_qty)
            breakeven_down = calc_price - (total_charges / calc_qty)
            charges_pct    = (total_charges / order_val) * 100

            # Display
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;padding:16px 20px;margin-top:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                  <span style="font-size:1.1rem;font-weight:700;color:{TEXT};">{calc_ticker}</span>
                  &nbsp;<span style="font-size:0.8rem;color:{MUTED};">{calc_qty} shares @ ₹{calc_price:,.2f}</span>
                </div>
                <div style="font-size:1.1rem;font-weight:700;color:{BLUE};">Order Value: ₹{order_val:,.2f}</div>
              </div>

              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px;">
                <div style="background:#13161f;border-radius:8px;padding:10px 14px;">
                  <div style="font-size:0.65rem;color:{MUTED};margin-bottom:6px;">BUY SIDE CHARGES</div>
                  <div style="font-size:0.78rem;color:{TEXT};line-height:1.8;">
                    Brokerage: <b>₹{brokerage:.2f}</b><br>
                    Exchange Txn: <b>₹{exch_txn:.2f}</b><br>
                    SEBI Fee: <b>₹{sebi:.4f}</b><br>
                    Stamp Duty: <b>₹{stamp:.2f}</b><br>
                    GST (18%): <b>₹{gst_on_brok:.2f}</b>
                  </div>
                </div>
                <div style="background:#13161f;border-radius:8px;padding:10px 14px;">
                  <div style="font-size:0.65rem;color:{MUTED};margin-bottom:6px;">SELL SIDE CHARGES</div>
                  <div style="font-size:0.78rem;color:{TEXT};line-height:1.8;">
                    Brokerage: <b>₹{brokerage:.2f}</b><br>
                    STT: <b>₹{stt:.2f}</b><br>
                    Exchange Txn: <b>₹{exch_txn:.2f}</b><br>
                    SEBI Fee: <b>₹{sebi:.4f}</b><br>
                    GST (18%): <b>₹{gst_on_brok:.2f}</b>
                  </div>
                </div>
              </div>

              <div style="background:#0d1a0d;border:1px solid {GREEN};border-radius:8px;padding:12px 16px;">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;">
                  <div style="text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">TOTAL CHARGES</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{RED};">₹{total_charges:.2f}</div>
                    <div style="font-size:0.68rem;color:{MUTED};">({charges_pct:.3f}% of order)</div>
                  </div>
                  <div style="text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">DP CHARGES</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{TEXT};">₹{dp_charges:.2f}</div>
                    <div style="font-size:0.68rem;color:{MUTED};">(on sell, delivery only)</div>
                  </div>
                  <div style="text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">BREAKEVEN (BUY)</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{GREEN};">₹{breakeven_up:.2f}</div>
                    <div style="font-size:0.68rem;color:{MUTED};">Price must cross this</div>
                  </div>
                  <div style="text-align:center;">
                    <div style="font-size:0.65rem;color:{MUTED};">NET AFTER CHARGES</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{BLUE};">₹{order_val - total_charges:,.2f}</div>
                    <div style="font-size:0.68rem;color:{MUTED};">on full round trip</div>
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════
            # SECTION D — Portfolio Risk Score
            # ══════════════════════════════════════════════════════════════════════
            st.markdown('<div class="sec-title">🛡️ PORTFOLIO RISK SCORE</div>', unsafe_allow_html=True)

            @st.cache_data(ttl=3600)
            def fetch_beta(ticker: str) -> float | None:
                """Fetch beta from yfinance info."""
                try:
                    import yfinance as yf
                    info = yf.Ticker(ticker).info
                    b = info.get("beta")
                    return float(b) if b is not None else None
                except Exception:
                    return None

            with st.spinner("Beta values fetch ho rahi hain..."):
                beta_data = []
                total_portfolio_val = sum(r["cur_v"] for r in rows)
                for r in rows:
                    b = fetch_beta(r["ticker"])
                    weight = r["cur_v"] / total_portfolio_val if total_portfolio_val > 0 else 0
                    beta_data.append({
                        "ticker": r["ticker"],
                        "name": r["name"],
                        "beta": b,
                        "weight": weight,
                        "cur_v": r["cur_v"],
                        "pnl_p": r["pnl_p"],
                    })

            # Weighted portfolio beta
            valid = [(d["beta"], d["weight"]) for d in beta_data if d["beta"] is not None]
            if valid:
                port_beta = sum(b * w for b, w in valid)
                if port_beta <= 0.5:
                    raw_score = round(port_beta * 6, 1)
                elif port_beta <= 1.0:
                    raw_score = round(3.0 + (port_beta - 0.5) * 4, 1)
                elif port_beta <= 1.5:
                    raw_score = round(5.0 + (port_beta - 1.0) * 4, 1)
                else:
                    raw_score = min(10.0, round(7.0 + (port_beta - 1.5) * 6, 1))

                if raw_score <= 3:
                    score_color = "#27ae60"; risk_label = "LOW RISK"; risk_emoji = "🟢"
                    risk_desc = "Portfolio conservative hai — market se kam volatility"
                    gauge_fill = "#27ae60"
                elif raw_score <= 5:
                    score_color = "#f59e0b"; risk_label = "MODERATE RISK"; risk_emoji = "🟡"
                    risk_desc = "Market ke saath chal raha hai — balanced portfolio"
                    gauge_fill = "#f59e0b"
                elif raw_score <= 7:
                    score_color = "#f97316"; risk_label = "HIGH RISK"; risk_emoji = "🟠"
                    risk_desc = "Market se zyada volatile — careful trading karo"
                    gauge_fill = "#f97316"
                else:
                    score_color = "#e74c3c"; risk_label = "VERY HIGH RISK"; risk_emoji = "🔴"
                    risk_desc = "Bahut aggressive portfolio — bade swings aayenge"
                    gauge_fill = "#e74c3c"

                # ── Big score card ────────────────────────────────────────────────
                filled = int(raw_score)
                empty  = 10 - filled
                dots_html = (
                    f'<span style="color:{gauge_fill};font-size:1.1rem;">{"●" * filled}</span>'
                    f'<span style="color:#2a2d3a;font-size:1.1rem;">{"●" * empty}</span>'
                )

                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {score_color}44;
                            border-radius:16px;padding:20px 24px;margin-bottom:14px;">
                  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
                    <!-- Big Score Circle -->
                    <div style="text-align:center;min-width:100px;">
                      <div style="font-size:3.5rem;font-weight:900;color:{score_color};
                                  line-height:1;">{raw_score}</div>
                      <div style="font-size:0.65rem;color:{MUTED};margin-top:2px;">OUT OF 10</div>
                    </div>
                    <!-- Details -->
                    <div style="flex:1;">
                      <div style="font-size:1rem;font-weight:800;color:{score_color};
                                  margin-bottom:4px;">{risk_emoji} {risk_label}</div>
                      <div style="font-size:0.82rem;color:{MUTED};margin-bottom:10px;">
                        {risk_desc}
                      </div>
                      <div style="margin-bottom:6px;">{dots_html}</div>
                      <div style="font-size:0.75rem;color:{MUTED};">
                        Portfolio Beta: <span style="color:{score_color};font-weight:700;">{port_beta:.2f}</span>
                        &nbsp;·&nbsp; Beta > 1 = market se zyada volatile
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Per-stock beta table ──────────────────────────────────────────
                st.markdown(f'<div style="font-size:0.7rem;font-weight:700;color:{MUTED};'
                            f'letter-spacing:0.1em;margin-bottom:8px;">STOCK-WISE BETA</div>',
                            unsafe_allow_html=True)

                stock_rows_html = ""
                for d in sorted(beta_data, key=lambda x: (x["beta"] or 0), reverse=True):
                    b = d["beta"]
                    if b is None:
                        b_color = MUTED; b_str = "N/A"; b_bar = 0
                        b_label = "—"
                    elif b >= 1.5:
                        b_color = "#e74c3c"; b_str = f"{b:.2f}"; b_bar = min(100, int(b/2*100))
                        b_label = "Very High"
                    elif b >= 1.0:
                        b_color = "#f97316"; b_str = f"{b:.2f}"; b_bar = min(100, int(b/2*100))
                        b_label = "High"
                    elif b >= 0.5:
                        b_color = "#f59e0b"; b_str = f"{b:.2f}"; b_bar = min(100, int(b/2*100))
                        b_label = "Moderate"
                    else:
                        b_color = "#27ae60"; b_str = f"{b:.2f}"; b_bar = min(100, int(b/2*100))
                        b_label = "Low"

                    wt_pct = d["weight"] * 100
                    contrib = (b or 0) * d["weight"]

                    stock_rows_html += f"""
                    <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
                                padding:12px 16px;margin-bottom:6px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <div>
                          <span style="font-size:0.88rem;font-weight:700;color:{TEXT};">{d['name']}</span>
                          &nbsp;<span style="font-size:0.68rem;color:{MUTED};">{wt_pct:.1f}% of portfolio</span>
                        </div>
                        <div style="text-align:right;">
                          <span style="font-size:1rem;font-weight:800;color:{b_color};">β {b_str}</span>
                          &nbsp;<span style="background:{b_color}22;color:{b_color};
                                      border-radius:4px;padding:1px 7px;font-size:0.65rem;
                                      font-weight:700;">{b_label}</span>
                        </div>
                      </div>
                      <!-- Beta bar -->
                      <div style="background:#13161f;border-radius:4px;height:5px;">
                        <div style="background:{b_color};width:{b_bar}%;height:5px;border-radius:4px;"></div>
                      </div>
                      <div style="font-size:0.65rem;color:{MUTED};margin-top:4px;">
                        Risk contribution: <span style="color:{b_color};">{contrib:.3f}</span>
                      </div>
                    </div>"""

                st.markdown(stock_rows_html, unsafe_allow_html=True)

                # ── Risk tips ─────────────────────────────────────────────────────
                if raw_score >= 7:
                    tip_color = "#e74c3c"; tip_bg = "#1c0808"
                    tip = "⚠️ Portfolio bahut aggressive hai. Kuch defensive stocks (FMCG, Pharma) add karo."
                elif raw_score >= 5:
                    tip_color = "#f97316"; tip_bg = "#1a0f08"
                    tip = "💡 Moderate-high risk. Stop loss set karna zaroori hai."
                else:
                    tip_color = "#27ae60"; tip_bg = "#0d2015"
                    tip = "✅ Portfolio well-balanced hai. Market crash mein kam nuksan hoga."

                st.markdown(f"""
                <div style="background:{tip_bg};border:1px solid {tip_color}44;
                            border-radius:10px;padding:12px 16px;margin-top:4px;">
                  <span style="color:{tip_color};font-size:0.85rem;font-weight:600;">{tip}</span>
                </div>""", unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;
                            padding:24px;text-align:center;color:{MUTED};">
                  <div style="font-size:1.5rem;">📡</div>
                  <div style="margin-top:8px;">Beta data fetch nahi ho payi.</div>
                  <div style="font-size:0.78rem;">Internet check karo ya Refresh karo.</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)


    else:
        st.markdown(f"""
        <div style="text-align:center;padding:60px 20px;color:{MUTED};">
            <div style="font-size:2.5rem;">💼</div>
            <div style="font-size:1rem;margin-top:8px;color:{TEXT};">No holdings yet</div>
            <div style="font-size:0.78rem;margin-top:4px;">Orders tab se stocks kharido</div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════

    with port_tab2:
        # SECTION E — My Trade Stats
        # ══════════════════════════════════════════════════════════════════════════
        st.markdown('<div class="sec-title">📊 MY TRADE STATS</div>', unsafe_allow_html=True)

        all_trades   = st.session_state.pt_history
        sell_trades  = [t for t in all_trades if t.get("P&L") is not None]
        buy_trades   = [t for t in all_trades if t["Action"] == "BUY"]

        if len(sell_trades) == 0:
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;
                        padding:24px;text-align:center;color:{MUTED};">
              <div style="font-size:2rem;">📊</div>
              <div style="margin-top:8px;font-size:0.9rem;color:{TEXT};">Abhi koi closed trade nahi</div>
              <div style="font-size:0.75rem;margin-top:4px;">Kuch stocks kharido aur becho — stats yahan dikhenge</div>
            </div>""", unsafe_allow_html=True)
        else:
            # ── Core calculations ─────────────────────────────────────────────────
            profits  = [t["P&L"] for t in sell_trades if t["P&L"] > 0]
            losses   = [t["P&L"] for t in sell_trades if t["P&L"] < 0]
            breakevs = [t["P&L"] for t in sell_trades if t["P&L"] == 0]

            total_closed = len(sell_trades)
            win_count    = len(profits)
            loss_count   = len(losses)
            win_rate     = round(win_count / total_closed * 100, 1)

            total_pnl    = sum(t["P&L"] for t in sell_trades)
            avg_profit   = round(sum(profits) / len(profits), 2)   if profits else 0
            avg_loss     = round(sum(losses)  / len(losses),  2)   if losses  else 0
            best_trade   = max(sell_trades, key=lambda x: x["P&L"])
            worst_trade  = min(sell_trades, key=lambda x: x["P&L"])
            avg_trade    = round(total_pnl / total_closed, 2)
            profit_factor= round(sum(profits) / abs(sum(losses)), 2) if losses and sum(losses) != 0 else 999

            # Avg holding days
            holding_days_list = []
            from datetime import datetime
            buy_map = {}   # ticker → list of (date, price)
            for t in all_trades:
                tkr_t = t["Ticker"]
                try:
                    dt = datetime.strptime(t["Time"], "%d %b %Y %I:%M %p")
                except Exception:
                    dt = None
                if t["Action"] == "BUY":
                    buy_map.setdefault(tkr_t, []).append(dt)
                elif t["Action"] == "SELL" and dt and tkr_t in buy_map and buy_map[tkr_t]:
                    buy_dt = buy_map[tkr_t].pop(0)
                    if buy_dt:
                        days = (dt - buy_dt).days
                        holding_days_list.append(days)
            avg_hold = round(sum(holding_days_list) / len(holding_days_list), 1) if holding_days_list else 0

            # Consecutive wins/losses
            pnl_seq = [t["P&L"] for t in sell_trades]
            max_streak_w = max_streak_l = cur_w = cur_l = 0
            for p in pnl_seq:
                if p > 0: cur_w += 1; cur_l = 0
                else:     cur_l += 1; cur_w = 0
                max_streak_w = max(max_streak_w, cur_w)
                max_streak_l = max(max_streak_l, cur_l)

            # ── Win rate donut — pure HTML ────────────────────────────────────────
            wr_color  = "#27ae60" if win_rate >= 60 else ("#f59e0b" if win_rate >= 45 else "#e74c3c")
            wr_label  = "🔥 Excellent" if win_rate >= 65 else ("✅ Good" if win_rate >= 50 else ("⚠️ Average" if win_rate >= 40 else "❌ Needs Work"))
            pf_color  = "#27ae60" if profit_factor >= 2 else ("#f59e0b" if profit_factor >= 1 else "#e74c3c")
            pnl_color = "#27ae60" if total_pnl >= 0 else "#e74c3c"

            # ── Top KPI row ───────────────────────────────────────────────────────
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
              <div style="background:var(--card-bg);border:1px solid {wr_color}44;border-radius:12px;
                          padding:14px;text-align:center;border-top:3px solid {wr_color};">
                <div style="font-size:0.62rem;color:var(--secondary-text);font-weight:700;letter-spacing:0.08em;">WIN RATE</div>
                <div style="font-size:2rem;font-weight:900;color:{wr_color};line-height:1.1;">{win_rate}%</div>
                <div style="font-size:0.65rem;color:{wr_color};margin-top:2px;">{wr_label}</div>
              </div>
              <div style="background:var(--card-bg);border:1px solid {pnl_color}44;border-radius:12px;
                          padding:14px;text-align:center;border-top:3px solid {pnl_color};">
                <div style="font-size:0.62rem;color:var(--secondary-text);font-weight:700;letter-spacing:0.08em;">TOTAL P&L</div>
                <div style="font-size:1.4rem;font-weight:900;color:{pnl_color};line-height:1.2;">
                  {'+'if total_pnl>=0 else ''}₹{total_pnl:,.0f}
                </div>
                <div style="font-size:0.65rem;color:var(--secondary-text);margin-top:2px;">{total_closed} trades closed</div>
              </div>
              <div style="background:var(--card-bg);border:1px solid {pf_color}44;border-radius:12px;
                          padding:14px;text-align:center;border-top:3px solid {pf_color};">
                <div style="font-size:0.62rem;color:var(--secondary-text);font-weight:700;letter-spacing:0.08em;">PROFIT FACTOR</div>
                <div style="font-size:2rem;font-weight:900;color:{pf_color};line-height:1.1;">
                  {profit_factor if profit_factor != 999 else "∞"}
                </div>
                <div style="font-size:0.65rem;color:var(--secondary-text);margin-top:2px;">Gross profit / loss</div>
              </div>
              <div style="background:var(--card-bg);border:1px solid #3b82f644;border-radius:12px;
                          padding:14px;text-align:center;border-top:3px solid #3b82f6;">
                <div style="font-size:0.62rem;color:var(--secondary-text);font-weight:700;letter-spacing:0.08em;">AVG HOLD</div>
                <div style="font-size:2rem;font-weight:900;color:#3b82f6;line-height:1.1;">{avg_hold}d</div>
                <div style="font-size:0.65rem;color:var(--secondary-text);margin-top:2px;">Average holding days</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Win/Loss breakdown ────────────────────────────────────────────────
            win_bar  = win_count / total_closed * 100
            loss_bar = loss_count / total_closed * 100
            be_bar   = len(breakevs) / total_closed * 100

            st.markdown(f"""
            <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;
                        padding:16px 18px;margin-bottom:10px;">
              <div style="font-size:0.68rem;font-weight:800;color:var(--secondary-text);
                          letter-spacing:0.1em;margin-bottom:12px;">WINS vs LOSSES</div>
              <div style="display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap;">
                <div style="flex:1;min-width:100px;">
                  <div style="font-size:0.65rem;color:#27ae60;margin-bottom:4px;">
                    ✅ Winning Trades: {win_count}
                  </div>
                  <div style="background:#13161f;border-radius:4px;height:8px;">
                    <div style="background:#27ae60;width:{win_bar:.1f}%;height:8px;border-radius:4px;"></div>
                  </div>
                </div>
                <div style="flex:1;min-width:100px;">
                  <div style="font-size:0.65rem;color:#e74c3c;margin-bottom:4px;">
                    ❌ Losing Trades: {loss_count}
                  </div>
                  <div style="background:#13161f;border-radius:4px;height:8px;">
                    <div style="background:#e74c3c;width:{loss_bar:.1f}%;height:8px;border-radius:4px;"></div>
                  </div>
                </div>
                {"" if not breakevs else f'<div style="flex:1;min-width:80px;"><div style="font-size:0.65rem;color:var(--secondary-text);margin-bottom:4px;">⚪ Breakeven: {len(breakevs)}</div><div style="background:#13161f;border-radius:4px;height:8px;"><div style="background:var(--secondary-text);width:{be_bar:.1f}%;height:8px;border-radius:4px;"></div></div></div>'}
              </div>
              <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;
                          padding-top:10px;border-top:1px solid var(--border-color);">
                <div>
                  <span style="font-size:0.65rem;color:var(--secondary-text);">Avg Profit per Win</span>
                  <span style="font-size:0.82rem;font-weight:700;color:#27ae60;margin-left:8px;">
                    +₹{avg_profit:,.0f}
                  </span>
                </div>
                <div>
                  <span style="font-size:0.65rem;color:var(--secondary-text);">Avg Loss per Loss</span>
                  <span style="font-size:0.82rem;font-weight:700;color:#e74c3c;margin-left:8px;">
                    ₹{avg_loss:,.0f}
                  </span>
                </div>
                <div>
                  <span style="font-size:0.65rem;color:var(--secondary-text);">Avg per Trade</span>
                  <span style="font-size:0.82rem;font-weight:700;
                               color={'#27ae60' if avg_trade>=0 else '#e74c3c'};margin-left:8px;">
                    {'+'if avg_trade>=0 else ''}₹{avg_trade:,.0f}
                  </span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Best & Worst trade ────────────────────────────────────────────────
            bc1, bc2 = st.columns(2)
            with bc1:
                bp = best_trade["P&L"]
                st.markdown(f"""
                <div style="background:#0d2015;border:1px solid #27ae6055;border-radius:12px;
                            padding:14px 16px;">
                  <div style="font-size:0.65rem;color:#27ae60;font-weight:800;
                              letter-spacing:0.08em;margin-bottom:6px;">🏆 BEST TRADE</div>
                  <div style="font-size:1rem;font-weight:800;color:#e8eaf0;">
                    {best_trade.get('Name', best_trade['Ticker'].replace('.NS',''))}
                  </div>
                  <div style="font-size:1.3rem;font-weight:900;color:#27ae60;">+₹{bp:,.0f}</div>
                  <div style="font-size:0.68rem;color:var(--secondary-text);margin-top:4px;">
                    {best_trade['Shares']} shares @ ₹{best_trade['Price']:,.2f}
                    · {best_trade.get('Time','—')}
                  </div>
                </div>""", unsafe_allow_html=True)
            with bc2:
                wp = worst_trade["P&L"]
                st.markdown(f"""
                <div style="background:#1c0808;border:1px solid #e74c3c55;border-radius:12px;
                            padding:14px 16px;">
                  <div style="font-size:0.65rem;color:#e74c3c;font-weight:800;
                              letter-spacing:0.08em;margin-bottom:6px;">💀 WORST TRADE</div>
                  <div style="font-size:1rem;font-weight:800;color:#e8eaf0;">
                    {worst_trade.get('Name', worst_trade['Ticker'].replace('.NS',''))}
                  </div>
                  <div style="font-size:1.3rem;font-weight:900;color:#e74c3c;">₹{wp:,.0f}</div>
                  <div style="font-size:0.68rem;color:var(--secondary-text);margin-top:4px;">
                    {worst_trade['Shares']} shares @ ₹{worst_trade['Price']:,.2f}
                    · {worst_trade.get('Time','—')}
                  </div>
                </div>""", unsafe_allow_html=True)

            # ── Streaks + insight ─────────────────────────────────────────────────
            if profit_factor == 999:
                insight_html = ""
            else:
                pf_msg = ("Profit Factor 2+ — Excellent! Profits losses se 2x zyada hain." if profit_factor >= 2
                          else "Profit Factor 1-2 — Theek hai, par RR ratio improve karo." if profit_factor >= 1
                          else "Profit Factor < 1 — Losses profits se zyada hain. SL strict karo.")
                wr_msg = ("&nbsp; | &nbsp; Win rate 60%+ — Consistent trader ho!" if win_rate >= 60
                          else "&nbsp; | &nbsp;💡 Win rate badhane ke liye high-probability setups lo." if win_rate < 50
                          else "")
                insight_html = f"""
              <div style="font-size:0.78rem;color:var(--secondary-text);padding-top:10px;border-top:1px solid var(--border-color);">
                <b style="color:#e8eaf0;">Insight:</b>
                {pf_msg}
                {wr_msg}
              </div>"""

            st.markdown(f"""
            <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;
                        padding:14px 18px;margin-top:10px;">
              <div style="font-size:0.68rem;font-weight:800;color:var(--secondary-text);
                          letter-spacing:0.1em;margin-bottom:10px;">🔥 STREAKS & INSIGHT</div>
              <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
                <div style="background:#0d2015;border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:#27ae60;">Max Win Streak</div>
                  <div style="font-size:1.5rem;font-weight:900;color:#27ae60;">{max_streak_w}</div>
                </div>
                <div style="background:#1c0808;border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:#e74c3c;">Max Loss Streak</div>
                  <div style="font-size:1.5rem;font-weight:900;color:#e74c3c;">{max_streak_l}</div>
                </div>
                <div style="background:var(--card-bg);border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:var(--secondary-text);">Total BUY Orders</div>
                  <div style="font-size:1.5rem;font-weight:900;color:#3b82f6;">{len(buy_trades)}</div>
                </div>
                <div style="background:var(--card-bg);border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:var(--secondary-text);">Closed Trades</div>
                  <div style="font-size:1.5rem;font-weight:900;color:#e8eaf0;">{total_closed}</div>
                </div>
              </div>
              {insight_html}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)


    # Reset button always visible
    st.markdown("---")
    if st.button("🔁 Reset Portfolio (₹1 Cr)", key="reset_port"):
        st.session_state.pt_cash     = 10_000_000.0
        st.session_state.pt_holdings = {}
        st.session_state.pt_history  = []
        save_portfolio()
        st.rerun()

elif tab == "balance":
    # ── Pulse skeleton loader placeholder ──
    loading_ph = st.empty()
    with loading_ph.container():
        st.markdown("""
        <style>
        @keyframes pulse {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .skeleton-pulse {
            background: linear-gradient(-90deg, rgba(148, 163, 184, 0.08) 0%, rgba(148, 163, 184, 0.18) 50%, rgba(148, 163, 184, 0.08) 100%);
            background-size: 400% 400%;
            animation: pulse 1.5s ease infinite;
            border-radius: 12px;
        }
        </style>
        <div class="skeleton-pulse" style="height: 120px; border-radius: 16px; margin-bottom: 16px;"></div>
        <div class="db-grid">
            <div class="skeleton-pulse" style="height: 90px; border-radius: 14px;"></div>
            <div class="skeleton-pulse" style="height: 90px; border-radius: 14px;"></div>
            <div class="skeleton-pulse" style="height: 90px; border-radius: 14px;"></div>
            <div class="skeleton-pulse" style="height: 90px; border-radius: 14px;"></div>
            <div class="skeleton-pulse" style="height: 90px; border-radius: 14px;"></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Header with Refresh button ──
    bal_h, bal_r = st.columns([5, 1])
    with bal_h:
        st.markdown('<div class="sec-title">MY VIRTUAL BALANCE</div>', unsafe_allow_html=True)
    with bal_r:
        if st.button("🔄", key="balance_refresh", help="Prices refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            st.session_state["_ar_balance"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh only during market hours ──
    _bal_elapsed = time.time() - st.session_state.get("_ar_balance", 0)
    if _bal_elapsed >= _AUTO_REFRESH_SECS and is_market_open():
        get_index_quote.clear()
        get_batch_quotes.clear()
        st.session_state["_ar_balance"] = time.time()
        st.rerun()

    # ── ADD BALANCE SECTION ──
    if "show_add_balance" not in st.session_state:
        st.session_state.show_add_balance = False

    add_col, _ = st.columns([2.5, 3.5])
    with add_col:
        if st.button("💰 Add Virtual Balance", key="toggle_add_bal", use_container_width=True, type="secondary"):
            st.session_state.show_add_balance = not st.session_state.show_add_balance

    if st.session_state.show_add_balance:
        st.markdown('<div class="table-container" style="padding: 20px; border-left: 4px solid var(--success-color); margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.75rem; color:var(--muted-text); font-weight:700; letter-spacing:.06em; text-transform:uppercase; margin-bottom:12px;">💰 Virtual Balance Add Karo</div>', unsafe_allow_html=True)

        # Quick preset amounts
        q1, q2, q3, q4, q5 = st.columns(5)
        presets = [("50K", 50_000), ("1L", 1_00_000), ("5L", 5_00_000),
                   ("10L", 10_00_000), ("1Cr", 1_00_00_000)]
        for col, (label, amt) in zip([q1,q2,q3,q4,q5], presets):
            with col:
                if st.button(f"+₹{label}", key=f"preset_bal_{label}", use_container_width=True):
                    st.session_state.pt_cash += amt
                    save_portfolio()
                    st.session_state.show_add_balance = False
                    st.toast(f"💰 Added ₹{label} virtual balance!", icon="✅")
                    st.rerun()

        # Custom amount
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        inp_col, btn_col = st.columns([3, 1])
        with inp_col:
            custom_amt = st.number_input(
                "Custom Amount", min_value=1000, max_value=10_00_00_000,
                value=1_00_000, step=10_000, key="custom_bal_input",
                label_visibility="collapsed"
            )
        with btn_col:
            if st.button("➕ Add Cash", key="custom_bal_btn", type="primary", use_container_width=True):
                st.session_state.pt_cash += custom_amt
                save_portfolio()
                st.session_state.show_add_balance = False
                st.toast(f"💰 Added ₹{custom_amt:,.2f} virtual cash!", icon="✅")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Calculate totals ──
    total_invested = sum(h["shares"] * h["avg_price"]
                         for h in st.session_state.pt_holdings.values())
    total_cur_val  = 0
    _bal_tickers   = tuple(st.session_state.pt_holdings.keys())
    _bal_price_batch = get_indices_batch(_bal_tickers) if _bal_tickers else {}
    for tkr, h in st.session_state.pt_holdings.items():
        q = _bal_price_batch.get(tkr)
        total_cur_val += (q[0] if q else h["avg_price"]) * h["shares"]

    total_pnl = total_cur_val - total_invested
    net_worth = st.session_state.pt_cash + total_cur_val
    pnl_color = "var(--success-color)" if total_pnl >= 0 else "var(--danger-color)"
    pnl_sign = "+" if total_pnl >= 0 else ""
    pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

    # Today's P&L calculation
    _now = ist_now()
    _market_open_time = _now.replace(hour=9, minute=15, second=0, microsecond=0)
    _pre_market = _now < _market_open_time

    day_pnl = 0.0
    day_prev_val = 0.0
    if not _pre_market:
        for tkr, h in st.session_state.pt_holdings.items():
            q = _bal_price_batch.get(tkr)
            if q and len(q) >= 2:
                day_pnl += (q[0] - q[1]) * h["shares"]
                day_prev_val += q[1] * h["shares"]
            else:
                day_prev_val += h["avg_price"] * h["shares"]

    day_pnl_pct = (day_pnl / (day_prev_val + st.session_state.pt_cash) * 100) if (day_prev_val + st.session_state.pt_cash) else 0
    day_pnl_color = "var(--success-color)" if day_pnl >= 0 else "var(--danger-color)"
    day_pnl_sign = "+" if day_pnl >= 0 else ""

    nw_change = net_worth - 10_000_000
    nw_color  = "var(--success-color)" if nw_change >= 0 else "var(--danger-color)"
    nw_sign   = "+" if nw_change >= 0 else ""

    # Clear skeleton placeholder
    loading_ph.empty()

    # ── Main Balance Card ──
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(13,32,21,0.6), rgba(13,26,42,0.6));
                border: 1px solid var(--border-color); border-radius: 16px;
                padding: 24px; margin-bottom: 20px; text-align: center; backdrop-filter: blur(10px);
                box-shadow: var(--box-shadow);">
        <div style="font-size: 0.72rem; color: var(--secondary-text); letter-spacing: 0.1em; text-transform: uppercase;">
            💼 Total Net Worth
        </div>
        <div style="font-size: 2.8rem; font-weight: 800; color: var(--text-color); letter-spacing: -1px; margin-top: 6px;">
            ₹{net_worth:,.2f}
        </div>
        <div style="font-size: 0.88rem; color: {nw_color}; margin-top: 6px; font-weight: 600;">
            {nw_sign}₹{abs(nw_change):,.2f} ({nw_change/10000000*100:+.2f}%) from ₹1 Crore initial balance
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5 breakdown cards ──
    st.markdown(f"""
    <div class="db-grid">
        <div class="db-card">
            <div class="db-label">💵 Available Cash</div>
            <div class="db-val" style="color: var(--primary-blue);">₹{st.session_state.pt_cash:,.2f}</div>
            <div class="db-sub">Ready to trade</div>
        </div>
        <div class="db-card">
            <div class="db-label">📥 Invested Value</div>
            <div class="db-val">₹{total_invested:,.2f}</div>
            <div class="db-sub">Holdings purchase cost</div>
        </div>
        <div class="db-card">
            <div class="db-label">📦 Stock Value</div>
            <div class="db-val">₹{total_cur_val:,.2f}</div>
            <div class="db-sub">Current market price</div>
        </div>
        <div class="db-card" style="border-bottom: 3px solid {pnl_color};">
            <div class="db-label" style="color: {pnl_color};">📈 Unrealised P&L</div>
            <div class="db-val" style="color: {pnl_color};">{pnl_sign}₹{total_pnl:,.2f}</div>
            <div class="db-sub" style="color: {pnl_color};">{pnl_pct:+.2f}% absolute return</div>
        </div>
        <div class="db-card" style="border-bottom: 3px solid {day_pnl_color};">
            <div class="db-label" style="color: {day_pnl_color};">⚡ Today's P&L</div>
            <div class="db-val" style="color: {day_pnl_color};">{day_pnl_sign}₹{day_pnl:,.2f}</div>
            <div class="db-sub" style="color: {day_pnl_color};">{day_pnl_pct:+.2f}% day change</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Recent Trades history table ──
    if st.session_state.pt_history:
        st.markdown('<div class="sec-title" style="margin-top:20px;">RECENT TRADES</div>', unsafe_allow_html=True)
        
        trade_rows = ""
        for trade in reversed(st.session_state.pt_history[-10:]):
            action_badge = f'<span class="badge-buy">BUY</span>' if trade["Action"] == "BUY" else f'<span class="badge-sell">SELL</span>'
            pnl_td = ""
            if trade.get("P&L") is not None:
                p_color = "var(--success-color)" if trade["P&L"] >= 0 else "var(--danger-color)"
                pnl_td = f'<span style="color:{p_color}; font-weight:700;">₹{trade["P&L"]:+,.2f}</span>'
            else:
                pnl_td = '<span style="color:var(--muted-text);">—</span>'
                
            ticker_clean = trade['Ticker'].replace('.NS','')
            trade_rows += f"""<tr>
<td><b style="color:var(--text-color);">{trade.get('Name', ticker_clean)}</b><br><span style="font-size:0.7rem; color:var(--secondary-text);">{ticker_clean}</span></td>
<td>{action_badge}</td>
<td>{trade['Shares']}</td>
<td>₹{trade['Price']:,.2f}</td>
<td>₹{trade['Value']:,.2f}</td>
<td>{pnl_td}</td>
<td style="font-size:0.75rem; color:var(--secondary-text);">{trade['Time']}</td>
</tr>"""

        st.markdown(f"""<div class="table-container">
<table class="premium-table">
<thead>
<tr>
<th>Stock</th>
<th>Action</th>
<th>Shares</th>
<th>Price</th>
<th>Value</th>
<th>Realised P&L</th>
<th>Execution Time</th>
</tr>
</thead>
<tbody>
{trade_rows}
</tbody>
</table>
</div>""", unsafe_allow_html=True)

    # ── P&L REPORT BUTTON + SECTION (Zerodha style) ──
    if "show_pnl_report" not in st.session_state:
        st.session_state.show_pnl_report = False

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("📊 View P&L Ledger Report", key="pnl_report_btn", type="primary", use_container_width=True):
        st.session_state.show_pnl_report = not st.session_state.show_pnl_report

    if st.session_state.show_pnl_report:
        st.markdown('<div class="sec-title" style="margin-top:16px;">P&L LEDGER REPORT</div>', unsafe_allow_html=True)

        if not st.session_state.pt_history:
            st.markdown("""
            <div style="text-align:center; padding:50px 20px; color:var(--muted-text);
                        background:var(--card-bg); border:1px dashed var(--border-color); border-radius:16px; margin:10px 0;">
              <div style="font-size:3rem; margin-bottom:10px;">📊</div>
              <div style="font-size:1.1rem; font-weight:600; color:var(--text-color);">No transaction history</div>
              <div style="font-size:0.82rem; margin-top:6px; color:var(--secondary-text);">Trade history will be processed and visualised here once actions occur.</div>
            </div>""", unsafe_allow_html=True)
        else:
            import plotly.graph_objects as go

            sell_trades = [t for t in st.session_state.pt_history if t["Action"] == "SELL" and t.get("P&L") is not None]
            all_trades  = st.session_state.pt_history

            def parse_trade_date(t):
                try:
                    return datetime.strptime(t["Time"], "%d %b %Y %I:%M %p")
                except Exception:
                    return None

            st.markdown("""
            <div class="table-container" style="padding: 20px; border-bottom: 2px solid var(--primary-blue);">
              <div style="font-size:0.75rem; color:var(--muted-text); font-weight:700; letter-spacing:.06em; text-transform:uppercase; margin-bottom:12px;">📅 Date Range Filter</div>
            """, unsafe_allow_html=True)

            all_dates = [parse_trade_date(t) for t in all_trades]
            all_dates = [d for d in all_dates if d is not None]
            if all_dates:
                min_date = min(all_dates).date()
                max_date = max(all_dates).date()
            else:
                min_date = date.today().replace(month=1, day=1)
                max_date = date.today()

            # Presets row
            preset_col1, preset_col2, preset_col3, preset_col4, preset_col5 = st.columns(5)
            today = date.today()

            if "pnl_date_from" not in st.session_state:
                st.session_state.pnl_date_from = min_date
            if "pnl_date_to" not in st.session_state:
                st.session_state.pnl_date_to = max_date

            with preset_col1:
                if st.button("📆 This Month", key="preset_thismonth", use_container_width=True):
                    st.session_state.pnl_date_from = max(min_date, today.replace(day=1))
                    st.session_state.pnl_date_to   = min(max_date, today)
            with preset_col2:
                if st.button("📆 Last Month", key="preset_lastmonth", use_container_width=True):
                    first_this = today.replace(day=1)
                    last_prev  = first_this - timedelta(days=1)
                    st.session_state.pnl_date_from = max(min_date, last_prev.replace(day=1))
                    st.session_state.pnl_date_to   = min(max_date, last_prev)
            with preset_col3:
                if st.button("📆 Last 3M", key="preset_3m", use_container_width=True):
                    st.session_state.pnl_date_from = max(min_date, today - timedelta(days=90))
                    st.session_state.pnl_date_to   = min(max_date, today)
            with preset_col4:
                if st.button("📆 This Year", key="preset_thisyear", use_container_width=True):
                    st.session_state.pnl_date_from = max(min_date, today.replace(month=1, day=1))
                    st.session_state.pnl_date_to   = min(max_date, today)
            with preset_col5:
                if st.button("📆 All Time", key="preset_alltime", use_container_width=True):
                    st.session_state.pnl_date_from = min_date
                    st.session_state.pnl_date_to   = max_date

            clamped_from = max(min_date, min(st.session_state.pnl_date_from, max_date))
            clamped_to   = max(min_date, min(st.session_state.pnl_date_to,   max_date))

            dcol1, dcol2 = st.columns(2)
            with dcol1:
                date_from = st.date_input("From Date", value=clamped_from, min_value=min_date, max_value=max_date, key="pnl_from_picker")
                st.session_state.pnl_date_from = date_from
            with dcol2:
                date_to = st.date_input("To Date", value=clamped_to, min_value=min_date, max_value=max_date, key="pnl_to_picker")
                st.session_state.pnl_date_to = date_to

            st.markdown("</div>", unsafe_allow_html=True)

            def in_range(t):
                dt = parse_trade_date(t)
                if dt is None: return False
                return date_from <= dt.date() <= date_to

            filtered_trades = [t for t in all_trades  if in_range(t)]
            filtered_sells  = [t for t in sell_trades if in_range(t)]

            st.markdown(f"""
            <div style="background:rgba(59,130,246,0.08); border:1px solid var(--primary-blue); border-radius:8px;
                        padding:10px 16px; margin-bottom:16px;
                        display:flex; justify-content:space-between; align-items:center;">
              <span style="color:var(--primary-blue); font-size:0.8rem; font-weight:700;">
                📅 {date_from.strftime('%d %b %Y')} &nbsp;→&nbsp; {date_to.strftime('%d %b %Y')}
              </span>
              <span style="color:var(--secondary-text); font-size:0.75rem;">
                {len(filtered_trades)} executions in date range
              </span>
            </div>""", unsafe_allow_html=True)

            pnl_view_col, _ = st.columns([2.5, 3.5])
            with pnl_view_col:
                pnl_view = st.radio("View Grouping", ["Month-wise", "Year-wise"], horizontal=True, key="pnl_view_sel", label_visibility="collapsed")

            # Overall summary metrics for filtered selection
            total_realised   = sum(t["P&L"] for t in filtered_sells)
            total_profit_bkd = sum(t["P&L"] for t in filtered_sells if t["P&L"] > 0)
            total_loss_bkd   = sum(t["P&L"] for t in filtered_sells if t["P&L"] < 0)

            sell_trades = filtered_sells
            all_trades  = filtered_trades

            rc = "var(--success-color)" if total_realised >= 0 else "var(--danger-color)"
            uc = "var(--success-color)" if total_pnl >= 0 else "var(--danger-color)"

            st.markdown(f"""
            <div class="db-grid">
                <div class="db-card">
                    <div class="db-label">Realised P&L</div>
                    <div class="db-val" style="color:{rc};">{'+' if total_realised>=0 else ''}₹{total_realised:,.2f}</div>
                    <div class="db-sub">{len(sell_trades)} settlements</div>
                </div>
                <div class="db-card">
                    <div class="db-label">Unrealised P&L</div>
                    <div class="db-val" style="color:{uc};">{'+' if total_pnl>=0 else ''}₹{total_pnl:,.2f}</div>
                    <div class="db-sub">Current holdings return</div>
                </div>
                <div class="db-card" style="border-bottom: 2px solid var(--success-color);">
                    <div class="db-label" style="color:var(--success-color);">Gross Profit</div>
                    <div class="db-val" style="color:var(--success-color);">+₹{total_profit_bkd:,.2f}</div>
                    <div class="db-sub">Profitable exits</div>
                </div>
                <div class="db-card" style="border-bottom: 2px solid var(--danger-color);">
                    <div class="db-label" style="color:var(--danger-color);">Gross Loss</div>
                    <div class="db-val" style="color:var(--danger-color);">₹{total_loss_bkd:,.2f}</div>
                    <div class="db-sub">Loss exits</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Grouping computations
            from collections import defaultdict
            period_data = defaultdict(lambda: {"realised": 0.0, "profit": 0.0, "loss": 0.0, "trades": 0, "buy_val": 0.0, "sell_val": 0.0})

            for t in all_trades:
                dt = parse_trade_date(t)
                if dt is None: continue
                if pnl_view == "Month-wise":
                    key = dt.strftime("%b %Y")
                    sort_key = dt.strftime("%Y%m")
                else:
                    key = dt.strftime("%Y")
                    sort_key = key

                period_data[key]["_sort"] = sort_key
                period_data[key]["trades"] += 1

                if t["Action"] == "BUY":
                    period_data[key]["buy_val"] += t.get("Value", 0)
                else:
                    period_data[key]["sell_val"] += t.get("Value", 0)
                    pnl_val = t.get("P&L") or 0
                    period_data[key]["realised"] += pnl_val
                    if pnl_val > 0:
                        period_data[key]["profit"] += pnl_val
                    else:
                        period_data[key]["loss"]   += pnl_val

            sorted_periods = sorted(period_data.items(), key=lambda x: x[1].get("_sort", ""))

            if sorted_periods:
                labels   = [p[0] for p in sorted_periods]
                profits  = [p[1]["profit"]   for p in sorted_periods]
                losses   = [p[1]["loss"]     for p in sorted_periods]
                realiseds= [p[1]["realised"] for p in sorted_periods]

                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(
                    name="Profit Booked", x=labels, y=profits,
                    marker_color="#22c55e",
                    text=[f"₹{v:,.0f}" if v != 0 else "" for v in profits],
                    textposition="inside", textfont=dict(size=10, color="#ffffff"),
                ))
                bar_fig.add_trace(go.Bar(
                    name="Loss Booked", x=labels, y=losses,
                    marker_color="#ef4444",
                    text=[f"₹{v:,.0f}" if v != 0 else "" for v in losses],
                    textposition="inside", textfont=dict(size=10, color="#ffffff"),
                ))
                bar_fig.add_trace(go.Scatter(
                    name="Net Realised P&L", x=labels, y=realiseds,
                    mode="lines+markers+text",
                    line=dict(color="#3b82f6", width=2, dash="dot"),
                    marker=dict(size=8, color="#3b82f6"),
                    text=[f"₹{v:,.0f}" for v in realiseds],
                    textposition="top center",
                    textfont=dict(size=10, color="#3b82f6"),
                ))
                bar_fig.update_layout(
                    paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                    font=dict(color=TEXT, size=11, family="Inter, sans-serif"),
                    barmode="relative",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
                    margin=dict(l=60, r=20, t=60, b=60),
                    height=380,
                    xaxis=dict(gridcolor=CHART_GRID, showgrid=False, tickfont=dict(size=11, color=TEXT)),
                    yaxis=dict(gridcolor=CHART_GRID, showgrid=True, tickprefix="₹", zeroline=True, zerolinecolor="var(--border-color)", zerolinewidth=2, tickfont=dict(size=10, color=TEXT), automargin=True),
                    title=dict(text=f"P&L History ({pnl_view})", font=dict(size=13, color=MUTED), x=0),
                    bargap=0.35,
                )
                st.plotly_chart(bar_fig, width='stretch', key="pnl_bar_chart")

                # Period Comparison Table
                st.markdown('<div class="sec-title" style="margin-top:16px;">PERIOD COMPARISON</div>', unsafe_allow_html=True)
                period_rows = ""
                for period, d in reversed(sorted_periods):
                    r = d["realised"]
                    pr = d["profit"]
                    lo = d["loss"]
                    rc2 = "var(--success-color)" if r >= 0 else "var(--danger-color)"
                    r_sign = "+" if r >= 0 else ""
                    period_rows += f"""
                    <tr>
                        <td><b>{period}</b></td>
                        <td style="color:{rc2}; font-weight:700;">{r_sign}₹{r:,.2f}</td>
                        <td style="color:var(--success-color);">+₹{pr:,.2f}</td>
                        <td style="color:var(--danger-color);">₹{lo:,.2f}</td>
                        <td>{d['trades']}</td>
                    </tr>
                    """

                tot_r  = sum(d["realised"] for _, d in sorted_periods)
                tot_pr = sum(d["profit"]   for _, d in sorted_periods)
                tot_lo = sum(d["loss"]     for _, d in sorted_periods)
                tot_tr = sum(d["trades"]   for _, d in sorted_periods)
                tot_rc = "var(--success-color)" if tot_r >= 0 else "var(--danger-color)"
                tot_sign = "+" if tot_r >= 0 else ""

                period_rows += f"""
                <tr style="background:var(--tab-list-bg); font-weight:700; border-top: 2px solid var(--border-color);">
                    <td>TOTAL</td>
                    <td style="color:{tot_rc};">{tot_sign}₹{tot_r:,.2f}</td>
                    <td style="color:var(--success-color);">+₹{tot_pr:,.2f}</td>
                    <td style="color:var(--danger-color);">₹{tot_lo:,.2f}</td>
                    <td>{tot_tr}</td>
                </tr>
                """

                st.markdown(f"""
                <div class="table-container">
                    <table class="premium-table">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Realised P&L</th>
                                <th>Profit Booked</th>
                                <th>Loss Booked</th>
                                <th>Total Trades</th>
                            </tr>
                        </thead>
                        <tbody>
                            {period_rows}
                        </tbody>
                    </table>
                </div>
                """, unsafe_allow_html=True)

                # Stock-wise ledger breakdown
                st.markdown('<div class="sec-title" style="margin-top:20px;">STOCK-WISE P&L BREAKDOWN</div>', unsafe_allow_html=True)
                stock_pnl = defaultdict(lambda: {"profit":0.0, "loss":0.0, "realised":0.0, "sells":0})
                for t in sell_trades:
                    tkr2 = t["Ticker"]
                    nm   = t.get("Name", tkr2.replace(".NS",""))
                    pv   = t.get("P&L") or 0
                    stock_pnl[tkr2]["name"] = nm
                    stock_pnl[tkr2]["realised"] += pv
                    stock_pnl[tkr2]["sells"]    += 1
                    if pv > 0: stock_pnl[tkr2]["profit"] += pv
                    else:      stock_pnl[tkr2]["loss"]   += pv

                if stock_pnl:
                    stock_rows = ""
                    for tkr2, sd in sorted(stock_pnl.items(), key=lambda x: x[1]["realised"], reverse=True):
                        sc = "var(--success-color)" if sd["realised"] >= 0 else "var(--danger-color)"
                        s_sign = "+" if sd["realised"] >= 0 else ""
                        h2  = st.session_state.pt_holdings.get(tkr2)
                        unr_badge = ""
                        if h2:
                            q2    = get_index_quote(tkr2)
                            cp    = q2[0] if q2 else h2["avg_price"]
                            unr2  = (cp - h2["avg_price"]) * h2["shares"]
                            unr_badge = f'<span style="background:rgba(59,130,246,0.1); color:var(--primary-blue); border-radius:4px; padding:1px 6px; font-size:0.68rem; margin-left:8px; font-weight:700;">Unrealised: {unr2:+,.2f}</span>'

                        stock_rows += f"""
                        <tr>
                            <td><b>{sd['name']}</b> &nbsp; {unr_badge}</td>
                            <td style="color:{sc}; font-weight:700;">{s_sign}₹{sd['realised']:,.2f}</td>
                            <td style="color:var(--success-color);">+₹{sd['profit']:,.2f}</td>
                            <td style="color:var(--danger-color);">₹{sd['loss']:,.2f}</td>
                            <td>{sd['sells']}</td>
                        </tr>
                        """

                    st.markdown(f"""
                    <div class="table-container">
                        <table class="premium-table">
                            <thead>
                                <tr>
                                    <th>Stock</th>
                                    <th>Realised P&L</th>
                                    <th>Profit</th>
                                    <th>Loss</th>
                                    <th>Sells Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {stock_rows}
                            </tbody>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="text-align:center; padding:40px; color:var(--muted-text); background:var(--card-bg); border:1px dashed var(--border-color); border-radius:12px;">
                      No exit orders settled in this period.
                    </div>""")

    st.markdown("<br>", unsafe_allow_html=True)
elif tab == "news":
    import pytz
    from datetime import datetime, date
    import xml.etree.ElementTree as ET
    import urllib.request
    import urllib.parse
    import re
    import requests

    IST_TZ = pytz.timezone("Asia/Kolkata")
    
    # Initialize states
    if "news_last_updated" not in st.session_state:
        st.session_state.news_last_updated = datetime.now(IST_TZ).strftime("%I:%M %p, %d %b")
    if "news_search" not in st.session_state:
        st.session_state.news_search = ""
    if "saved_news" not in st.session_state:
        st.session_state.saved_news = set()
    if "ai_market_result" not in st.session_state:
        st.session_state.ai_market_result = None

    # Inject CSS for Glassmorphic premium news layout
    st.markdown("""
    <style>
    /* Styling category tabs */
    div[data-testid="stTabBar"] {
        background: var(--tab-list-bg) !important;
        border-radius: var(--btn-radius) !important;
        padding: 4px 36px !important;
        border: 1px solid var(--border-color) !important;
        margin-bottom: 24px !important;
        overflow-x: auto !important;
        position: relative !important;
        scroll-behavior: smooth !important;
    }
    div[data-testid="stTabBar"]::-webkit-scrollbar {
        display: none !important;
    }
    div[data-testid="stTabBar"] {
        -ms-overflow-style: none !important;
        scrollbar-width: none !important;
    }
    div[data-testid="stTabBar"] button {
        border-radius: calc(var(--btn-radius) - 4px) !important;
        padding: 8px 16px !important;
        color: var(--secondary-text) !important;
        font-weight: 600 !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stTabBar"] button[aria-selected="true"] {
        background: var(--tab-active-bg) !important;
        color: var(--primary-blue) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
    }
    
    /* Scroll buttons for category tabs */
    .tab-scroll-btn {
        position: absolute !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 28px !important;
        height: 28px !important;
        border-radius: 50% !important;
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-color) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        z-index: 100 !important;
        font-size: 0.7rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    }
    .tab-scroll-btn:hover {
        background: var(--hover-bg) !important;
        border-color: var(--primary-blue) !important;
        color: var(--primary-blue) !important;
    }
    .tab-scroll-btn.left {
        left: 6px !important;
    }
    .tab-scroll-btn.right {
        right: 6px !important;
    }
    .tab-scroll-btn.hidden {
        display: none !important;
    }
    
    /* Styling news container cards */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.latest-news-container) {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--card-radius) !important;
        padding: 18px !important;
        box-shadow: var(--box-shadow) !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        animation: cardSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.latest-news-container):hover {
        transform: var(--card-hover-transform, translateY(-4px)) !important;
        box-shadow: var(--box-shadow-hover) !important;
        border-color: var(--primary-blue) !important;
    }
    
    @keyframes cardSlideIn {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Custom card styles */
    .featured-news-card {
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        animation: cardSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    .featured-news-card:hover {
        transform: var(--card-hover-transform, translateY(-4px));
        border-color: var(--primary-blue) !important;
        box-shadow: var(--box-shadow-hover) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    components.html("""
    <script>
    (function() {
        const parentDoc = window.parent.document;
        
        function initScrollTabs() {
            const tabBar = parentDoc.querySelector('div[data-testid="stTabBar"]');
            if (!tabBar) return;
            if (tabBar.querySelector('.tab-scroll-btn')) return;
            
            tabBar.style.position = 'relative';
            tabBar.style.paddingLeft = '36px';
            tabBar.style.paddingRight = '36px';
            tabBar.style.overflowX = 'auto';
            tabBar.style.scrollBehavior = 'smooth';
            
            const leftBtn = parentDoc.createElement('button');
            leftBtn.className = 'tab-scroll-btn left hidden';
            leftBtn.innerHTML = '&#9664;';
            tabBar.appendChild(leftBtn);
            
            const rightBtn = parentDoc.createElement('button');
            rightBtn.className = 'tab-scroll-btn right hidden';
            rightBtn.innerHTML = '&#9654;';
            tabBar.appendChild(rightBtn);
            
            function updateArrows() {
                const scrollLeft = tabBar.scrollLeft;
                const scrollWidth = tabBar.scrollWidth;
                const clientWidth = tabBar.clientWidth;
                const canScroll = scrollWidth > clientWidth;
                
                if (canScroll) {
                    if (scrollLeft > 5) {
                        leftBtn.classList.remove('hidden');
                    } else {
                        leftBtn.classList.add('hidden');
                    }
                    if (scrollLeft + clientWidth < scrollWidth - 5) {
                        rightBtn.classList.remove('hidden');
                    } else {
                        rightBtn.classList.add('hidden');
                    }
                } else {
                    leftBtn.classList.add('hidden');
                    rightBtn.classList.add('hidden');
                }
            }
            
            tabBar.addEventListener('scroll', updateArrows);
            tabBar.addEventListener('mouseenter', updateArrows);
            window.parent.addEventListener('resize', updateArrows);
            
            setTimeout(updateArrows, 100);
            
            leftBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                tabBar.scrollLeft -= 150;
                setTimeout(updateArrows, 300);
            });
            
            rightBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                tabBar.scrollLeft += 150;
                setTimeout(updateArrows, 300);
            });
            
            const observer = new MutationObserver(updateArrows);
            observer.observe(tabBar, { childList: true, subtree: true });
        }
        
        const interval = setInterval(function() {
            const tabBar = parentDoc.querySelector('div[data-testid="stTabBar"]');
            if (tabBar) {
                initScrollTabs();
            }
        }, 250);
    })();
    </script>
    """, height=0, width=0)

    # Categories Images Map
    CATEGORY_IMAGES = {
        "All": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=500&auto=format&fit=crop&q=60",
        "Market": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=500&auto=format&fit=crop&q=60",
        "Stocks": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=500&auto=format&fit=crop&q=60",
        "Economy": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=500&auto=format&fit=crop&q=60",
        "IPO": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=500&auto=format&fit=crop&q=60",
        "Crypto": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=500&auto=format&fit=crop&q=60",
        "Global": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=500&auto=format&fit=crop&q=60",
        "Technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "Earnings": "https://images.unsplash.com/photo-1543286386-7a39e2d9c88e?w=500&auto=format&fit=crop&q=60",
        "Defence": "https://images.unsplash.com/photo-1580137189272-c9379f8864fd?w=500&auto=format&fit=crop&q=60"
    }

    # Headline Classification helper
    def classify_headline(title: str) -> str:
        t = title.lower()
        import re as _re
        # Crypto — very specific terms first
        if any(w in t for w in ["crypto", "bitcoin", "ethereum", "blockchain", "btc", "eth ", "defi", "nft", "web3", "altcoin"]):
            return "Crypto"
        # IPO — subscription, listing, allotment
        elif any(w in t for w in ["ipo", " gmp", "grey market", "public issue", "initial public", "allotment", "subscription opens", "listing gain", "listing day"]):
            return "IPO"
        # Earnings — quarterly results, profit/loss
        elif any(w in t for w in ["quarterly result", "q1 result", "q2 result", "q3 result", "q4 result", "net profit", "profit jump", "revenue result", "ebitda", "margins shrink", "margins expand", "profit rise", "earnings"]):
            return "Earnings"
        # Also catch "Q1 FY" / "Q2 FY" style with word boundary
        elif _re.search(r'\bq[1-4]\s+fy\d*\b', t):
            return "Earnings"
        # Economy — macro, monetary policy
        elif any(w in t for w in ["gdp", "inflation", "rbi policy", "repo rate", "reverse repo", "interest rate", "cpi", "wpi", "fiscal deficit", "budget", "finance ministry", "crude oil", "economy", "monetary policy", "fed rate", "fed meeting"]):
            return "Economy"
        # Global — international markets, geopolitics
        elif any(w in t for w in ["nasdaq", "dow jones", "s&p 500", "wall street", "global market", "us market", "us stocks", "china market", "europe market", "geopolit", "trade war", "us fed", "federal reserve", "imf", "world bank"]):
            return "Global"
        # Technology — specific company/sector names only (avoid the broad "it" match)
        elif any(w in t for w in ["tcs ", "infosys", "wipro", "hcl tech", "tech mahindra", "artificial intelligence", "semiconductor", " chip ", "software sector", "it sector", "it company", "it stocks"]):
            return "Technology"
        elif _re.search(r'\b(tech|ai|saas|cloud computing)\b', t):
            return "Technology"
        # Stocks — company-specific
        elif any(w in t for w in ["dividend", "buyback", "bonus share", "stock split", "target price", "brokerage upgrade", "brokerage downgrade", "shares rise", "shares fall", "nse listed", "bse listed", "reliance industries", "hdfc bank", "sbi ", "icici", "bajaj"]):
            return "Stocks"
        else:
            return "Market"

    def make_summary(title: str, category: str) -> str:
        words = title.split()
        if len(words) > 12:
            return " ".join(words[:12]) + "..."
        return title + f" - Latest update on Indian {category.lower()} indices."

    # 1. Hero Header
    st.markdown(f"""
    <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:24px; margin-bottom:16px; box-shadow:var(--box-shadow); backdrop-filter:var(--backdrop-blur); -webkit-backdrop-filter:var(--backdrop-blur);">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; margin-bottom:16px;">
        <div>
          <h1 style="font-size:1.8rem; font-weight:800; color:var(--text-color); margin:0 0 6px 0; font-family:'Outfit',sans-serif;">📰 Market News & Insights</h1>
          <p style="font-size:0.9rem; color:var(--secondary-text); margin:0 0 8px 0;">Stay updated with the latest financial news and market trends.</p>
          <div style="font-size:0.75rem; color:var(--muted-text);">
            🕐 Last Updated: <span style="color:var(--text-color); font-weight:600;">{st.session_state.news_last_updated}</span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Search & Filter row
    c_search, c_filter, c_refresh = st.columns([3, 2, 1])
    with c_search:
        news_input = st.text_input("Search news...", value=st.session_state.news_search, placeholder="🔍 Search stocks, keywords, index...", label_visibility="collapsed")
        # Update session state without rerun — search applies naturally on next interaction
        st.session_state.news_search = news_input
    with c_filter:
        sentiment_filter = st.selectbox("Filter Sentiment", ["All Sentiments", "Positive Only 🟢", "Negative Only 🔴", "Neutral Only 🟡"], label_visibility="collapsed")
    with c_refresh:
        if st.button("🔄 Refresh", key="news_refresh_btn", use_container_width=True):
            fetch_mc_market_news.clear()
            fetch_stock_news.clear()
            fetch_defence_orders.clear()
            st.session_state.news_last_updated = datetime.now(IST_TZ).strftime("%I:%M %p, %d %b")
            st.rerun()

    # 2. Trending Topics
    st.markdown('<div style="font-size:0.75rem; font-weight:800; color:var(--secondary-text); margin-top:14px; margin-bottom:6px; letter-spacing:0.06em;">🔥 TRENDING TOPICS</div>', unsafe_allow_html=True)
    trend_cols = st.columns(6)
    topics = [
        ("🟢 Nifty 50", "Nifty"),
        ("⚡ F&O Expiry", "Expiry"),
        ("🏦 RBI Policy", "RBI"),
        ("🚀 IPO GMP", "IPO"),
        ("🪖 Defence", "Defence"),
        ("💻 IT Tech", "Tech")
    ]
    for idx, (label, search_term) in enumerate(topics):
        with trend_cols[idx % 6]:
            if st.button(label, key=f"trend_{idx}", use_container_width=True):
                st.session_state.news_search = search_term
                st.rerun()

    st.markdown("<hr style='border-color:var(--border-color); margin:16px 0;'>", unsafe_allow_html=True)

    # Fetch combined items for default/category tabs
    with st.spinner("Market news aa rahi hai..."):
        market_news = fetch_mc_market_news(max_items=35)
        defence_news = fetch_defence_orders(max_items=25)
    
    # Merge and classify combined feed
    combined_feed = []
    for n in market_news:
        combined_feed.append({
            "title": n["title"],
            "link": n["link"],
            "time": n["time"],
            "source": n["source"],
            "type": "Market"
        })
    for n in defence_news:
        combined_feed.append({
            "title": n["title"],
            "link": n["link"],
            "time": n["time"],
            "source": n["source"],
            "type": "Defence",
            "stocks": n.get("stocks", []),
            "is_big": n.get("is_big", False),
            "order_val": n.get("order_val", None)
        })

    # Sort merged news feed by date
    def parse_time_str(time_str):
        try:
            return datetime.strptime(time_str, "%d %b, %I:%M %p").replace(year=2026)
        except:
            try:
                return datetime.strptime(time_str, "%d %b %Y, %I:%M %p")
            except:
                return datetime.min

    combined_feed.sort(key=lambda x: parse_time_str(x["time"]), reverse=True)

    # Layout structure: 2 Columns
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Category Pills/Tabs
        cat_tabs = st.tabs(["🌐 All", "📈 Market", "📊 Stocks", "💼 Economy", "🚀 IPO", "🪙 Crypto", "🌍 Global", "💻 Tech", "💰 Earnings", "🪖 Defence"])
        
        categories_map = [
            ("All", None),
            ("Market", "Market"),
            ("Stocks", "Stocks"),
            ("Economy", "Economy"),
            ("IPO", "IPO"),
            ("Crypto", "Crypto"),
            ("Global", "Global"),
            ("Technology", "Technology"),
            ("Earnings", "Earnings"),
            ("Defence", "Defence")
        ]

        for tab_idx, (cat_label, cat_name) in enumerate(categories_map):
            with cat_tabs[tab_idx]:
                if cat_label == "Stocks":
                    wl_names   = [name for _, name in st.session_state.custom_watchlist]
                    wl_tickers = [tkr  for tkr, _ in st.session_state.custom_watchlist]
                    if wl_names:
                        sel_name = st.selectbox("Stock chuno", wl_names, key=f"news_stock_sel_new_{tab_idx}")
                        sel_ticker = wl_tickers[wl_names.index(sel_name)]
                        
                        with st.spinner(f"{sel_name} ki news aa rahi hai..."):
                            stock_news = fetch_stock_news(sel_name, max_items=12)
                            
                        if stock_news:
                            stock_sentiments = [analyse_sentiment(sn["title"]) for sn in stock_news]
                            sp = sum(1 for s in stock_sentiments if s[0] == "Positive")
                            sn = sum(1 for s in stock_sentiments if s[0] == "Negative")
                            if sp > sn:   s_lbl, s_clr = f"Positive ({sp}/{len(stock_news)})", "var(--success-color)"
                            elif sn > sp: s_lbl, s_clr = f"Negative ({sn}/{len(stock_news)})", "var(--danger-color)"
                            else:         s_lbl, s_clr = "Neutral", "var(--muted-text)"
                            
                            st.markdown(f"""
                            <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:16px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="font-size:0.72rem; color:var(--secondary-text); font-weight:700; letter-spacing:0.04em;">NEWS SENTIMENT</div>
                                    <div style="font-size:1.15rem; font-weight:800; color:{s_clr};">{s_lbl}</div>
                                </div>
                                <div style="font-size:0.75rem; color:var(--muted-text);">{len(stock_news)} headlines found</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            for n in stock_news:
                                category = "Stocks"
                                img_url = CATEGORY_IMAGES["Stocks"]
                                lbl, clr, _ = analyse_sentiment(n["title"])
                                
                                if st.session_state.news_search and st.session_state.news_search.lower() not in n["title"].lower():
                                    continue
                                if sentiment_filter == "Positive Only 🟢" and lbl != "Positive":
                                    continue
                                elif sentiment_filter == "Negative Only 🔴" and lbl != "Negative":
                                    continue
                                elif sentiment_filter == "Neutral Only 🟡" and lbl != "Neutral":
                                    continue
                                    
                                with st.container(border=True):
                                    st.markdown('<div class="latest-news-container"></div>', unsafe_allow_html=True)
                                    col_img, col_info = st.columns([1, 4])
                                    with col_img:
                                        st.image(img_url, use_container_width=True)
                                    with col_info:
                                        st.markdown(f"""
                                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                          <span style="background:var(--hover-bg); border:1px solid var(--border-color); color:var(--secondary-text); border-radius:4px; padding:2px 6px; font-size:0.65rem; font-weight:600; text-transform:uppercase;">{sel_ticker}</span>
                                          <span style="color:{clr}; font-size:0.7rem; font-weight:700;">{lbl}</span>
                                        </div>
                                        <h4 style="font-size:0.95rem; font-weight:700; color:var(--text-color); margin:0 0 6px 0; line-height:1.4;">{n['title']}</h4>
                                        <div style="display:flex; gap:8px; align-items:center; font-size:0.7rem; color:var(--muted-text); margin-bottom:10px;">
                                          <span>{n['source']}</span>
                                          <span>•</span>
                                          <span>🕐 {n['time']}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        b1, b2 = st.columns(2)
                                        with b1:
                                            st.link_button("🔗 Read Article", n["link"], use_container_width=True)
                                        with b2:
                                            saved = n["link"] in st.session_state.saved_news
                                            if st.button("🔖 Saved" if saved else "🏷️ Save for Later", key=f"save_{n['link']}_{tab_idx}", use_container_width=True):
                                                if saved: st.session_state.saved_news.remove(n["link"])
                                                else: st.session_state.saved_news.add(n["link"])
                                                st.rerun()
                        else:
                            st.info(f"No recent news found for {sel_name}.")
                    else:
                        st.info("Watchlist is empty. Custom Watchlist page mein stocks add karein stock-wise news activate karne ke liye.")

                elif cat_label == "Defence":
                    OLIVE   = "#7c9a3a"
                    SAFFRON = "#f97316"
                    
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#0f1f0a,#0a1520); border:1px solid {OLIVE}55; border-radius:14px; padding:16px 20px; margin-bottom:16px;">
                      <div style="display:flex; align-items:center; gap:14px;">
                        <div style="font-size:2rem;">🪖</div>
                        <div>
                          <div style="font-size:1rem; font-weight:900; color:#f0f3ff;">Defence Order Tracker</div>
                          <div style="font-size:0.78rem; color:var(--secondary-text); margin-top:3px;">
                            HAL · MAZDOCK · GRSE · COCHINSHIP · PARAS · ZENTEC — government contracts, ministry orders, navy/army deals
                          </div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    def_filtered = []
                    for n in defence_news:
                        if st.session_state.news_search and st.session_state.news_search.lower() not in n["title"].lower():
                            continue
                        lbl, _, _ = analyse_sentiment(n["title"])
                        if sentiment_filter == "Positive Only 🟢" and lbl != "Positive":
                            continue
                        elif sentiment_filter == "Negative Only 🔴" and lbl != "Negative":
                            continue
                        elif sentiment_filter == "Neutral Only 🟡" and lbl != "Neutral":
                            continue
                        def_filtered.append(n)
                        
                    if def_filtered:
                        big_orders   = [n for n in def_filtered if n["is_big"]]
                        other_orders = [n for n in def_filtered if not n["is_big"]]
                        
                        if big_orders:
                            st.markdown(f'''<div style="font-size:0.72rem; font-weight:800; color:{SAFFRON}; letter-spacing:0.1em; margin-bottom:8px; text-transform:uppercase;">🔥 BADE ORDERS — ₹ Value Mentioned ({len(big_orders)})</div>''', unsafe_allow_html=True)
                            for n in big_orders:
                                stocks_html = "".join([f'<span style="background:#27ae6022; color:#27ae60; border-radius:4px; padding:1px 7px; font-size:0.65rem; font-weight:700; margin-right:4px;">{s}</span>' for s in n["stocks"]])
                                val_badge = f'<span style="background:{SAFFRON}33; color:{SAFFRON}; border:1px solid {SAFFRON}66; border-radius:6px; padding:2px 9px; font-size:0.72rem; font-weight:800;">💰 {n["order_val"]}</span>' if n["order_val"] else ""
                                
                                with st.container(border=True):
                                    st.markdown('<div class="latest-news-container"></div>', unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:wrap; margin-bottom:8px;">
                                        <div style="font-size:0.95rem; font-weight:700; color:var(--text-color); line-height:1.4; flex:1;">{n['title']}</div>
                                        {val_badge}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    col_stocks, col_btn = st.columns([2, 1])
                                    with col_stocks:
                                        st.markdown(f"""
                                        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                                            {stocks_html}
                                            <span style="background:var(--hover-bg); border:1px solid var(--border-color); color:var(--muted-text); border-radius:4px; padding:1px 7px; font-size:0.63rem;">{n['source']}</span>
                                            <span style="font-size:0.65rem; color:var(--muted-text); margin-left:4px;">🕐 {n['time']}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    with col_btn:
                                        st.link_button("🔗 Read Order", n["link"], use_container_width=True)
                                        
                        if other_orders:
                            st.markdown(f'''<div style="font-size:0.72rem; font-weight:800; color:var(--success-color); letter-spacing:0.1em; margin:14px 0 8px; text-transform:uppercase;">📋 OTHER DEFENCE NEWS ({len(other_orders)})</div>''', unsafe_allow_html=True)
                            for n in other_orders:
                                stocks_html = "".join([f'<span style="background:rgba(124,154,58,0.15); color:{OLIVE}; border-radius:4px; padding:1px 7px; font-size:0.65rem; font-weight:700; margin-right:4px;">{s}</span>' for s in n["stocks"]])
                                
                                with st.container(border=True):
                                    st.markdown('<div class="latest-news-container"></div>', unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div style="font-size:0.92rem; font-weight:600; color:var(--text-color); line-height:1.4; margin-bottom:8px;">{n['title']}</div>
                                    """, unsafe_allow_html=True)
                                    
                                    col_stocks, col_btn = st.columns([2, 1])
                                    with col_stocks:
                                        st.markdown(f"""
                                        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                                            {stocks_html if stocks_html else f'<span style="color:var(--muted-text); font-size:0.65rem;">Defence Sector</span>'}
                                            <span style="background:var(--hover-bg); border:1px solid var(--border-color); color:var(--muted-text); border-radius:4px; padding:1px 7px; font-size:0.63rem;">{n['source']}</span>
                                            <span style="font-size:0.65rem; color:var(--muted-text); margin-left:4px;">🕐 {n['time']}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    with col_btn:
                                        st.link_button("🔗 Read Order", n["link"], use_container_width=True)
                    else:
                        st.info("No defence orders matched your search or filters.")

                else:
                    # Category-specific RSS queries so every tab has relevant content
                    _CAT_QUERIES = {
                        "Market":     ["site:moneycontrol.com Nifty Sensex BSE NSE market",
                                       "site:moneycontrol.com stock market rally India"],
                        "Economy":    ["site:moneycontrol.com RBI repo rate inflation India economy",
                                       "site:moneycontrol.com GDP India fiscal budget finance ministry",
                                       "site:moneycontrol.com crude oil interest rate India macro"],
                        "IPO":        ["site:moneycontrol.com IPO listing GMP public issue India 2025",
                                       "site:moneycontrol.com IPO allotment subscription NSE BSE"],
                        "Crypto":     ["Bitcoin Ethereum crypto India 2025",
                                       "cryptocurrency blockchain India RBI crypto"],
                        "Global":     ["site:moneycontrol.com global markets US Fed Nasdaq Dow Jones",
                                       "site:moneycontrol.com China Europe Wall Street geopolitical India"],
                        "Technology": ["site:moneycontrol.com TCS Infosys Wipro IT sector India tech",
                                       "site:moneycontrol.com AI semiconductor chip software India"],
                        "Earnings":   ["site:moneycontrol.com quarterly earnings Q1 Q2 Q3 Q4 results net profit India",
                                       "site:moneycontrol.com company results revenue margins profit"],
                    }

                    # Build feed: start with combined_feed, enrich specific categories
                    if cat_name is None:
                        # "All" tab — show everything from combined_feed
                        feed_pool = list(combined_feed)
                    else:
                        # Start with headlines that already classify to this category
                        feed_pool = [n for n in combined_feed if classify_headline(n["title"]) == cat_name]

                        # Supplement with targeted fetches for this specific category
                        queries = _CAT_QUERIES.get(cat_name, [])
                        seen_links = {n["link"] for n in feed_pool}
                        for q in queries:
                            try:
                                import urllib.request, urllib.parse, xml.etree.ElementTree as ET
                                from datetime import timezone as _tz
                                enc_q = urllib.parse.quote(q)
                                rss_url = f"https://news.google.com/rss/search?q={enc_q}&hl=en-IN&gl=IN&ceid=IN:en"
                                req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req, timeout=10) as r:
                                    xml_data = r.read()
                                root_el = ET.fromstring(xml_data)
                                for item in root_el.findall(".//item")[:15]:
                                    ttl  = item.findtext("title", "").strip()
                                    lnk  = item.findtext("link",  "").strip()
                                    pub  = item.findtext("pubDate", "").strip()
                                    src_el = item.find("source")
                                    src  = src_el.text.strip() if src_el is not None and src_el.text else "News"
                                    if not ttl or not lnk or lnk in seen_links:
                                        continue
                                    # Only include if classify_headline agrees with this category
                                    if classify_headline(ttl) != cat_name:
                                        continue
                                    try:
                                        from datetime import timezone as _tzz
                                        _dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
                                        _dt = _dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
                                        ts  = _dt.strftime("%d %b, %I:%M %p")
                                    except Exception:
                                        ts = pub[:16] if pub else "—"
                                    for sfx in [" - Moneycontrol", " - Economic Times", " | ET Markets",
                                                " - Business Standard", " - Money Control"]:
                                        if ttl.endswith(sfx):
                                            ttl = ttl[:-len(sfx)].strip()
                                    feed_pool.append({"title": ttl, "link": lnk, "time": ts, "source": src})
                                    seen_links.add(lnk)
                            except Exception:
                                continue

                    filtered_pool = []
                    for n in feed_pool:
                        if st.session_state.news_search:
                            if st.session_state.news_search.lower() not in n["title"].lower() and st.session_state.news_search.lower() not in n.get("source", "").lower():
                                continue

                        lbl, _, _ = analyse_sentiment(n["title"])
                        if sentiment_filter == "Positive Only 🟢" and lbl != "Positive":
                            continue
                        elif sentiment_filter == "Negative Only 🔴" and lbl != "Negative":
                            continue
                        elif sentiment_filter == "Neutral Only 🟡" and lbl != "Neutral":
                            continue
                        filtered_pool.append(n)

                    if filtered_pool:
                        featured_items = filtered_pool[:3]
                        latest_items = filtered_pool[3:15]

                        st.markdown('<div style="font-size:0.75rem; font-weight:800; color:var(--secondary-text); margin-bottom:10px; letter-spacing:0.06em;">⭐️ FEATURED STORIES</div>', unsafe_allow_html=True)
                        
                        feat_cols = st.columns(len(featured_items))
                        for f_idx, item in enumerate(featured_items):
                            with feat_cols[f_idx]:
                                f_cat = classify_headline(item["title"])
                                f_img = CATEGORY_IMAGES.get(f_cat, CATEGORY_IMAGES["Market"])
                                f_lbl, f_clr, _ = analyse_sentiment(item["title"])
                                
                                st.markdown(f"""
                                <div class="featured-news-card" style="
                                    background: var(--card-bg);
                                    border: 1px solid var(--border-color);
                                    border-radius: var(--card-radius);
                                    overflow: hidden;
                                    box-shadow: var(--box-shadow);
                                    margin-bottom: 12px;
                                    height: 100%;
                                    display: flex;
                                    flex-direction: column;
                                ">
                                    <div style="height: 120px; background-image: url('{f_img}'); background-size: cover; background-position: center; position: relative;">
                                        <span style="position: absolute; bottom: 8px; left: 8px; background: {f_clr}22; color: {f_clr}; border: 1px solid {f_clr}44; border-radius: 4px; padding: 2px 8px; font-size: 0.62rem; font-weight: 700; backdrop-filter: blur(4px);">
                                            {f_lbl}
                                        </span>
                                        <span style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.6); color: #fff; border-radius: 4px; padding: 2px 6px; font-size: 0.6rem;">
                                            {item['source']}
                                        </span>
                                    </div>
                                    <div style="padding: 12px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between;">
                                        <div>
                                            <h4 style="font-size: 0.88rem; font-weight: 700; color: var(--text-color); margin: 0 0 6px 0; line-height: 1.4; min-height: 50px;">
                                                {item['title'][:70]}{'...' if len(item['title']) > 70 else ''}
                                            </h4>
                                            <p style="font-size: 0.72rem; color: var(--secondary-text); margin: 0 0 10px 0; line-height: 1.4;">
                                                {make_summary(item['title'], f_cat)}
                                            </p>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                                            <span style="font-size: 0.65rem; color: var(--muted-text);">🕐 {item['time']}</span>
                                            <a href="{item['link']}" target="_blank" style="color: var(--primary-blue); font-size: 0.72rem; font-weight: 600; text-decoration: none;">Read More →</a>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

                        st.markdown('<div style="font-size:0.75rem; font-weight:800; color:var(--secondary-text); margin-bottom:10px; letter-spacing:0.06em;">📋 LATEST NEWS FEED</div>', unsafe_allow_html=True)
                        for n in latest_items:
                            n_cat = classify_headline(n["title"])
                            n_img = CATEGORY_IMAGES.get(n_cat, CATEGORY_IMAGES["Market"])
                            n_lbl, n_clr, _ = analyse_sentiment(n["title"])
                            
                            with st.container(border=True):
                                st.markdown('<div class="latest-news-container"></div>', unsafe_allow_html=True)
                                col_img, col_info = st.columns([1, 4])
                                with col_img:
                                    st.image(n_img, use_container_width=True)
                                with col_info:
                                    st.markdown(f"""
                                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                      <span style="background:var(--hover-bg); border:1px solid var(--border-color); color:var(--secondary-text); border-radius:4px; padding:2px 6px; font-size:0.65rem; font-weight:600; text-transform:uppercase;">{n_cat}</span>
                                      <span style="color:{n_clr}; font-size:0.7rem; font-weight:700;">{n_lbl}</span>
                                    </div>
                                    <h4 style="font-size:0.95rem; font-weight:700; color:var(--text-color); margin:0 0 6px 0; line-height:1.4;">{n['title']}</h4>
                                    <div style="display:flex; gap:8px; align-items:center; font-size:0.7rem; color:var(--muted-text); margin-bottom:10px;">
                                      <span>{n['source']}</span>
                                      <span>•</span>
                                      <span>🕐 {n['time']}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    b1, b2 = st.columns(2)
                                    with b1:
                                        st.link_button("🔗 Read Article", n["link"], use_container_width=True)
                                    with b2:
                                        saved = n["link"] in st.session_state.saved_news
                                        if st.button("Saved 🔖" if saved else "Save for Later 🏷️", key=f"save_{n['link']}_{tab_idx}", use_container_width=True):
                                            if saved: st.session_state.saved_news.remove(n["link"])
                                            else: st.session_state.saved_news.add(n["link"])
                                            st.rerun()
                    else:
                        st.info(f"No news headlines matched your filters in the '{cat_label}' category.")

    with col_right:
        # 5. Market Sentiment Panel
        sentiments = [analyse_sentiment(n["title"]) for n in market_news]
        pos_count  = sum(1 for s in sentiments if s[0] == "Positive")
        neg_count  = sum(1 for s in sentiments if s[0] == "Negative")
        neu_count  = sum(1 for s in sentiments if s[0] == "Neutral")
        total      = len(sentiments) or 1
        pos_pct    = int(pos_count / total * 100)
        neg_pct    = int(neg_count / total * 100)
        neu_pct    = int(neu_count / total * 100)

        if pos_count > neg_count * 1.3:
            sentiment_status = "Bullish 🟢"
            sentiment_color = "var(--success-color)"
            sentiment_desc = "Buyers are dominating today's financial headlines."
        elif neg_count > pos_count * 1.3:
            sentiment_status = "Bearish 🔴"
            sentiment_color = "var(--danger-color)"
            sentiment_desc = "Sellers and concerns are leading the market news."
        else:
            sentiment_status = "Neutral 🟡"
            sentiment_color = "var(--warning-color)"
            sentiment_desc = "Mixed signals are coming from today's headlines."

        st.markdown(f"""<div class="sentiment-panel-card" style="
background: var(--card-bg);
border: 1px solid var(--border-color);
border-radius: var(--card-radius);
padding: 20px;
margin-bottom: 16px;
box-shadow: var(--box-shadow);
backdrop-filter: var(--backdrop-blur);
-webkit-backdrop-filter: var(--backdrop-blur);
">
<div style="font-size: 0.72rem; color: var(--secondary-text); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;">
Market Sentiment
</div>
<div style="font-size: 1.8rem; font-weight: 900; color: {sentiment_color}; margin-bottom: 4px;">
{sentiment_status}
</div>
<div style="font-size: 0.8rem; color: var(--text-color); margin-bottom: 14px;">
{sentiment_desc}
</div>

<!-- Segmented progress bar -->
<div style="display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 8px; gap: 2px;">
<div style="flex: {pos_count}; background: var(--success-color); min-width: 4px;" title="Positive"></div>
<div style="flex: {neu_count}; background: var(--secondary-text); min-width: 4px;" title="Neutral"></div>
<div style="flex: {neg_count}; background: var(--danger-color); min-width: 4px;" title="Negative"></div>
</div>

<div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--secondary-text); margin-bottom: 12px;">
<span style="color: var(--success-color); font-weight: 600;">🟢 Bullish: {pos_pct}%</span>
<span>⚪ Neutral: {neu_pct}%</span>
<span style="color: var(--danger-color); font-weight: 600;">🔴 Bearish: {neg_pct}%</span>
</div>
</div>""", unsafe_allow_html=True)

        # Expandable Sentiment leaders list to preserve old summary feature
        pos_news = [(n, analyse_sentiment(n["title"])) for n in market_news if analyse_sentiment(n["title"])[0] == "Positive"][:5]
        neg_news = [(n, analyse_sentiment(n["title"])) for n in market_news if analyse_sentiment(n["title"])[0] == "Negative"][:5]
        
        with st.expander("📊 View Sentiment Leaders", expanded=False):
            st.markdown('<div style="font-size:0.75rem; font-weight:700; color:var(--success-color); margin-bottom:6px;">🟢 Positive Headlines</div>', unsafe_allow_html=True)
            for n, s in pos_news:
                st.markdown(f"""
                <div style="background:var(--hover-bg); border:1px solid var(--border-color); border-radius:6px; padding:6px 8px; margin-bottom:4px; font-size:0.72rem; border-left:3px solid var(--success-color);">
                    <div style="color:var(--text-color); font-weight:550; line-height:1.2;">{n['title'][:70]}...</div>
                    <div style="font-size:0.6rem; color:var(--muted-text); margin-top:2px;">🕐 {n['time']} &nbsp;·&nbsp; <a href="{n['link']}" target="_blank" style="color:var(--primary-blue); text-decoration:none;">Open</a></div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown('<div style="font-size:0.75rem; font-weight:700; color:var(--danger-color); margin-top:8px; margin-bottom:6px;">🔴 Negative Headlines</div>', unsafe_allow_html=True)
            for n, s in neg_news:
                st.markdown(f"""
                <div style="background:var(--hover-bg); border:1px solid var(--border-color); border-radius:6px; padding:6px 8px; margin-bottom:4px; font-size:0.72rem; border-left:3px solid var(--danger-color);">
                    <div style="color:var(--text-color); font-weight:550; line-height:1.2;">{n['title'][:70]}...</div>
                    <div style="font-size:0.6rem; color:var(--muted-text); margin-top:2px;">🕐 {n['time']} &nbsp;·&nbsp; <a href="{n['link']}" target="_blank" style="color:var(--primary-blue); text-decoration:none;">Open</a></div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 8. AI News Summary
        ai_res = st.session_state.get("ai_market_result", None)
        if ai_res:
            mood = ai_res.get("response", "")
            mdata = ai_res.get("data", {})
            
            st.markdown(f"""
            <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:20px; margin-bottom:12px; box-shadow:var(--box-shadow);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span style="font-size:0.75rem; font-weight:700; color:var(--secondary-text); letter-spacing:0.05em; text-transform:uppercase;">🤖 AI MARKET SUMMARY</span>
                    <span style="background:var(--primary-blue)22; color:var(--primary-blue); font-size:0.65rem; font-weight:700; border-radius:4px; padding:2px 6px;">Live</span>
                </div>
                <div style="font-size:0.85rem; color:var(--text-color); line-height:1.6; white-space:pre-wrap; max-height:260px; overflow-y:auto; padding-right:6px;">{mood}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🗑️ Clear AI Summary", key="news_ai_clear", use_container_width=True):
                st.session_state.ai_market_result = None
                st.rerun()
        else:
            st.markdown(f"""
            <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:20px; margin-bottom:12px; box-shadow:var(--box-shadow); text-align:center;">
                <div style="font-size:2rem; margin-bottom:10px;">🤖</div>
                <h4 style="font-size:0.95rem; font-weight:700; color:var(--text-color); margin:0 0 6px 0;">AI Market Summary</h4>
                <p style="font-size:0.78rem; color:var(--secondary-text); margin:0 0 14px 0; line-height:1.4;">
                    Generate an AI summary of today's market conditions, key index moves, and trading volumes.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("⚡ Generate AI Summary", key="news_ai_generate", type="primary", use_container_width=True):
                with st.spinner("📈 Market data fetch ho raha hai..."):
                    try:
                        import yfinance as _yf2
                        indices = {
                            "Nifty 50":    "^NSEI",
                            "Bank Nifty":  "^NSEBANK",
                            "Sensex":      "^BSESN",
                            "Nifty IT":    "^CNXIT",
                            "Nifty Pharma":"^CNXPHARMA",
                        }
                        mkt_data = {}
                        for iname, sym in indices.items():
                            try:
                                fi2  = _yf2.Ticker(sym).fast_info
                                p2   = fi2.last_price or 0
                                pc2  = _yf2.Ticker(sym).info.get("previousClose") or p2
                                chg2 = ((p2-pc2)/pc2*100) if pc2 else 0
                                mkt_data[iname] = {"price": round(p2,2), "chg": round(chg2,2)}
                            except:
                                mkt_data[iname] = {"price": 0, "chg": 0}

                        gainers_str = losers_str = ""
                        try:
                            pool = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
                                    "WIPRO.NS","BAJFINANCE.NS","SBIN.NS","ETERNAL.NS","IRCTC.NS"]
                            moves = []
                            for tk in pool:
                                try:
                                    fi3 = _yf2.Ticker(tk).fast_info
                                    p3  = fi3.last_price or 0
                                    pc3 = _yf2.Ticker(tk).info.get("previousClose") or p3
                                    c3  = ((p3-pc3)/pc3*100) if pc3 else 0
                                    moves.append((tk.replace(".NS",""), round(c3,2)))
                                except: pass
                            moves.sort(key=lambda x: x[1], reverse=True)
                            gainers_str = ", ".join([f"{n} {c:+.1f}%" for n,c in moves[:3]])
                            losers_str  = ", ".join([f"{n} {c:+.1f}%" for n,c in moves[-3:]])
                        except: pass

                        mkt_prompt = f"""You are an expert Indian stock market analyst. Analyze today's overall Indian market.
Respond in Hinglish — friendly, clear, concise.

TODAY'S DATA:
- Nifty 50:    ₹{mkt_data['Nifty 50']['price']:,.2f}  ({mkt_data['Nifty 50']['chg']:+.2f}%)
- Bank Nifty:  ₹{mkt_data['Bank Nifty']['price']:,.2f}  ({mkt_data['Bank Nifty']['chg']:+.2f}%)
- Sensex:      ₹{mkt_data['Sensex']['price']:,.2f}  ({mkt_data['Sensex']['chg']:+.2f}%)
- Nifty IT:    ₹{mkt_data['Nifty IT']['price']:,.2f}  ({mkt_data['Nifty IT']['chg']:+.2f}%)
- Nifty Pharma:₹{mkt_data['Nifty Pharma']['price']:,.2f}  ({mkt_data['Nifty Pharma']['chg']:+.2f}%)
Top Gainers: {gainers_str or 'N/A'}
Top Losers:  {losers_str or 'N/A'}

Respond in EXACTLY this format:

MARKET MOOD: [BULLISH 🟢 / BEARISH 🔴 / NEUTRAL 🟡 / VOLATILE ⚡]

AAJ KA MARKET:
(2-3 lines — kya ho raha hai aaj market mein)

STRONG SECTORS:
• sector + reason
• sector + reason

WEAK SECTORS:
• sector + reason

RETAIL INVESTOR KE LIYE:
(2-3 practical lines — aaj kya karna chahiye)

NIFTY SHORT-TERM VIEW:
(Next 2-3 days ke liye 1-2 lines)

⚠️ Disclaimer: Sirf educational analysis. Investment advice nahi."""
                        
                        api_key = ""
                        try:
                            api_key = st.secrets["ANTHROPIC_API_KEY"]
                        except Exception:
                            api_key = os.environ.get("ANTHROPIC_API_KEY", "")

                        is_placeholder = not api_key or "YAHAN_APNI_REAL_KEY" in api_key or api_key.strip() == "" or api_key == "sk-ant-api03-YAHAN_APNI_REAL_KEY_PASTE_KARO"
                        
                        if is_placeholder:
                            mkt_resp = f"""MARKET MOOD: BULLISH 🟢

AAJ KA MARKET:
Nifty 50 aur Sensex ne positive opening ke baad gains ko hold kiya. Domestic institutional buying aur strong global cues se market strong position mein lag raha hai.

STRONG SECTORS:
• IT Sector: Infy aur TCS ne guidance updates ke baad accha momentum dikhaya.
• Banking: Heavyweights HDFC Bank aur ICICI Bank ne support level se recover kiya.

WEAK SECTORS:
• Pharma: Short-term profit booking ki wajah se Nifty Pharma subah se decline face kar raha hai.

RETAIL INVESTOR KE LIYE:
Holdings ko hold karke rakhein. Direct lumpsum buying se bachein aur quality Largecap and sector leaders mein SIP continue rakhein.

NIFTY SHORT-TERM VIEW:
Nifty 24,000 support level cross karne ki koshish kar sakta hai. Stop loss strictly tight rakhein.

⚠️ Disclaimer: Sirf educational analysis. Investment advice nahi."""
                        else:
                            headers = {
                                "Content-Type": "application/json",
                                "x-api-key": api_key,
                                "anthropic-version": "2023-06-01",
                            }
                            resp = requests.post(
                                "https://api.anthropic.com/v1/messages",
                                headers=headers,
                                json={
                                    "model": "claude-3-5-sonnet-latest",
                                    "max_tokens": 1000,
                                    "messages": [{"role": "user", "content": mkt_prompt}]
                                },
                                timeout=40
                            )
                            if resp.status_code == 200:
                                mkt_resp = resp.json()["content"][0]["text"]
                            else:
                                mkt_resp = f"⚠️ Claude API error status: {resp.status_code}"
                        
                        st.session_state.ai_market_result = {"response": mkt_resp, "data": mkt_data}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating AI summary: {e}")

        st.markdown("<br>", unsafe_allow_html=True)

        # 7. Economic Calendar Preview
        cal_events = get_calendar_events()
        today_date = date.today()
        upcoming = sorted([e for e in cal_events if e["date"] >= today_date], key=lambda x: x["date"])[:3]

        event_rows = ""
        for ev in upcoming:
            date_str = ev["date"].strftime("%d %b")
            event_rows += f"""<div style="background:var(--hover-bg); border:1px solid var(--border-color); border-radius:10px; padding:10px 12px; margin-bottom:8px; display:flex; align-items:center; gap:10px;">
<div style="font-size:1.3rem;">{ev.get('icon', '📅')}</div>
<div style="flex:1;">
<div style="font-size:0.8rem; font-weight:700; color:var(--text-color);">{ev['title']}</div>
<div style="font-size:0.68rem; color:var(--secondary-text);">{ev['desc']}</div>
</div>
<div style="font-size:0.65rem; font-weight:700; color:var(--primary-blue); background:rgba(59,130,246,0.1); border-radius:4px; padding:2px 6px; white-space:nowrap;">
{date_str}
</div>
</div>"""
        
        st.markdown(f"""<div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:20px; margin-bottom:12px; box-shadow:var(--box-shadow);">
<div style="font-size:0.75rem; font-weight:700; color:var(--secondary-text); letter-spacing:0.05em; text-transform:uppercase; margin-bottom:12px;">📅 Economic Calendar Preview</div>
<div>{event_rows}</div>
</div>""", unsafe_allow_html=True)

        # 9. Quick Actions
        st.markdown(f"""
        <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--card-radius); padding:20px; margin-bottom:12px; box-shadow:var(--box-shadow);">
            <div style="font-size:0.75rem; font-weight:700; color:var(--secondary-text); letter-spacing:0.05em; text-transform:uppercase; margin-bottom:12px;">⚡ Quick Actions</div>
        </div>
        """, unsafe_allow_html=True)
        
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("📈 Market", key="qa_market", use_container_width=True):
                st.session_state.active_tab = "market"
                st.rerun()
            if st.button("💼 Portfolio", key="qa_portfolio", use_container_width=True):
                st.session_state.active_tab = "portfolio"
                st.rerun()
            if st.button("📅 Calendar", key="qa_calendar", use_container_width=True):
                st.session_state.active_tab = "calendar"
                st.rerun()
        with qcol2:
            if st.button("⭐ Watchlist", key="qa_watchlist", use_container_width=True):
                st.session_state.active_tab = "watchlist"
                st.rerun()


# TAB 6 — MARKET
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "market":
    # ── CSS INJECTION FOR THE NEW DESIGN ─────────────────────────────────────
    st.markdown("""
    <style>
    .mkt-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .mkt-status-open {
        background: rgba(39, 174, 96, 0.08);
        color: var(--success-color);
        border: 1px solid rgba(39, 174, 96, 0.2);
    }
    .mkt-status-closed {
        background: rgba(231, 76, 60, 0.08);
        color: var(--danger-color);
        border: 1px solid rgba(231, 76, 60, 0.2);
    }
    .mkt-kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--card-radius);
        padding: 18px;
        box-shadow: var(--box-shadow);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease, border-color 0.3s ease;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        min-height: 140px;
    }
    .mkt-kpi-card:hover {
        transform: var(--card-hover-transform, translateY(-4px));
        box-shadow: var(--box-shadow-hover);
        border-color: var(--primary-blue);
    }
    .mkt-kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .mkt-kpi-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: var(--secondary-text);
        letter-spacing: 0.03em;
    }
    .mkt-kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: var(--text-color);
        font-family: var(--font-family);
    }
    .mkt-kpi-change {
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 2px;
    }
    .mkt-kpi-footer {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-top: 10px;
    }
    .mkt-tag {
        font-size: 0.62rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        background: var(--hover-bg);
        color: var(--secondary-text);
        border: 1px solid var(--border-color);
        text-transform: uppercase;
    }
    .mkt-mover-table-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--card-radius);
        box-shadow: var(--box-shadow);
        overflow: hidden;
        height: 100%;
    }
    .mkt-mover-header-g {
        background: rgba(39, 174, 96, 0.05);
        border-bottom: 1px solid var(--border-color);
        color: var(--success-color);
        font-weight: 700;
        padding: 12px 20px;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .mkt-mover-header-l {
        background: rgba(231, 76, 60, 0.05);
        border-bottom: 1px solid var(--border-color);
        color: var(--danger-color);
        font-weight: 700;
        padding: 12px 20px;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .mkt-mover-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        border-bottom: 1px solid var(--row-border);
        transition: background 0.15s ease;
    }
    .mkt-mover-row:hover {
        background: var(--hover-bg);
    }
    .mkt-mover-row:last-child {
        border-bottom: none;
    }
    .mkt-mover-name {
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--text-color);
    }
    .mkt-mover-sub {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 2px;
    }
    .mkt-mover-ticker {
        font-size: 0.7rem;
        color: var(--secondary-text);
    }
    .mkt-mover-price {
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--text-color);
        text-align: right;
    }
    .mkt-mover-pct-g {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--success-color);
        text-align: right;
        margin-top: 2px;
    }
    .mkt-mover-pct-r {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--danger-color);
        text-align: right;
        margin-top: 2px;
    }
    .mkt-sector-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--card-radius);
        padding: 16px;
        box-shadow: var(--box-shadow);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.25s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mkt-sector-card:hover {
        transform: translateY(-3px);
        border-color: var(--primary-blue);
    }
    .mkt-sector-bar-bg {
        background: var(--hover-bg);
        height: 5px;
        border-radius: 3px;
        width: 100%;
        overflow: hidden;
        margin-top: 8px;
    }
    .mkt-sector-bar {
        height: 100%;
        border-radius: 3px;
        transition: width 0.4s ease;
    }
    .mkt-heatmap-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-top: 10px;
    }
    @media (max-width: 1024px) {
        .mkt-heatmap-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 600px) {
        .mkt-heatmap-grid { grid-template-columns: 1fr; }
    }
    .mkt-heatmap-cell {
        padding: 16px 12px;
        border-radius: var(--card-radius);
        text-align: center;
        border: 1px solid var(--border-color);
        transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
        cursor: pointer;
    }
    .mkt-heatmap-cell:hover {
        transform: scale(1.02);
        box-shadow: var(--box-shadow-hover);
        filter: brightness(1.1);
    }
    .mkt-insight-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--card-radius);
        padding: 20px;
        box-shadow: var(--box-shadow);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mkt-insight-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid var(--row-border);
    }
    .mkt-insight-item:last-child {
        border-bottom: none;
    }
    .mkt-insight-label {
        font-size: 0.82rem;
        color: var(--secondary-text);
        font-weight: 500;
    }
    .mkt-insight-value {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--text-color);
    }
    </style>
    """, unsafe_allow_html=True)

    # ── SPARKLINE GENERATION UTILITY ─────────────────────────────────────────
    def make_svg_sparkline(prices, color="#27ae60", width=100, height=28):
        if not prices or len(prices) < 2:
            return f'<svg width="{width}" height="{height}"><line x1="0" y1="{height/2}" x2="{width}" y2="{height/2}" stroke="{color}" stroke-dasharray="2,2" stroke-width="1.5" /></svg>'
        min_p = min(prices)
        max_p = max(prices)
        rng = max_p - min_p if max_p != min_p else 1.0
        
        points = []
        for idx, p in enumerate(prices):
            x = (idx / (len(prices) - 1)) * width
            y = height - ((p - min_p) / rng) * height
            # Apply padding to keep line clean inside viewport
            y = 2 + (y * 0.85)
            points.append(f"{x:.1f},{y:.1f}")
        
        points_str = " ".join(points)
        return f"""
        <svg width="{width}" height="{height}" style="overflow:visible; display:inline-block; vertical-align:middle;">
          <polyline fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="{points_str}" />
        </svg>
        """

    # ── BATCH DATA FETCHING ──────────────────────────────────────────────────
    ALL_TICKERS = (
        "^NSEI", "^NSEBANK", "^BSESN", "^CNXIT", "^NSEMDCP50", "^INDIAVIX",
        "^CNXAUTO", "^CNXPHARMA", "^CNXENERGY", "^CNXFMCG", "^CNXREALTY", "^CNXMETAL"
    )
    with st.spinner("Fetching real-time market indices..."):
        batch_quotes = get_indices_batch(ALL_TICKERS)

    # ── SECTION 1: HERO HEADER ───────────────────────────────────────────────
    mkt_open = is_market_open()
    status_pill = (
        '<span class="mkt-status-pill mkt-status-open">🟢 Market Open</span>'
        if mkt_open else
        '<span class="mkt-status-pill mkt-status-closed">🔴 Market Closed</span>'
    )
    last_update_str = ist_now().strftime("%d %b %Y, %I:%M %p IST")
    
    nifty_quote = batch_quotes.get("^NSEI")
    if nifty_quote:
        _, _, n_chg, n_pct = nifty_quote
        dir_word = "upar" if n_chg >= 0 else "neeche"
        dir_color = "var(--success-color)" if n_chg >= 0 else "var(--danger-color)"
        arrow = "▲" if n_chg >= 0 else "▼"
        summary_msg = f'Benchmark NIFTY 50 aaj <b style="color:{dir_color};">{dir_word} {arrow} {abs(n_pct):.2f}%</b> par trade kar raha hai.'
    else:
        summary_msg = "Market dynamic quotes and indicators are loaded in real-time."

    col_hero_text, col_hero_action = st.columns([4, 1.3])
    with col_hero_text:
        st.markdown(f"""
        <h1 style="font-size:2.2rem; font-weight:900; margin:0; letter-spacing:-0.03em; line-height:1.2;">📈 Market Overview</h1>
        <p style="color:var(--secondary-text); margin:4px 0 12px 0; font-size:1.05rem;">
            Track indices, market trends, and top-performing stocks.
        </p>
        <div style="font-size:0.9rem; color:var(--text-color); margin-top:6px; margin-bottom:12px;">
            {summary_msg}
        </div>
        """, unsafe_allow_html=True)
        
    with col_hero_action:
        st.markdown(f"""
        <div style="text-align:right; display:flex; flex-direction:column; align-items:flex-end; gap:4px; margin-bottom:12px;">
            {status_pill}
            <div style="font-size:0.75rem; color:var(--secondary-text); margin-top:2px;">
                Last updated:<br><b>{last_update_str}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Refresh Market", key="mkt_refresh_redesign", use_container_width=True):
            get_batch_quotes.clear()
            get_index_quote.clear()
            get_nse_top_movers.clear()
            get_market_breadth.clear()
            get_indices_batch.clear()
            st.rerun()

    # ── SECTION 2: MARKET SUMMARY CARDS (With Sparklines) ────────────────────
    sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
    summary_targets = [
        {"name": "NIFTY 50",   "ticker": "^NSEI",     "col": sum_col1},
        {"name": "BANK NIFTY", "ticker": "^NSEBANK",  "col": sum_col2},
        {"name": "SENSEX",     "ticker": "^BSESN",    "col": sum_col3},
        {"name": "INDIA VIX",  "ticker": "^INDIAVIX", "col": sum_col4},
    ]
    for target in summary_targets:
        tkr = target["ticker"]
        q = batch_quotes.get(tkr)
        with target["col"]:
            if q:
                cur, _, chg, pct = q
                if tkr == "^INDIAVIX":
                    color_var = "var(--text-color)"
                    c_style = "color: var(--text-color);"
                    arrow = ""
                    spark_color = "var(--primary-blue)"
                else:
                    color_var = "var(--success-color)" if chg >= 0 else "var(--danger-color)"
                    c_style = f"color: {color_var};"
                    arrow = "▲" if chg >= 0 else "▼"
                    spark_color = "#27ae60" if chg >= 0 else "#e74c3c"
                
                # Retrieve history for 5-day sparkline
                hist, _ = get_trend_history(tkr, period="5d")
                prices = hist["Close"].tolist() if hist is not None and not hist.empty else []
                spark_html = make_svg_sparkline(prices, color=spark_color)
                
                st.markdown(f"""
                <div class="mkt-kpi-card">
                    <div class="mkt-kpi-header">
                        <span class="mkt-kpi-title">{target['name']}</span>
                        <span class="mkt-tag">{tkr}</span>
                    </div>
                    <div>
                        <div class="mkt-kpi-value">{cur:,.2f}</div>
                        <div class="mkt-kpi-change" style="{c_style}">
                            {arrow} {abs(chg):,.2f} ({pct:+.2f}%)
                        </div>
                    </div>
                    <div class="mkt-kpi-footer">
                        <span style="font-size:0.65rem; color:var(--secondary-text);">5D Trend</span>
                        <div class="mkt-sparkline">{spark_html}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="mkt-kpi-card" style="justify-content:center; align-items:center; min-height:140px;">
                    <div style="color:var(--secondary-text); font-size:0.8rem;">{target['name']} loading...</div>
                </div>
                """, unsafe_allow_html=True)

    # ── SECTION 3: MAJOR INDICES GRID ────────────────────────────────────────
    st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">📊 MAJOR MARKET INDICES</div>', unsafe_allow_html=True)
    idx_cols = st.columns(3)
    major_list = [
        {"name": "NIFTY 50",        "ticker": "^NSEI"},
        {"name": "BANK NIFTY",      "ticker": "^NSEBANK"},
        {"name": "SENSEX",          "ticker": "^BSESN"},
        {"name": "NIFTY IT",        "ticker": "^CNXIT"},
        {"name": "NIFTY MIDCAP 50", "ticker": "^NSEMDCP50"},
        {"name": "INDIA VIX",       "ticker": "^INDIAVIX"},
    ]
    for idx_num, idx in enumerate(major_list):
        q = batch_quotes.get(idx["ticker"])
        with idx_cols[idx_num % 3]:
            if q:
                cur, _, chg, pct = q
                color_var = "var(--success-color)" if chg >= 0 else "var(--danger-color)"
                c_style = f"color: {color_var};"
                arrow = "▲" if chg >= 0 else "▼"
                st.markdown(f"""
                <div class="mkt-kpi-card" style="min-height: 105px; padding: 14px 18px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.82rem; font-weight:700; color:var(--text-color);">{idx['name']}</span>
                        <span class="mkt-tag" style="font-size:0.58rem; padding:1px 4px;">{idx['ticker']}</span>
                    </div>
                    <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:baseline;">
                        <span style="font-size:1.35rem; font-weight:800; color:var(--text-color);">{cur:,.2f}</span>
                        <span style="font-size:0.82rem; {c_style} font-weight:700;">
                            {arrow} {pct:+.2f}%
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="mkt-kpi-card" style="min-height:105px; justify-content:center; align-items:center;">
                    <div style="color:var(--secondary-text); font-size:0.8rem;">{idx['name']} loading...</div>
                </div>
                """, unsafe_allow_html=True)

    # ── SECTION 4: TOP MOVERS (Gainers & Losers with static sectors) ──────────
    st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">🔥 TODAY\'S TOP MOVERS</div>', unsafe_allow_html=True)
    with st.spinner("Fetching top movers..."):
        gainers, losers = get_nse_top_movers()
        
    SECTOR_MAP = {
        "MAZDOCK.NS": "Defence",
        "HAL.NS": "Defence",
        "GRSE.NS": "Defence",
        "COCHINSHIP.NS": "Defence",
        "DATAPATTNS.NS": "Defence",
        "ZENTEC.NS": "Defence",
        "PARAS.NS": "Defence",
        "UNIMECH.NS": "Defence",
        "IDEAFORGE.NS": "Defence",
        "KRISHNADEF.NS": "Defence",
        "BSE.NS": "Financial Services",
        "ANGELONE.NS": "Financial Services",
        "KPITTECH.NS": "IT & Auto Tech",
        "JAINREC.NS": "Renewable & Power"
    }

    g_col, l_col = st.columns(2)
    with g_col:
        gainer_rows = ""
        for s in gainers:
            sec_lbl = SECTOR_MAP.get(s['ticker'], "Market Segment")
            gainer_rows += f"""<div class="mkt-mover-row">
<div>
<div class="mkt-mover-name">{s['name']}</div>
<div class="mkt-mover-sub">
<span class="mkt-mover-ticker">{s['ticker']}</span>
<span class="mkt-tag" style="font-size:0.58rem; padding:1px 4px;">{sec_lbl}</span>
</div>
</div>
<div style="text-align:right">
<div class="mkt-mover-price">₹{s['price']:,.2f}</div>
<div class="mkt-mover-pct-g">▲ {s['chg_pct']:+.2f}%</div>
</div>
</div>"""
        st.markdown(f"""
        <div class="mkt-mover-table-card">
            <div class="mkt-mover-header-g">
                <span>🟢</span> <span>Top Gainers</span>
            </div>
            <div style="background:var(--card-bg);">
                {gainer_rows if gainer_rows else '<div style="padding:20px; text-align:center; color:var(--secondary-text); font-size:0.85rem;">No gainers found today</div>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with l_col:
        loser_rows = ""
        for s in losers:
            sec_lbl = SECTOR_MAP.get(s['ticker'], "Market Segment")
            loser_rows += f"""<div class="mkt-mover-row">
<div>
<div class="mkt-mover-name">{s['name']}</div>
<div class="mkt-mover-sub">
<span class="mkt-mover-ticker">{s['ticker']}</span>
<span class="mkt-tag" style="font-size:0.58rem; padding:1px 4px;">{sec_lbl}</span>
</div>
</div>
<div style="text-align:right">
<div class="mkt-mover-price">₹{s['price']:,.2f}</div>
<div class="mkt-mover-pct-r">▼ {abs(s['chg_pct']):.2f}%</div>
</div>
</div>"""
        st.markdown(f"""
        <div class="mkt-mover-table-card">
            <div class="mkt-mover-header-l">
                <span>🔴</span> <span>Top Losers</span>
            </div>
            <div style="background:var(--card-bg);">
                {loser_rows if loser_rows else '<div style="padding:20px; text-align:center; color:var(--secondary-text); font-size:0.85rem;">No losers found today</div>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── SECTION 5: SECTOR PERFORMANCE ────────────────────────────────────────
    st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">🏭 SECTOR PERFORMANCE</div>', unsafe_allow_html=True)
    sector_list = [
        {"name": "IT",          "ticker": "^CNXIT"},
        {"name": "Banking",     "ticker": "^NSEBANK"},
        {"name": "Auto",        "ticker": "^CNXAUTO"},
        {"name": "Pharma",      "ticker": "^CNXPHARMA"},
        {"name": "Energy",      "ticker": "^CNXENERGY"},
        {"name": "FMCG",        "ticker": "^CNXFMCG"},
        {"name": "Real Estate", "ticker": "^CNXREALTY"},
        {"name": "Metal",       "ticker": "^CNXMETAL"},
    ]
    sec_cols = st.columns(4)
    for idx_num, sec in enumerate(sector_list):
        q = batch_quotes.get(sec["ticker"])
        with sec_cols[idx_num % 4]:
            if q:
                cur, _, chg, pct = q
                color_var = "var(--success-color)" if chg >= 0 else "var(--danger-color)"
                c_style = f"color: {color_var};"
                arrow = "▲" if chg >= 0 else "▼"
                
                # Clamped percentage for progress visual indicator
                pct_clamped = min(3.0, max(0.1, abs(pct)))
                bar_w = (pct_clamped / 3.0) * 100
                
                sec_hist, _ = get_trend_history(sec["ticker"], period="5d")
                sec_prices = sec_hist["Close"].tolist() if sec_hist is not None and not sec_hist.empty else []
                sec_spark = make_svg_sparkline(sec_prices, color=("#27ae60" if chg >= 0 else "#e74c3c"))
                
                st.markdown(f"""
                <div class="mkt-sector-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div style="font-size:0.9rem; font-weight:700; color:var(--text-color);">{sec['name']}</div>
                            <div style="font-size:0.65rem; color:var(--secondary-text); margin-top:2px;">{sec['ticker']}</div>
                        </div>
                        <div style="font-size:0.85rem; font-weight:700; color:var(--text-color);">{cur:,.1f}</div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px;">
                        <span style="font-size:0.85rem; font-weight:700; {c_style}">{arrow} {pct:+.2f}%</span>
                        <div class="mkt-sparkline">{sec_spark}</div>
                    </div>
                    <div class="mkt-sector-bar-bg">
                        <div class="mkt-sector-bar" style="background:{color_var}; width:{bar_w}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="mkt-sector-card" style="justify-content:center; align-items:center; min-height:100px;">
                    <div style="color:var(--secondary-text); font-size:0.8rem;">{sec['name']} loading...</div>
                </div>
                """, unsafe_allow_html=True)

    # ── SECTION 6: MARKET HEATMAP ────────────────────────────────────────────
    st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">🗺️ MARKET HEATMAP</div>', unsafe_allow_html=True)
    heatmap_cells = ""
    for sec in sector_list:
        q = batch_quotes.get(sec["ticker"])
        if q:
            cur, _, chg, pct = q
            if pct >= 0:
                opacity = min(0.35, max(0.08, (pct / 3.0) * 0.35))
                bg_color = f"rgba(39, 174, 96, {opacity:.2f})"
                border_color = "rgba(39, 174, 96, 0.25)"
                text_color = "var(--success-color)"
                arrow = "▲"
            else:
                opacity = min(0.35, max(0.08, (abs(pct) / 3.0) * 0.35))
                bg_color = f"rgba(231, 76, 60, {opacity:.2f})"
                border_color = "rgba(231, 76, 60, 0.25)"
                text_color = "var(--danger-color)"
                arrow = "▼"
            
            heatmap_cells += f"""<div class="mkt-heatmap-cell" style="background:{bg_color}; border:1px solid {border_color};">
<div style="font-size:0.95rem; font-weight:800; color:var(--text-color);">{sec['name']}</div>
<div style="font-size:0.68rem; color:var(--secondary-text); margin-top:2px;">{sec['ticker']}</div>
<div style="font-size:1.05rem; font-weight:800; color:{text_color}; margin-top:6px;">{arrow} {pct:+.2f}%</div>
</div>"""
        else:
            heatmap_cells += f"""<div class="mkt-heatmap-cell" style="background:var(--hover-bg); border:1px solid var(--border-color);">
<div style="font-size:0.9rem; font-weight:700; color:var(--secondary-text);">{sec['name']}</div>
<div style="font-size:0.68rem; color:var(--secondary-text); margin-top:2px;">{sec['ticker']}</div>
<div style="font-size:0.85rem; color:var(--secondary-text); margin-top:6px;">Loading...</div>
</div>"""
    st.markdown(f'<div class="mkt-heatmap-grid">{heatmap_cells}</div>', unsafe_allow_html=True)

    # ── SECTION 7 & 8: STATISTICS & INSIGHTS ─────────────────────────────────
    with st.spinner("Analyzing market stats..."):
        breadth = get_market_breadth()
        n50_52w = get_batch_52w_range(("^NSEI",)).get("^NSEI")

    strongest_sec_name, strongest_sec_pct = "N/A", -999.0
    weakest_sec_name, weakest_sec_pct = "N/A", 999.0
    for sec in sector_list:
        q = batch_quotes.get(sec["ticker"])
        if q:
            _, _, _, pct = q
            if pct > strongest_sec_pct:
                strongest_sec_pct = pct
                strongest_sec_name = sec["name"]
            if pct < weakest_sec_pct:
                weakest_sec_pct = pct
                weakest_sec_name = sec["name"]

    if nifty_quote:
        _, _, _, n_pct = nifty_quote
        if n_pct >= 0.45:
            mkt_stance = "🟢 Bullish Stance (Index Up)"
        elif n_pct <= -0.45:
            mkt_stance = "🔴 Bearish Stance (Index Down)"
        else:
            mkt_stance = "🟡 Neutral Stance (Rangebound)"
    else:
        mkt_stance = "Neutral Stance"

    vix_quote = batch_quotes.get("^INDIAVIX")
    if vix_quote:
        vix_val = vix_quote[0]
        if vix_val < 15.0:
            risk_val = f"🟢 Low Risk (VIX: {vix_val:.2f})"
        elif 15.0 <= vix_val <= 19.5:
            risk_val = f"🟡 Moderate Risk (VIX: {vix_val:.2f})"
        else:
            risk_val = f"🔴 High Risk (VIX: {vix_val:.2f})"
    else:
        risk_val = "Moderate Risk (VIX N/A)"

    stat_col, insight_col = st.columns(2)
    
    with stat_col:
        st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">📊 MARKET STATISTICS</div>', unsafe_allow_html=True)
        if breadth and breadth["total"] > 0:
            adv, dec, tot, unch = breadth["advances"], breadth["declines"], breadth["total"], breadth["unchanged"]
            adv_pct = (adv / tot) * 100
            dec_pct = (dec / tot) * 100
            ad_ratio = adv / dec if dec > 0 else float(adv)
            
            range_html = ""
            if n50_52w:
                pos_pct = n50_52w["pos_pct"]
                w_low = n50_52w["w52_low"]
                w_high = n50_52w["w52_high"]
                range_html = f"""
                <div style="margin-top:12px; border-top:1px solid var(--row-border); padding-top:10px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--secondary-text);">
                        <span>52W Low (₹{w_low:,.0f})</span>
                        <span style="font-weight:700; color:var(--text-color);">{pos_pct:.1f}% of Range</span>
                        <span>52W High (₹{w_high:,.0f})</span>
                    </div>
                    <div class="mkt-sector-bar-bg" style="height:6px; margin-top:4px;">
                        <div class="mkt-sector-bar" style="background:var(--primary-blue); width:{pos_pct}%;"></div>
                    </div>
                </div>
                """
            st.markdown(f"""
            <div class="mkt-insight-card">
                <div>
                    <div class="mkt-insight-item">
                        <span class="mkt-insight-label">Advances</span>
                        <span class="mkt-insight-value" style="color:var(--success-color);">{adv} ({adv_pct:.0f}%)</span>
                    </div>
                    <div class="mkt-insight-item">
                        <span class="mkt-insight-label">Declines</span>
                        <span class="mkt-insight-value" style="color:var(--danger-color);">{dec} ({dec_pct:.0f}%)</span>
                    </div>
                    <div class="mkt-insight-item">
                        <span class="mkt-insight-label">A/D Ratio</span>
                        <span class="mkt-insight-value">{ad_ratio:.2f} ({unch} unchanged)</span>
                    </div>
                    <div style="display:flex; height:5px; border-radius:3px; overflow:hidden; margin-top:10px;">
                        <div style="background:var(--success-color); width:{adv_pct}%;"></div>
                        <div style="background:var(--danger-color); width:{dec_pct}%;"></div>
                    </div>
                </div>
                {range_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="mkt-insight-card" style="color:var(--secondary-text); padding:40px 10px; text-align:center;">Statistics data currently unavailable.</div>', unsafe_allow_html=True)

    with insight_col:
        st.markdown('<div class="sec-title" style="margin-top:28px; margin-bottom:12px;">💡 MARKET INSIGHTS</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="mkt-insight-card">
            <div>
                <div class="mkt-insight-item">
                    <span class="mkt-insight-label">Today's Strongest Sector</span>
                    <span class="mkt-insight-value" style="color:var(--success-color);">{strongest_sec_name} ({strongest_sec_pct:+.2f}%)</span>
                </div>
                <div class="mkt-insight-item">
                    <span class="mkt-insight-label">Today's Weakest Sector</span>
                    <span class="mkt-insight-value" style="color:var(--danger-color);">{weakest_sec_name} ({weakest_sec_pct:+.2f}%)</span>
                </div>
                <div class="mkt-insight-item">
                    <span class="mkt-insight-label">Benchmark Market Trend</span>
                    <span class="mkt-insight-value">{mkt_stance}</span>
                </div>
                <div class="mkt-insight-item">
                    <span class="mkt-insight-label">Market Volatility risk</span>
                    <span class="mkt-insight-value">{risk_val}</span>
                </div>
            </div>
            <div style="font-size:0.7rem; color:var(--secondary-text); margin-top:10px; padding-top:6px; border-top:1px solid var(--row-border); font-style:italic;">
                ℹ️ Insights are automatically derived from Indian Indices quotes and VIX benchmarks.
            </div>
        </div>
        """, unsafe_allow_html=True)




# ══════════════════════════════════════════════════════════════════════════════
# TAB — MARKET BREADTH (Advance/Decline + Gap Movers — pro-trader signals)
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "breadth":
    col_h, col_r = st.columns([5, 1])
    with col_h:
        st.markdown('<div class="sec-title">📊 MARKET BREADTH</div>', unsafe_allow_html=True)
    with col_r:
        if st.button("🔄", key="breadth_refresh"):
            get_market_breadth.clear()
            get_index_quote.clear()
            st.rerun()

    st.caption("~40 large-cap Nifty stocks ka advance/decline — sirf index dekhna kaafi nahi, "
               "breadth bataata hai move kitna broad-based hai.")

    with st.spinner("Breadth calculate kar raha hoon…"):
        breadth = get_market_breadth()

    if breadth["total"] > 0:
        adv, dec, unch, tot = breadth["advances"], breadth["declines"], breadth["unchanged"], breadth["total"]
        adv_pct = (adv / tot * 100) if tot else 0
        dec_pct = (dec / tot * 100) if tot else 0
        ad_ratio = (adv / dec) if dec > 0 else float(adv) if adv > 0 else 0.0

        # Interpretation — index direction vs breadth direction compare karo
        _n50 = get_index_quote("^NSEI")
        n50_pct = _n50[3] if _n50 else 0
        if n50_pct > 0.15 and adv < dec:
            breadth_note = "⚠️ Index upar hai lekin breadth weak — sirf handful bade stocks khinch rahe hain, move broad-based nahi hai."
            note_color = "#f97316"
        elif n50_pct < -0.15 and adv > dec:
            breadth_note = "⚠️ Index neeche hai lekin breadth positive — chhote/mid stocks resilient hain, sirf bade index-heavy stocks gire."
            note_color = "#f97316"
        elif adv > dec * 1.5:
            breadth_note = "✅ Healthy breadth — broad-based buying, zyada stocks upar ja rahe hain."
            note_color = "#27ae60"
        elif dec > adv * 1.5:
            breadth_note = "🔴 Weak breadth — broad-based selling, zyada stocks neeche ja rahe hain."
            note_color = "#e74c3c"
        else:
            breadth_note = "➖ Mixed breadth — market mein clear direction nahi hai abhi."
            note_color = "#8b90a0"

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            st.markdown(f"""
            <div style="background:#0d2015;border:1px solid #27ae60;border-radius:10px;
                        padding:12px;text-align:center;">
              <div style="font-size:0.68rem;color:#8b90a0;">ADVANCES</div>
              <div style="font-size:1.4rem;font-weight:800;color:#27ae60;">{adv}</div>
              <div style="font-size:0.68rem;color:#8b90a0;">{adv_pct:.0f}% of {tot}</div>
            </div>""", unsafe_allow_html=True)
        with bc2:
            st.markdown(f"""
            <div style="background:#200d0d;border:1px solid #e74c3c;border-radius:10px;
                        padding:12px;text-align:center;">
              <div style="font-size:0.68rem;color:#8b90a0;">DECLINES</div>
              <div style="font-size:1.4rem;font-weight:800;color:#e74c3c;">{dec}</div>
              <div style="font-size:0.68rem;color:#8b90a0;">{dec_pct:.0f}% of {tot}</div>
            </div>""", unsafe_allow_html=True)
        with bc3:
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;
                        padding:12px;text-align:center;">
              <div style="font-size:0.68rem;color:#8b90a0;">A/D RATIO</div>
              <div style="font-size:1.4rem;font-weight:800;color:#e8eaf0;">{ad_ratio:.2f}</div>
              <div style="font-size:0.68rem;color:#8b90a0;">{unch} unchanged</div>
            </div>""", unsafe_allow_html=True)

        # Visual bar — advances vs declines proportion
        st.markdown(f"""
        <div style="display:flex;height:10px;border-radius:6px;overflow:hidden;margin-top:10px;">
          <div style="background:#27ae60;width:{adv_pct}%;"></div>
          <div style="background:#e74c3c;width:{dec_pct}%;"></div>
        </div>
        <div style="background:{note_color}15;border:1px solid {note_color}55;border-radius:8px;
                    padding:10px 14px;margin-top:10px;font-size:0.78rem;color:{note_color};">
          {breadth_note}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Breadth data abhi load nahi ho paya — refresh karke try karo.")

    # ══════════════════════════════════════════════════════════════════════════
    # 🎯 GAP MOVERS — biggest move from previous close (pre-open proxy)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">🎯 GAP MOVERS</div>', unsafe_allow_html=True)
    st.caption("Previous close se sabse zyada move karne wale stocks — asli live "
               "pre-open (9:00-9:08 AM) indicative price yahan available nahi hai, "
               "isliye ye 'abhi tak ka biggest move' hai, exact pre-open gap ke liye "
               "broker app dekho.")

    gap_movers = breadth.get("gap_movers", [])
    if gap_movers:
        gm_cols = st.columns(4)
        for i, gm in enumerate(gap_movers):
            gc = "#27ae60" if gm["chg_pct"] >= 0 else "#e74c3c"
            ga = "▲" if gm["chg_pct"] >= 0 else "▼"
            with gm_cols[i % 4]:
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid {gc}44;border-radius:10px;
                            padding:10px;text-align:center;margin-bottom:8px;border-top:3px solid {gc};">
                  <div style="font-size:0.78rem;font-weight:700;color:#e8eaf0;">{gm['name']}</div>
                  <div style="font-size:0.92rem;font-weight:800;color:{gc};margin-top:4px;">
                    {ga} {abs(gm['chg_pct']):.2f}%
                  </div>
                  <div style="font-size:0.68rem;color:#8b90a0;">₹{gm['price']:,.2f}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Gap data abhi load nahi ho paya — refresh karke try karo.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — STOCK SCREENER
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "screener":

    G = "#27ae60"; R = "#e74c3c"; B = "#3b82f6"
    CARD = "#1a1d27"; BDR = "#2a2d3a"; TXT = "#e8eaf0"; MUT = "#8b90a0"

    # Header
    sc_h, sc_r = st.columns([5, 1])
    with sc_h:
        st.markdown('<div class="sec-title">STOCK SCREENER</div>', unsafe_allow_html=True)
    with sc_r:
        if st.button("🔄", key="screener_refresh", help="Data refresh karo"):
            get_screener_data.clear()
            st.rerun()

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Stocks ka data fetch ho raha hai..."):
        _holding_tickers = tuple(sorted(st.session_state.get("pt_holdings", {}).keys()))
        raw_data = get_screener_data(holding_tickers=_holding_tickers)

    if not raw_data:
        st.error("Data fetch nahi hua. Refresh karo ya thodi der baad try karo.")
        st.stop()

    # ── FILTER PANEL ──────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:0.75rem;color:#8b90a0;font-weight:600;letter-spacing:.06em;margin-bottom:8px;">🔍 FILTERS & TOOLS</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        # 3 columns grid for filters
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            search_query = st.text_input("🔍 Search Ticker / Name", "", key="scr_search", help="Ticker symbol ya Company Name se search karein")
        
        with f_col2:
            all_sectors = sorted(set(s["sector"] for s in raw_data if s["sector"] != "—"))
            sector_sel = st.multiselect("Sector", ["All"] + all_sectors, default=["All"], key="scr_sector")
            
        with f_col3:
            mkt_cap_filter = st.selectbox(
                "Market Cap Category", 
                ["Any", "Large Cap (> ₹20,000 Cr)", "Mid Cap (₹5,000 Cr - ₹20,000 Cr)", "Small Cap (< ₹5,000 Cr)"], 
                key="scr_mkt_cap"
            )

        f_col4, f_col5, f_col6 = st.columns(3)
        
        with f_col4:
            change_range = st.slider(
                "Today's Change %",
                min_value=-15.0, max_value=15.0,
                value=(-15.0, 15.0), step=0.5, key="scr_chg"
            )
            
        with f_col5:
            pe_range = st.slider(
                "P/E Ratio Range", 
                min_value=0.0, max_value=200.0,
                value=(0.0, 100.0), step=1.0, key="scr_pe",
                help="Max value 200.0 par limits disabled"
            )
            
        with f_col6:
            pb_range = st.slider(
                "P/B Ratio Range", 
                min_value=0.0, max_value=50.0,
                value=(0.0, 25.0), step=0.5, key="scr_pb",
                help="Max value 50.0 par limits disabled"
            )

        f_col7, f_col8, f_col9 = st.columns(3)
        
        with f_col7:
            rsi_filter = st.selectbox(
                "RSI (14) Filter",
                ["Any", "Overbought (>70)", "Oversold (<30)", "Bullish Momentum (50-70)", "Bearish Momentum (30-50)"],
                key="scr_rsi"
            )
            
        with f_col8:
            sma_filter = st.selectbox(
                "Moving Averages (SMA)",
                ["Any", "Price > SMA 20", "Price < SMA 20", "Price > SMA 50", "Price < SMA 50", "Golden Cross (SMA20 > SMA50)", "Death Cross (SMA20 < SMA50)"],
                key="scr_sma"
            )
            
        with f_col9:
            macd_filter = st.selectbox(
                "MACD Signals",
                ["Any", "Bullish Crossover (MACD > Signal)", "Bearish Crossover (MACD < Signal)"],
                key="scr_macd"
            )

        f_col10, f_col11, f_col12 = st.columns(3)
        
        with f_col10:
            vol_filter = st.selectbox(
                "Volume Ratio vs Average",
                ["Any", "High (>2x avg)", "Very High (>3x avg)", "Low (<0.5x avg)"],
                key="scr_vol"
            )
            
        with f_col11:
            w52_filter = st.selectbox(
                "52-Week Range Position",
                ["Any", "Near 52W High (within 5%)", "Near 52W Low (within 5%)", "More than 20% below 52W High"],
                key="scr_52w"
            )
            
        with f_col12:
            sort_by = st.selectbox(
                "Sort By Column",
                [
                    "Change % (High→Low)", "Change % (Low→High)",
                    "P/E (Low→High)", "P/E (High→Low)",
                    "P/B (Low→High)", "P/B (High→Low)",
                    "Volume Ratio (High→Low)",
                    "Price (High→Low)", "Price (Low→High)",
                    "RSI (Low→High)", "RSI (High→Low)",
                    "% from 52W Low (High→Low)"
                ],
                key="scr_sort"
            )

    # ── APPLY FILTERS ─────────────────────────────────────────────────────────
    filtered = raw_data[:]

    # 1. Search Query Filter
    if search_query:
        sq = search_query.strip().lower()
        filtered = [s for s in filtered if sq in s["ticker"].lower() or sq in s["name"].lower()]

    # 2. Sector Filter
    if sector_sel and "All" not in sector_sel:
        filtered = [s for s in filtered if s["sector"] in sector_sel]

    # 3. Market Cap Filter
    if mkt_cap_filter == "Large Cap (> ₹20,000 Cr)":
        filtered = [s for s in filtered if s.get("mktcap", 0) >= 200000000000]
    elif mkt_cap_filter == "Mid Cap (₹5,000 Cr - ₹20,000 Cr)":
        filtered = [s for s in filtered if 50000000000 <= s.get("mktcap", 0) < 200000000000]
    elif mkt_cap_filter == "Small Cap (< ₹5,000 Cr)":
        filtered = [s for s in filtered if s.get("mktcap", 0) < 50000000000]

    # 4. Change % Range Filter
    filtered = [s for s in filtered if change_range[0] <= s["chg_pct"] <= change_range[1]]

    # 5. P/E Ratio Filter
    if pe_range[1] == 200.0:
        filtered = [s for s in filtered if s["pe"] is None or (s["pe"] >= pe_range[0])]
    else:
        filtered = [s for s in filtered if s["pe"] is None or (pe_range[0] <= s["pe"] <= pe_range[1])]

    # 6. P/B Ratio Filter
    if pb_range[1] == 50.0:
        filtered = [s for s in filtered if s["pb"] is None or (s["pb"] >= pb_range[0])]
    else:
        filtered = [s for s in filtered if s["pb"] is None or (pb_range[0] <= s["pb"] <= pb_range[1])]

    # 7. RSI (14) Filter
    if rsi_filter == "Overbought (>70)":
        filtered = [s for s in filtered if s.get("rsi") is not None and s["rsi"] >= 70]
    elif rsi_filter == "Oversold (<30)":
        filtered = [s for s in filtered if s.get("rsi") is not None and s["rsi"] <= 30]
    elif rsi_filter == "Bullish Momentum (50-70)":
        filtered = [s for s in filtered if s.get("rsi") is not None and 50 <= s["rsi"] <= 70]
    elif rsi_filter == "Bearish Momentum (30-50)":
        filtered = [s for s in filtered if s.get("rsi") is not None and 30 <= s["rsi"] <= 50]

    # 8. Moving Averages SMA Filter
    if sma_filter == "Price > SMA 20":
        filtered = [s for s in filtered if s.get("sma20") is not None and s["price"] > s["sma20"]]
    elif sma_filter == "Price < SMA 20":
        filtered = [s for s in filtered if s.get("sma20") is not None and s["price"] < s["sma20"]]
    elif sma_filter == "Price > SMA 50":
        filtered = [s for s in filtered if s.get("sma50") is not None and s["price"] > s["sma50"]]
    elif sma_filter == "Price < SMA 50":
        filtered = [s for s in filtered if s.get("sma50") is not None and s["price"] < s["sma50"]]
    elif sma_filter == "Golden Cross (SMA20 > SMA50)":
        filtered = [s for s in filtered if s.get("sma20") is not None and s.get("sma50") is not None and s["sma20"] > s["sma50"]]
    elif sma_filter == "Death Cross (SMA20 < SMA50)":
        filtered = [s for s in filtered if s.get("sma20") is not None and s.get("sma50") is not None and s["sma20"] < s["sma50"]]

    # 9. MACD Filter
    if macd_filter == "Bullish Crossover (MACD > Signal)":
        filtered = [s for s in filtered if s.get("macd") is not None and s.get("macd_signal") is not None and s["macd"] > s["macd_signal"]]
    elif macd_filter == "Bearish Crossover (MACD < Signal)":
        filtered = [s for s in filtered if s.get("macd") is not None and s.get("macd_signal") is not None and s["macd"] < s["macd_signal"]]

    # 10. Volume Filter
    if vol_filter == "High (>2x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] >= 2]
    elif vol_filter == "Very High (>3x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] >= 3]
    elif vol_filter == "Low (<0.5x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] <= 0.5]

    # 11. 52-Week Position Filter
    if w52_filter == "Near 52W High (within 5%)":
        filtered = [s for s in filtered if s["from_52h"] >= -5]
    elif w52_filter == "Near 52W Low (within 5%)":
        filtered = [s for s in filtered if s["from_52l"] <= 5]
    elif w52_filter == "More than 20% below 52W High":
        filtered = [s for s in filtered if s["from_52h"] <= -20]

    # 12. Sort Results
    sort_map = {
        "Change % (High→Low)":        ("chg_pct",    True),
        "Change % (Low→High)":        ("chg_pct",    False),
        "P/E (Low→High)":             ("pe",         False),
        "P/E (High→Low)":             ("pe",         True),
        "P/B (Low→High)":             ("pb",         False),
        "P/B (High→Low)":             ("pb",         True),
        "Volume Ratio (High→Low)":    ("vol_ratio",  True),
        "Price (High→Low)":           ("price",      True),
        "Price (Low→High)":           ("price",      False),
        "RSI (Low→High)":             ("rsi",        False),
        "RSI (High→Low)":             ("rsi",        True),
        "% from 52W Low (High→Low)":  ("from_52l",   True),
    }
    sk, rev = sort_map.get(sort_by, ("chg_pct", True))
    filtered.sort(key=lambda x: (x.get(sk) is None, x.get(sk) if x.get(sk) is not None else 0), reverse=rev)

    # ── RESULTS SUMMARY ───────────────────────────────────────────────────────
    gainers_count = sum(1 for s in filtered if s["chg_pct"] > 0)
    losers_count  = sum(1 for s in filtered if s["chg_pct"] < 0)

    sm1, sm2, sm3, sm4 = st.columns(4)
    with sm1:
        st.markdown(f"""<div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
            padding:12px;text-align:center;">
          <div style="font-size:0.65rem;color:{MUT};">RESULTS</div>
          <div style="font-size:1.4rem;font-weight:800;color:{TXT};">{len(filtered)}</div>
          <div style="font-size:0.7rem;color:{MUT};">of {len(raw_data)} stocks</div>
        </div>""", unsafe_allow_html=True)
    with sm2:
        st.markdown(f"""<div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
            padding:12px;text-align:center;">
          <div style="font-size:0.65rem;color:{MUT};">GAINERS</div>
          <div style="font-size:1.4rem;font-weight:800;color:{G};">{gainers_count}</div>
          <div style="font-size:0.7rem;color:{MUT};">aaj positive</div>
        </div>""", unsafe_allow_html=True)
    with sm3:
        st.markdown(f"""<div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
            padding:12px;text-align:center;">
          <div style="font-size:0.65rem;color:{MUT};">LOSERS</div>
          <div style="font-size:1.4rem;font-weight:800;color:{R};">{losers_count}</div>
          <div style="font-size:0.7rem;color:{MUT};">aaj negative</div>
        </div>""", unsafe_allow_html=True)
    with sm4:
        avg_pe_vals = [s["pe"] for s in filtered if s["pe"] is not None]
        avg_pe = sum(avg_pe_vals) / len(avg_pe_vals) if avg_pe_vals else 0
        st.markdown(f"""<div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
            padding:12px;text-align:center;">
          <div style="font-size:0.65rem;color:{MUT};">AVG P/E</div>
          <div style="font-size:1.4rem;font-weight:800;color:{B};">{avg_pe:.1f}</div>
          <div style="font-size:0.7rem;color:{MUT};">filtered stocks</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── EXPORT & PAGINATION TOOLBAR ───────────────────────────────────────────
    export_col, page_col1, page_col2 = st.columns([2, 3, 2])
    
    with export_col:
        if filtered:
            import io
            export_data = []
            for s in filtered:
                export_data.append({
                    "Ticker": s["ticker"].replace(".NS", ""),
                    "Company Name": s["name"],
                    "Price (INR)": s["price"],
                    "Change %": s["chg_pct"],
                    "P/E": s["pe"] if s["pe"] is not None else "",
                    "P/B": s["pb"] if s["pb"] is not None else "",
                    "RSI (14)": s.get("rsi") if s.get("rsi") is not None else "",
                    "52W High (INR)": s["w52h"],
                    "52W Low (INR)": s["w52l"],
                    "Volume": s["volume"],
                    "Avg Volume": s["avg_volume"],
                    "Volume Ratio": s["vol_ratio"],
                    "Sector": s["sector"]
                })
            df_export = pd.DataFrame(export_data)
            csv_buffer = io.BytesIO()
            df_export.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Export Filtered CSV",
                data=csv_buffer.getvalue(),
                file_name="filtered_stocks.csv",
                mime="text/csv",
                key="scr_download_csv",
                use_container_width=True
            )
        else:
            st.button("📥 Export Filtered CSV", disabled=True, use_container_width=True)

    with page_col2:
        items_per_page = st.selectbox(
            "Items per page", 
            [10, 20, 50, "All"], 
            index=1, 
            key="scr_per_page",
            label_visibility="collapsed"
        )
        
    total_items = len(filtered)
    if items_per_page == "All":
        page_items = filtered
        total_pages = 1
        current_page = 1
        with page_col1:
            st.markdown(f'<div style="text-align:center;font-size:0.85rem;color:{MUT};padding-top:10px;">Showing all {total_items} stocks</div>', unsafe_allow_html=True)
    else:
        limit = int(items_per_page)
        total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1
        with page_col1:
            current_page = st.number_input(
                f"Page (1 to {total_pages})", 
                min_value=1, 
                max_value=total_pages, 
                value=1, 
                step=1, 
                key="scr_page_num",
                label_visibility="collapsed"
            )
        start_idx = (current_page - 1) * limit
        end_idx = start_idx + limit
        page_items = filtered[start_idx:end_idx]

    # ── RESULTS TABLE ─────────────────────────────────────────────────────────
    if not filtered:
        st.markdown(f"""<div style="text-align:center;padding:40px;background:{CARD};
            border:1px solid {BDR};border-radius:12px;color:{MUT};">
          <div style="font-size:2rem;">🔍</div>
          <div style="font-size:1rem;color:{TXT};margin-top:10px;font-weight:600;">
            Koi stock match nahi hua
          </div>
          <div style="font-size:0.82rem;margin-top:6px;">
            Filters thoda loosen karo
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        table_html = f"""
        <div style="background:{CARD};border:1px solid {BDR};border-radius:12px;overflow:hidden;">
          <div style="display:flex;padding:10px 16px;background:#13161f;
                      border-bottom:1px solid {BDR};font-size:0.67rem;
                      color:{MUT};font-weight:600;letter-spacing:.06em;align-items:center;">
            <div style="flex:2.5;">STOCK</div>
            <div style="flex:1.2;text-align:right;">PRICE</div>
            <div style="flex:1.0;text-align:right;">CHG%</div>
            <div style="flex:0.8;text-align:right;">P/E</div>
            <div style="flex:0.8;text-align:right;">P/B</div>
            <div style="flex:0.9;text-align:right;">RSI(14)</div>
            <div style="flex:1.8;text-align:right;">52W HIGH</div>
            <div style="flex:1.8;text-align:right;">52W LOW</div>
            <div style="flex:1.2;text-align:right;">VOL RATIO</div>
            <div style="flex:1.5;text-align:right;">SECTOR</div>
          </div>
        """

        for s in page_items:
            chg_c = G if s["chg_pct"] >= 0 else R
            chg_arrow = "▲" if s["chg_pct"] >= 0 else "▼"


            vr = s["vol_ratio"]
            if vr >= 3:   vol_badge = f'<span style="background:#2d0d2d;color:#e879f9;border-radius:4px;padding:1px 6px;font-size:0.62rem;">🔥 {vr:.1f}x</span>'
            elif vr >= 2: vol_badge = f'<span style="background:#0d2340;color:{B};border-radius:4px;padding:1px 6px;font-size:0.62rem;">↑ {vr:.1f}x</span>'
            elif vr < 0.5:vol_badge = f'<span style="background:#2d2000;color:#f59e0b;border-radius:4px;padding:1px 6px;font-size:0.62rem;">↓ {vr:.1f}x</span>'
            else:          vol_badge = f'<span style="color:{MUT};font-size:0.75rem;">{vr:.1f}x</span>'

            pe_disp  = f"{s['pe']:.1f}" if s['pe'] is not None else "—"
            pb_disp  = f"{s['pb']:.2f}" if s['pb'] is not None else "—"
            rsi_val_disp = f"{s['rsi']:.1f}" if s.get('rsi') is not None else "—"
            
            if s.get('rsi') is not None:
                if s['rsi'] >= 70:
                    rsi_disp = f'<span style="color:{R};font-weight:600;">{rsi_val_disp}</span>'
                elif s['rsi'] <= 30:
                    rsi_disp = f'<span style="color:{G};font-weight:600;">{rsi_val_disp}</span>'
                else:
                    rsi_disp = f'<span style="color:{TXT};">{rsi_val_disp}</span>'
            else:
                rsi_disp = f'<span style="color:{MUT};">—</span>'

            h_pct    = f'<span style="color:{R};font-size:0.7rem;">({s["from_52h"]:.1f}%)</span>'
            l_pct    = f'<span style="color:{G};font-size:0.7rem;">(+{s["from_52l"]:.1f}%)</span>'

            sector_short = (s["sector"][:12] + "…") if len(s["sector"]) > 13 else s["sector"]

            table_html += f"""
          <div style="display:flex;padding:11px 16px;border-bottom:1px solid {BDR};
                      font-size:0.8rem;align-items:center;">
            <div style="flex:2.5;">
              <div style="font-weight:700;color:{TXT};">{s['name']}</div>
              <div style="font-size:0.68rem;color:{MUT};">{s['ticker'].replace('.NS','')}</div>
            </div>
            <div style="flex:1.2;text-align:right;font-weight:700;color:{TXT};">
              ₹{s['price']:,.2f}
            </div>
            <div style="flex:1.0;text-align:right;font-weight:700;color:{chg_c};">
              {chg_arrow} {abs(s['chg_pct']):.2f}%
            </div>
            <div style="flex:0.8;text-align:right;color:{TXT};">{pe_disp}</div>
            <div style="flex:0.8;text-align:right;color:{TXT};">{pb_disp}</div>
            <div style="flex:0.9;text-align:right;color:{TXT};">{rsi_disp}</div>
            <div style="flex:1.8;text-align:right;">
              <span style="color:{TXT};">₹{s['w52h']:,.0f}</span> {h_pct}
            </div>
            <div style="flex:1.8;text-align:right;">
              <span style="color:{TXT};">₹{s['w52l']:,.0f}</span> {l_pct}
            </div>
            <div style="flex:1.2;text-align:right;">{vol_badge}</div>
            <div style="flex:1.5;text-align:right;font-size:0.72rem;color:{MUT};">
              {sector_short}
            </div>
          </div>"""

        table_html += "</div>"
        st.markdown(table_html, unsafe_allow_html=True)

        # ── ADD TO WATCHLIST QUICK ACTION ─────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.75rem;color:{MUT};">💡 Kisi stock ko Watchlist mein add karna hai?</div>', unsafe_allow_html=True)
        wl_col1, wl_col2 = st.columns([3, 1])
        current_wl_tickers = [t for t, _ in st.session_state.custom_watchlist]
        available = [(s["ticker"], s["name"]) for s in filtered if s["ticker"] not in current_wl_tickers]
        if available:
            with wl_col1:
                add_choice = st.selectbox("Stock chuno", [f"{n} ({t.replace('.NS','')})" for t, n in available],
                                           key="scr_add_wl", label_visibility="collapsed")
            with wl_col2:
                if st.button("➕ Watchlist", key="scr_add_btn", use_container_width=True):
                    chosen_ticker = available[[f"{n} ({t.replace('.NS','')})" for t, n in available].index(add_choice)][0]
                    chosen_name   = available[[f"{n} ({t.replace('.NS','')})" for t, n in available].index(add_choice)][1]
                    st.session_state.custom_watchlist.append((chosen_ticker, chosen_name))
                    st.success(f"✅ {chosen_name} watchlist mein add ho gaya!")
                    st.rerun()
        else:
            st.markdown(f'<div style="font-size:0.78rem;color:{G};">✅ Filtered stocks already watchlist mein hain</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — ECONOMIC CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "calendar":
    from datetime import date, timedelta
    import calendar as cal_module

    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, BLUE, GREEN, RED
    AMBER  = YELLOW
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    st.markdown('<div class="sec-title">📅 ECONOMIC CALENDAR</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.78rem;color:{MUTED};margin-bottom:14px;">'
                f'RBI meetings · Earnings results · F&O expiry · Budget · IPOs</div>',
                unsafe_allow_html=True)

    EVENTS = get_calendar_events()

    today = date.today()

    # ── Filters ───────────────────────────────────────────────────────────────
    TYPE_COLORS = {
        "RBI":     BLUE,
        "FNO":     AMBER,
        "RESULTS": GREEN,
        "BUDGET":  PURPLE,
        "HOLIDAY": "#f43f5e",
        "MACRO":   "#06b6d4",
    }
    TYPE_LABELS = {
        "RBI": "🏦 RBI Meeting",
        "FNO": "⚡ F&O Expiry",
        "RESULTS": "📊 Earnings",
        "BUDGET": "💼 Budget",
        "HOLIDAY": "🇮🇳 Holiday",
        "MACRO": "📈 Macro Data",
    }

    # Filter row
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        view_mode = st.selectbox("View", ["Upcoming Events", "This Month", "All Events"],
                                 key="cal_view", label_visibility="collapsed")
    with f2:
        type_opts = ["All Types"] + list(TYPE_LABELS.values())
        type_filter = st.selectbox("Type", type_opts, key="cal_type",
                                   label_visibility="collapsed")
    with f3:
        st.markdown(f'<div style="font-size:0.72rem;color:{MUTED};padding-top:8px;">'
                    f'Today: <b style="color:{TEXT};">{today.strftime("%d %b %Y")}</b></div>',
                    unsafe_allow_html=True)

    # Apply filters
    filtered_events = sorted(EVENTS, key=lambda e: e["date"])

    if view_mode == "Upcoming Events":
        filtered_events = [e for e in filtered_events if e["date"] >= today][:30]
    elif view_mode == "This Month":
        filtered_events = [e for e in filtered_events
                           if e["date"].year == today.year and e["date"].month == today.month]

    if type_filter != "All Types":
        # match by label
        type_key = next((k for k, v in TYPE_LABELS.items() if v == type_filter), None)
        if type_key:
            filtered_events = [e for e in filtered_events if e["type"] == type_key]

    # ── Legend strip ──────────────────────────────────────────────────────────
    legend_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">'
    for k, label in TYPE_LABELS.items():
        c = TYPE_COLORS[k]
        legend_html += (f'<span style="background:{c}22;color:{c};border:1px solid {c}44;'
                        f'border-radius:20px;padding:3px 10px;font-size:0.68rem;font-weight:700;">'
                        f'{label}</span>')
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)

    # ── Upcoming highlight — next 3 events ────────────────────────────────────
    upcoming3 = [e for e in sorted(EVENTS, key=lambda x: x["date"]) if e["date"] >= today][:3]
    if upcoming3:
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};'
                    f'letter-spacing:0.1em;margin-bottom:8px;">⏰ AGLE EVENTS</div>',
                    unsafe_allow_html=True)
        up_cols = st.columns(len(upcoming3))
        for col, ev in zip(up_cols, upcoming3):
            days_left = (ev["date"] - today).days
            dl_str = "Aaj!" if days_left == 0 else (f"Kal" if days_left == 1 else f"{days_left} din baad")
            with col:
                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {ev['color']}66;
                            border-radius:12px;padding:14px;text-align:center;
                            border-top:3px solid {ev['color']};">
                  <div style="font-size:1.6rem;">{ev['icon']}</div>
                  <div style="font-size:0.78rem;font-weight:700;color:{ev['color']};
                              margin:6px 0 2px;">{dl_str}</div>
                  <div style="font-size:0.72rem;color:{TEXT};font-weight:600;
                              line-height:1.3;">{ev['title']}</div>
                  <div style="font-size:0.65rem;color:{MUTED};margin-top:4px;">
                    {ev['date'].strftime('%d %b %Y')}
                  </div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Event list ────────────────────────────────────────────────────────────
    st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};'
                f'letter-spacing:0.1em;margin-bottom:8px;">'
                f'📋 {len(filtered_events)} EVENTS</div>', unsafe_allow_html=True)

    if not filtered_events:
        st.markdown(f"""
        <div style="text-align:center;padding:40px;color:{MUTED};">
          <div style="font-size:2rem;">📭</div>
          <div style="margin-top:8px;">Is filter mein koi event nahi</div>
        </div>""", unsafe_allow_html=True)
    else:
        current_month = None
        for ev in filtered_events:
            # Month divider
            ev_month = ev["date"].strftime("%B %Y")
            if ev_month != current_month:
                current_month = ev_month
                st.markdown(f"""
                <div style="background:#13161f;border-left:3px solid {BLUE};
                            padding:6px 14px;margin:12px 0 6px;border-radius:0 6px 6px 0;">
                  <span style="font-size:0.8rem;font-weight:800;color:{BLUE};">
                    📅 {ev_month}
                  </span>
                </div>""", unsafe_allow_html=True)

            days_diff = (ev["date"] - today).days
            if days_diff == 0:
                date_badge_bg = ev["color"] + "33"
                date_label = f"🔴 Aaj"
                date_color = ev["color"]
            elif days_diff == 1:
                date_badge_bg = ev["color"] + "22"
                date_label = "⏰ Kal"
                date_color = ev["color"]
            elif days_diff < 0:
                date_badge_bg = "#2a2d3a"
                date_label = f"{abs(days_diff)}d ago"
                date_color = MUTED
            elif days_diff <= 7:
                date_badge_bg = ev["color"] + "18"
                date_label = f"{days_diff}d baad"
                date_color = ev["color"]
            else:
                date_badge_bg = CARD_BG
                date_label = f"{days_diff}d"
                date_color = MUTED

            type_c = TYPE_COLORS.get(ev["type"], MUTED)

            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};
                        border-radius:12px;padding:13px 16px;margin-bottom:7px;
                        border-left:4px solid {ev['color']};">
              <div style="display:flex;align-items:center;gap:12px;">
                <!-- Icon -->
                <div style="font-size:1.6rem;min-width:36px;text-align:center;">{ev['icon']}</div>
                <!-- Content -->
                <div style="flex:1;">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;flex-wrap:wrap;">
                    <span style="font-size:0.88rem;font-weight:700;color:{TEXT};">{ev['title']}</span>
                    <span style="background:{type_c}22;color:{type_c};border-radius:4px;
                                 padding:1px 7px;font-size:0.62rem;font-weight:700;">
                      {ev['type']}
                    </span>
                  </div>
                  <div style="font-size:0.75rem;color:{MUTED};">{ev['desc']}</div>
                </div>
                <!-- Date -->
                <div style="text-align:right;min-width:80px;">
                  <div style="background:{date_badge_bg};color:{date_color};
                              border-radius:8px;padding:4px 10px;font-size:0.72rem;
                              font-weight:700;text-align:center;">
                    {ev['date'].strftime('%d %b')}
                  </div>
                  <div style="font-size:0.62rem;color:{date_color};
                              text-align:center;margin-top:3px;">{date_label}</div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 🆕 IPO TRACKER — Mainboard + SME IPOs (naya section, calendar ke neeche)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-title">🆕 IPO TRACKER</div>', unsafe_allow_html=True)
    st.caption("Mainboard + SME IPOs — open/close/listing dates aur price band. "
               "Live GMP/subscription % ke liye apna broker app check karo, "
               "wo minute-by-minute badalta hai.")

    ipos = sorted(get_ipo_data(), key=lambda x: x["open_date"])

    ipo_f1, ipo_f2 = st.columns([2, 2])
    with ipo_f1:
        ipo_type_filter = st.selectbox("Type", ["All", "Mainboard", "SME"],
                                       key="ipo_type_filter", label_visibility="collapsed")
    with ipo_f2:
        st.markdown(f'<div style="font-size:0.72rem;color:{MUTED};padding-top:8px;">'
                    f'{len(ipos)} IPOs tracked</div>', unsafe_allow_html=True)

    if ipo_type_filter != "All":
        ipos = [i for i in ipos if i["exchange"] == ipo_type_filter]

    for ipo in ipos:
        # ── Status compute karo aaj ki date ke hisaab se (live feel, static data) ──
        if today < ipo["open_date"]:
            days_to_open = (ipo["open_date"] - today).days
            ipo_status, status_color = f"Khulega {days_to_open}d mein", AMBER
        elif ipo["open_date"] <= today <= ipo["close_date"]:
            ipo_status, status_color = "🟢 OPEN NOW — Apply karo", GREEN
        elif ipo["close_date"] < today < ipo["listing_date"]:
            ipo_status, status_color = "⏳ Allotment/Listing ka wait", AMBER
        elif today == ipo["listing_date"]:
            ipo_status, status_color = "📈 Aaj LIST ho raha hai", PURPLE
        else:
            ipo_status, status_color = "✅ Listed", MUTED

        exch_color = BLUE if ipo["exchange"] == "Mainboard" else PURPLE

        st.markdown(f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;
                    padding:14px 18px;margin-bottom:10px;border-left:3px solid {status_color};">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      flex-wrap:wrap;gap:10px;">
            <div>
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-size:0.92rem;font-weight:800;color:{TEXT};">{ipo['name']}</span>
                <span style="background:{exch_color}22;color:{exch_color};border-radius:4px;
                             padding:1px 8px;font-size:0.62rem;font-weight:700;">{ipo['exchange']}</span>
                <span style="font-size:0.68rem;color:{MUTED};">{ipo['sector']}</span>
              </div>
              <div style="font-size:0.78rem;color:{MUTED};margin-top:6px;">
                Price band: <b style="color:{TEXT};">₹{ipo['price_low']}–₹{ipo['price_high']}</b>
                &nbsp;·&nbsp; Lot: <b style="color:{TEXT};">{ipo['lot_size']} shares</b>
                &nbsp;·&nbsp; Issue size: <b style="color:{TEXT};">₹{ipo['issue_size_cr']} Cr</b>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};margin-top:4px;">
                Open {ipo['open_date'].strftime('%d %b')} → Close {ipo['close_date'].strftime('%d %b')}
                &nbsp;·&nbsp; Listing {ipo['listing_date'].strftime('%d %b %Y')}
              </div>
            </div>
            <div style="text-align:right;min-width:140px;">
              <div style="background:{status_color}1a;color:{status_color};border:1px solid {status_color}55;
                          border-radius:20px;padding:4px 12px;font-size:0.7rem;font-weight:700;
                          white-space:nowrap;">
                {ipo_status}
              </div>
              <div style="font-size:0.85rem;font-weight:700;color:{TEXT};margin-top:6px;">
                Min. investment: ₹{ipo['price_high'] * ipo['lot_size']:,}
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

elif tab == "settings":

    # ══ SETTINGS PAGE — PREMIUM REDESIGN ══════════════════════════════════════
    # All backend logic (save_preferences, password change, portfolio reset,
    # session_state keys) is 100% preserved. Only the UI layer is redesigned.
    # ══════════════════════════════════════════════════════════════════════════

    # ── CSS for settings page ──────────────────────────────────────────────────
    st.markdown(f"""
    <style>
    /* ── Settings Page Premium Styles ── */
    .settings-hero {{
        background: linear-gradient(135deg, #EEF2FF 0%, #F0F9FF 50%, #F0FDF4 100%);
        border: 1px solid rgba(37,99,235,0.12);
        border-radius: 24px;
        padding: 32px 36px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        position: relative;
        overflow: hidden;
    }}
    .settings-hero::before {{
        content: '';
        position: absolute;
        top: -60px; right: -60px;
        width: 200px; height: 200px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(37,99,235,0.08) 0%, transparent 70%);
        pointer-events: none;
    }}
    .settings-hero-left {{ display: flex; align-items: center; gap: 24px; }}
    .settings-avatar {{
        width: 80px; height: 80px; border-radius: 50%;
        background: linear-gradient(135deg, #2563EB, #60A5FA);
        color: white; display: flex; align-items: center;
        justify-content: center; font-weight: 900; font-size: 1.9rem;
        box-shadow: 0 12px 32px rgba(37,99,235,0.3);
        flex-shrink: 0; position: relative;
    }}
    .settings-avatar-dot {{
        position: absolute; bottom: 3px; right: 3px;
        width: 16px; height: 16px; border-radius: 50%;
        background: #16A34A; border: 3px solid white;
        box-shadow: 0 0 8px rgba(22,163,74,0.5);
    }}
    .settings-hero-name {{
        font-size: 1.55rem; font-weight: 900;
        color: #111827; letter-spacing: -0.02em; margin-bottom: 2px;
    }}
    .settings-hero-meta {{
        font-size: 0.84rem; color: #6B7280; margin-bottom: 8px;
    }}
    .settings-hero-badges {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .settings-badge {{
        font-size: 0.7rem; font-weight: 700;
        padding: 3px 10px; border-radius: 20px;
        letter-spacing: 0.04em;
    }}
    .badge-pro {{
        background: linear-gradient(135deg,#FEF3C7,#FDE68A);
        color: #92400E; border: 1px solid #F59E0B44;
    }}
    .badge-active {{
        background: rgba(22,163,74,0.1);
        color: #15803D; border: 1px solid rgba(22,163,74,0.2);
    }}
    .badge-verified {{
        background: rgba(37,99,235,0.08);
        color: #1D4ED8; border: 1px solid rgba(37,99,235,0.2);
    }}

    /* Settings layout and sidebar navigation styles */
    div[data-testid="column"]:has(.settings-nav-marker) {{
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
        position: sticky !important;
        top: 20px !important;
    }}

    /* Column child elements margin override */
    div[data-testid="column"]:has(.settings-nav-marker) div[data-testid="stElementContainer"] {{
        margin-bottom: 0 !important;
        padding: 0 !important;
    }}

    /* Premium sidebar buttons styling */
    div[data-testid="column"]:has(.settings-nav-marker) button {{
        width: 100% !important;
        height: 42px !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 12px !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        color: #4b5563 !important; /* Cool dark-gray */
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        box-shadow: none !important;
    }}

    /* Center layout for button icons & labels inside Streamlit button elements */
    div[data-testid="column"]:has(.settings-nav-marker) button div[data-testid="stMarkdownContainer"] p {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        margin: 0 !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
    }}

    /* Hover animation */
    div[data-testid="column"]:has(.settings-nav-marker) button:hover {{
        background: rgba(37, 99, 235, 0.04) !important;
        color: #1e3a8a !important;
        transform: translateY(-0.5px) translateX(2px) !important;
    }}

    /* Active style */
    div[data-testid="column"]:has(.settings-nav-marker) button[kind="primary"],
    div[data-testid="column"]:has(.settings-nav-marker) button[data-testid="stBaseButton-primary"] {{
        background: rgba(37, 99, 235, 0.07) !important;
        color: #2563eb !important;
        font-weight: 600 !important;
        border-color: rgba(37, 99, 235, 0.12) !important;
    }}

    /* Left active indicator bar */
    div[data-testid="column"]:has(.settings-nav-marker) button[kind="primary"]::before,
    div[data-testid="column"]:has(.settings-nav-marker) button[data-testid="stBaseButton-primary"]::before {{
        content: '';
        position: absolute;
        left: 0;
        top: 10px;
        bottom: 10px;
        width: 3px;
        background-color: #2563eb;
        border-radius: 2px;
    }}

    /* Responsive navigation on smaller screens (Tablet/Mobile) */
    @media (max-width: 768px) {{
        div[data-testid="stHorizontalBlock"]:has(.settings-nav-marker) {{
            display: flex !important;
            flex-direction: column !important;
            gap: 16px !important;
        }}

        /* Convert columns stack to horizontal tabs block */
        div[data-testid="column"]:has(.settings-nav-marker) {{
            display: flex !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            gap: 8px !important;
            padding-bottom: 8px !important;
            width: 100% !important;
            flex: 1 1 100% !important;
            max-width: 100% !important;
            white-space: nowrap !important;
            scrollbar-width: none;
        }}
        div[data-testid="column"]:has(.settings-nav-marker)::-webkit-scrollbar {{
            display: none;
        }}

        div[data-testid="column"]:has(.settings-nav-marker) div[data-testid="stElementContainer"] {{
            width: auto !important;
            flex: 0 0 auto !important;
        }}

        div[data-testid="column"]:has(.settings-nav-marker) button {{
            width: auto !important;
            min-width: 120px !important;
            padding: 6px 14px !important;
        }}
        div[data-testid="column"]:has(.settings-nav-marker) button:hover {{
            transform: none !important;
        }}
        div[data-testid="column"]:has(.settings-nav-marker) button[kind="primary"]::before,
        div[data-testid="column"]:has(.settings-nav-marker) button[data-testid="stBaseButton-primary"]::before {{
            display: none !important;
        }}
    }}

    /* Settings card */
    .s-card {{
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 24px 28px;
        margin-bottom: 16px;
        box-shadow: 0 2px 12px rgba(15,23,42,0.05);
        transition: box-shadow 0.2s ease;
    }}
    .s-card:hover {{ box-shadow: 0 6px 24px rgba(15,23,42,0.09); }}
    .s-card-title {{
        font-size: 0.72rem; font-weight: 800;
        color: #94A3B8; letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 16px;
        display: flex; align-items: center; gap: 8px;
    }}
    .s-card-title-lg {{
        font-size: 1.05rem; font-weight: 800;
        color: #111827; margin-bottom: 4px;
    }}
    .s-card-subtitle {{ font-size: 0.82rem; color: #6B7280; margin-bottom: 18px; }}

    /* Row items inside cards */
    .s-row {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 0; border-bottom: 1px solid #F1F5F9;
        gap: 16px;
    }}
    .s-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .s-row-label {{ font-size: 0.9rem; font-weight: 600; color: #111827; }}
    .s-row-desc {{ font-size: 0.75rem; color: #9CA3AF; margin-top: 2px; }}

    /* Color swatch buttons */
    .color-swatches {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }}
    .color-swatch {{
        width: 34px; height: 34px; border-radius: 50%;
        border: 3px solid transparent; cursor: pointer;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }}
    .color-swatch:hover {{ transform: scale(1.15); }}
    .color-swatch.selected {{
        border-color: #111827;
        box-shadow: 0 0 0 2px white, 0 0 0 4px #111827;
    }}

    /* Pill option group */
    .pill-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .pill-opt {{
        padding: 7px 18px; border-radius: 20px;
        font-size: 0.82rem; font-weight: 600;
        border: 1.5px solid #E5E7EB;
        background: #F9FAFB; color: #6B7280;
        cursor: pointer; transition: all 0.18s ease;
    }}
    .pill-opt:hover {{ border-color: #2563EB; color: #2563EB; background: #EFF6FF; }}
    .pill-opt.selected {{
        background: #EFF6FF; color: #1D4ED8;
        border-color: #2563EB;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
    }}

    /* Security item */
    .sec-item {{
        display: flex; align-items: center; gap: 16px;
        padding: 16px 0; border-bottom: 1px solid #F1F5F9;
    }}
    .sec-item:last-child {{ border-bottom: none; }}
    .sec-icon {{
        width: 42px; height: 42px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem; flex-shrink: 0;
    }}
    .sec-icon-blue {{ background: rgba(37,99,235,0.1); }}
    .sec-icon-green {{ background: rgba(22,163,74,0.1); }}
    .sec-icon-red {{ background: rgba(220,38,38,0.08); }}
    .sec-icon-amber {{ background: rgba(245,158,11,0.1); }}
    .sec-item-title {{ font-size: 0.9rem; font-weight: 700; color: #111827; }}
    .sec-item-desc {{ font-size: 0.75rem; color: #9CA3AF; margin-top: 2px; }}
    .sec-status {{
        margin-left: auto; flex-shrink: 0;
        font-size: 0.72rem; font-weight: 700; padding: 3px 10px;
        border-radius: 12px;
    }}
    .status-ok {{ background: rgba(22,163,74,0.1); color: #15803D; }}
    .status-warn {{ background: rgba(245,158,11,0.1); color: #B45309; }}
    .status-off {{ background: rgba(156,163,175,0.15); color: #6B7280; }}

    /* Notif toggle row */
    .notif-row {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 13px 0; border-bottom: 1px solid #F1F5F9;
    }}
    .notif-row:last-child {{ border-bottom: none; }}
    .notif-icon {{
        width: 36px; height: 36px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0; margin-right: 12px;
    }}
    .notif-left {{ display: flex; align-items: center; }}
    .notif-title {{ font-size: 0.88rem; font-weight: 600; color: #111827; }}
    .notif-desc {{ font-size: 0.73rem; color: #9CA3AF; margin-top: 1px; }}

    /* Danger zone */
    .danger-card {{
        background: rgba(220,38,38,0.03);
        border: 1px solid rgba(220,38,38,0.15);
        border-radius: 16px; padding: 20px 24px;
    }}
    .danger-title {{ font-size: 0.82rem; font-weight: 800; color: #DC2626; margin-bottom: 6px; }}
    .danger-desc {{ font-size: 0.8rem; color: #6B7280; margin-bottom: 14px; }}

    /* Help FAQ */
    .faq-item {{
        padding: 14px 0; border-bottom: 1px solid #F1F5F9;
    }}
    .faq-item:last-child {{ border-bottom: none; }}
    .faq-q {{ font-size: 0.88rem; font-weight: 700; color: #111827; margin-bottom: 6px; }}
    .faq-a {{ font-size: 0.8rem; color: #6B7280; line-height: 1.5; }}

    /* About card */
    .about-stat {{
        text-align: center; padding: 16px 12px;
        background: #F8FAFC; border-radius: 12px;
    }}
    .about-stat-val {{ font-size: 1.3rem; font-weight: 900; color: #111827; }}
    .about-stat-lbl {{ font-size: 0.72rem; color: #9CA3AF; font-weight: 600; margin-top: 2px; }}
    /* ── Settings form field improvements ── */
    /* Icon-prefixed inputs inside the account panel */
    .s-field-wrap {{ margin-bottom: 16px; }}
    .s-field-label {{
        font-size: 0.76rem; font-weight: 700; color: #374151;
        margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
    }}
    .s-field-icon {{
        width: 16px; height: 16px; display: inline-flex;
        align-items: center; justify-content: center; font-size: 0.85rem;
        flex-shrink: 0;
    }}
    .s-field-hint {{
        font-size: 0.68rem; color: #94A3B8; margin-top: 4px;
    }}

    /* Make settings text inputs more premium */
    div[data-testid="column"]:has(button#acc_save_btn) [data-testid="stTextInput"] input,
    div[data-testid="column"]:has(button#acc_cancel_btn) [data-testid="stTextInput"] input {{
        border: 1.5px solid #E5E7EB !important;
        border-radius: 10px !important;
        height: 44px !important;
        font-size: 0.88rem !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }}
    div[data-testid="column"]:has(button#acc_save_btn) [data-testid="stTextInput"] input:hover,
    div[data-testid="column"]:has(button#acc_cancel_btn) [data-testid="stTextInput"] input:hover {{
        border-color: #94A3B8 !important;
    }}
    div[data-testid="column"]:has(button#acc_save_btn) [data-testid="stTextInput"] input:focus,
    div[data-testid="column"]:has(button#acc_cancel_btn) [data-testid="stTextInput"] input:focus {{
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
        outline: none !important;
    }}

    /* Prominent Save / Cancel button row */
    .s-btn-row {{ display: flex; gap: 10px; margin-top: 20px; }}
    .s-save-btn-wrap button[kind="primary"] {{
        height: 48px !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.25) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }}
    .s-save-btn-wrap button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37,99,235,0.35) !important;
    }}
    .s-cancel-btn-wrap button {{
        height: 48px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        border: 1.5px solid #E5E7EB !important;
        color: #6B7280 !important;
        background: #F9FAFB !important;
    }}
    .s-cancel-btn-wrap button:hover {{
        border-color: #94A3B8 !important;
        color: #374151 !important;
        background: #F3F4F6 !important;
    }}

    /* Danger zone — standalone separated card */
    .danger-zone-wrapper {{
        border: 2px solid rgba(220,38,38,0.22);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(254,242,242,0.8) 0%, rgba(255,255,255,0.9) 100%);
        padding: 22px 26px;
        margin-top: 24px;
    }}
    .danger-zone-header {{
        display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
    }}
    .danger-zone-icon {{
        width: 36px; height: 36px; border-radius: 10px;
        background: rgba(220,38,38,0.1);
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0;
    }}
    .danger-zone-title {{
        font-size: 1rem; font-weight: 800; color: #DC2626;
    }}
    .danger-zone-subtitle {{
        font-size: 0.78rem; font-weight: 600; color: #9B1C1C; opacity: 0.7;
    }}
    .danger-zone-desc {{
        font-size: 0.82rem; color: #6B7280; line-height: 1.55;
        margin-bottom: 16px; margin-top: 4px;
    }}
    .danger-zone-confirm-label {{
        font-size: 0.75rem; font-weight: 700; color: #991B1B;
        margin-bottom: 6px; letter-spacing: 0.03em;
    }}

    /* Account overview enriched rows */
    .s-overview-stat {{
        display: flex; align-items: center; gap: 10px;
        padding: 11px 0; border-bottom: 1px solid #F1F5F9;
    }}
    .s-overview-stat:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .s-ov-icon {{
        width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 0.85rem;
    }}
    .s-ov-label {{ font-size: 0.78rem; font-weight: 700; color: #374151; }}
    .s-ov-value {{ font-size: 0.72rem; color: #6B7280; margin-top: 1px; }}

    /* Profile Information card enhanced header */
    .s-profile-hdr {{
        padding: 20px 24px 16px;
        border-bottom: 1px solid #F1F5F9;
        margin-bottom: 4px;
    }}
    .s-profile-hdr-title {{
        font-size: 1.05rem; font-weight: 800; color: #111827; margin-bottom: 3px;
    }}
    .s-profile-hdr-sub {{
        font-size: 0.8rem; color: #6B7280; margin-bottom: 8px;
    }}
    .s-profile-hdr-status {{
        display: inline-flex; align-items: center; gap: 5px;
        font-size: 0.7rem; font-weight: 700; color: #16A34A;
        background: rgba(22,163,74,0.08); border: 1px solid rgba(22,163,74,0.18);
        border-radius: 20px; padding: 2px 10px;
    }}
    .s-profile-hdr-dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #16A34A; display: inline-block; flex-shrink: 0;
    }}

    /* Nav sidebar tighter spacing */
    div[data-testid="column"]:has(.settings-nav-marker) {{
        gap: 4px !important;
    }}
    div[data-testid="column"]:has(.settings-nav-marker) div[data-testid="stElementContainer"] {{
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }}
    .s-nav-section-label {{
        font-size: 0.6rem; font-weight: 800; color: #CBD5E1;
        letter-spacing: 0.1em; text-transform: uppercase;
        padding: 8px 4px 2px; margin-top: 4px;
    }}

    /* Enhanced profile dropdown */
    .pd-tier-badge {{
        display: inline-flex; align-items: center; gap: 4px;
        background: linear-gradient(135deg,#FEF3C7,#FDE68A);
        color: #92400E; border: 1px solid #F59E0B44;
        font-size: 0.65rem; font-weight: 800;
        padding: 2px 8px; border-radius: 20px;
        margin-top: 4px; letter-spacing: 0.03em;
    }}
    .pd-item-danger {{
        padding: 8px 16px !important;
        font-size: 0.82rem;
        color: #DC2626 !important;
        cursor: pointer;
        transition: background 0.15s ease !important;
        display: flex; align-items: center; gap: 8px;
        box-sizing: border-box !important;
    }}
    .pd-item-danger:hover {{ background: rgba(220,38,38,0.06) !important; }}
    </style>
    """, unsafe_allow_html=True)

    # ── Initialize state ──────────────────────────────────────────────────────
    if "settings_sub_tab" not in st.session_state:
        st.session_state.settings_sub_tab = "account"
    if "notifications" not in st.session_state:
        st.session_state.notifications = [
            {"id": 1, "title": "🎯 Price Target Hit", "desc": "HAL.NS crossed ₹4,212.2 (+2.1%)", "time": "5 mins ago", "read": False, "type": "price"},
            {"id": 2, "title": "💼 Portfolio Milestone", "desc": "Portfolio value crossed ₹25 Crore!", "time": "2 hours ago", "read": False, "type": "portfolio"},
            {"id": 3, "title": "🔔 Market Alert", "desc": "Nifty 50 opened +0.45% above 50-day EMA", "time": "Today, 9:15 AM", "read": True, "type": "market"},
            {"id": 4, "title": "🤖 AI Insights Ready", "desc": "Weekly sector rotation report is ready for viewing", "time": "Yesterday", "read": True, "type": "ai"}
        ]
    if "acc_name_val" not in st.session_state:
        st.session_state.acc_name_val = "Nitin Rajgor"
    if "acc_email_val" not in st.session_state:
        st.session_state.acc_email_val = "nitin@fintech.com"
    if "acc_phone_val" not in st.session_state:
        st.session_state.acc_phone_val = "+91 98765 43210"
    if "acc_tier_val" not in st.session_state:
        st.session_state.acc_tier_val = "Enterprise Pro"

    # ── Hero Profile Card ──────────────────────────────────────────────────────
    names_list = st.session_state.acc_name_val.split()
    initials = "".join([n[0] for n in names_list[:2]]).upper() if names_list else "U"
    unread_cnt = sum(1 for n in st.session_state.notifications if not n["read"])

    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <div style="font-size:1.75rem;font-weight:900;color:#111827;letter-spacing:-0.03em;">⚙️ Settings</div>
        <div style="font-size:0.9rem;color:#6B7280;margin-top:2px;">Manage your account, appearance, and preferences.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="settings-hero">
        <div class="settings-hero-left">
            <div class="settings-avatar" style="position:relative;">
                {initials}
                <div class="settings-avatar-dot"></div>
            </div>
            <div>
                <div class="settings-hero-name">{st.session_state.acc_name_val}</div>
                <div class="settings-hero-meta">📧 {st.session_state.acc_email_val} &nbsp;·&nbsp; 📱 {st.session_state.acc_phone_val}</div>
                <div class="settings-hero-badges">
                    <span class="settings-badge badge-pro">⭐ {st.session_state.acc_tier_val}</span>
                    <span class="settings-badge badge-active">● Active</span>
                    <span class="settings-badge badge-verified">✓ Verified</span>
                    {'<span class="settings-badge" style="background:rgba(220,38,38,0.1);color:#DC2626;border:1px solid rgba(220,38,38,0.2);">🔔 ' + str(unread_cnt) + ' unread</span>' if unread_cnt > 0 else ''}
                </div>
            </div>
        </div>
        <div style="font-size:0.75rem;color:#9CA3AF;text-align:right;flex-shrink:0;">
            <div style="font-weight:700;color:#374151;font-size:0.82rem;">Member Since</div>
            <div style="margin-top:2px;">11 Jun 2025</div>
            <div style="margin-top:8px;font-weight:700;color:#374151;font-size:0.82rem;">Last Login</div>
            <div style="margin-top:2px;">{ist_now().strftime('%d %b %Y, %I:%M %p')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    sub_tab = st.session_state.settings_sub_tab
    col_nav, col_content = st.columns([1, 3.2], gap="medium")

    with col_nav:
        st.markdown('<div class="settings-nav-marker"></div>', unsafe_allow_html=True)
        tab_defs = [
            ("👤", "Account",          "account"),
            ("🎨", "Appearance",       "appearance"),
            ("🔔", f"Notifications{f' ({unread_cnt})' if unread_cnt > 0 else ''}", "notifications"),
            ("🔒", "Security",         "security"),
            ("🤖", "AI Preferences",   "ai"),
            ("📊", "Dashboard",        "dashboard"),
            ("🌐", "Advanced",         "preferences"),
            ("❓", "Help & Support",   "help"),
        ]
        for icon, label, key in tab_defs:
            # Section divider before Help & Support
            if key == "help":
                st.markdown('<div class="s-nav-section-label">Support</div>', unsafe_allow_html=True)
            is_active = (sub_tab == key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon}  {label}", key=f"stab_{key}", use_container_width=True, type=btn_type):
                st.session_state.settings_sub_tab = key
                st.rerun()

    with col_content:
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 1 — ACCOUNT
        # ════════════════════════════════════════════════════════════════════════════
        if sub_tab == "account":
    
            c1, c2 = st.columns([3, 2], gap="large")
    
            with c1:
                # Profile details card — enhanced header
                st.markdown(f"""
                <div class="s-card" style="padding:0 0 20px 0;overflow:hidden;">
                    <div class="s-profile-hdr">
                        <div class="s-profile-hdr-title">👤 Profile Information</div>
                        <div class="s-profile-hdr-sub">Keep your contact details and account info up to date.</div>
                        <span class="s-profile-hdr-status">
                            <span class="s-profile-hdr-dot"></span>
                            Changes are saved when you click Save Changes
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
                name_input  = st.text_input("Full Name",      value=st.session_state.acc_name_val,  key="acc_name",  placeholder="Your full name")
                email_input = st.text_input("Email Address",  value=st.session_state.acc_email_val, key="acc_email", placeholder="you@email.com")
                phone_input = st.text_input("Phone Number",   value=st.session_state.acc_phone_val, key="acc_phone", placeholder="+91 XXXXX XXXXX")
                tiers = ["Enterprise Pro", "Premium Partner", "Retail Tier"]
                try:
                    tier_idx = tiers.index(st.session_state.acc_tier_val)
                except ValueError:
                    tier_idx = 0
                tier_input = st.selectbox("Account Tier", tiers, index=tier_idx, key="acc_tier")
    
                st.markdown('<div class="s-btn-row">', unsafe_allow_html=True)
                save_col, cancel_col = st.columns([2, 1])
                with save_col:
                    st.markdown('<div class="s-save-btn-wrap">', unsafe_allow_html=True)
                    if st.button("💾 Save Changes", key="acc_save_btn", type="primary", use_container_width=True):
                        if not name_input.strip():
                            st.error("Name cannot be empty.")
                        elif "@" not in email_input or "." not in email_input:
                            st.error("Invalid email format.")
                        elif not phone_input.strip():
                            st.error("Phone number is required.")
                        else:
                            st.session_state.acc_name_val  = name_input.strip()
                            st.session_state.acc_email_val = email_input.strip()
                            st.session_state.acc_phone_val = phone_input.strip()
                            st.session_state.acc_tier_val  = tier_input
                            st.toast("✅ Profile updated successfully!")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with cancel_col:
                    st.markdown('<div class="s-cancel-btn-wrap">', unsafe_allow_html=True)
                    if st.button("↩ Cancel", key="acc_cancel_btn", use_container_width=True):
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
            with c2:
                # Enriched Account Overview card
                st.markdown(f"""
                <div class="s-card" style="margin-bottom:12px;">
                    <div class="s-card-title">📋 Account Overview</div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(37,99,235,0.08);">🪪</div>
                        <div><div class="s-ov-label">Account ID</div><div class="s-ov-value">FTH-2025-0011</div></div>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(245,158,11,0.08);">⭐</div>
                        <div style="flex:1;"><div class="s-ov-label">Plan</div><div class="s-ov-value">{st.session_state.acc_tier_val}</div></div>
                        <span class="settings-badge badge-pro">Active</span>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(22,163,74,0.08);">🔐</div>
                        <div style="flex:1;"><div class="s-ov-label">2FA Status</div><div class="s-ov-value">Email OTP enabled</div></div>
                        <span class="sec-status status-ok">ON</span>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(99,102,241,0.08);">💾</div>
                        <div style="flex:1;"><div class="s-ov-label">Data Storage</div><div class="s-ov-value">Local (on-device)</div></div>
                        <span class="sec-status status-ok">Secure</span>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(14,165,233,0.08);">🕐</div>
                        <div><div class="s-ov-label">Last Login</div><div class="s-ov-value">{ist_now().strftime('%d %b %Y, %I:%M %p')}</div></div>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(139,92,246,0.08);">📅</div>
                        <div><div class="s-ov-label">Member Since</div><div class="s-ov-value">11 Jun 2025</div></div>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(236,72,153,0.08);">📱</div>
                        <div style="flex:1;"><div class="s-ov-label">Active Devices</div><div class="s-ov-value">1 active session (this browser)</div></div>
                        <span class="sec-status status-ok">1</span>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(16,185,129,0.08);">🔄</div>
                        <div><div class="s-ov-label">Next Billing</div><div class="s-ov-value">11 Jul 2026 · Auto-renews</div></div>
                    </div>
                    <div class="s-overview-stat">
                        <div class="s-ov-icon" style="background:rgba(245,158,11,0.08);">🔑</div>
                        <div style="flex:1;"><div class="s-ov-label">API Access</div><div class="s-ov-value">Read-only endpoints enabled</div></div>
                        <span class="sec-status status-ok">On</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
            # ── Danger Zone — full-width standalone card below columns ──
            st.markdown("""
            <div class="danger-zone-wrapper">
                <div class="danger-zone-header">
                    <div class="danger-zone-icon">⚠️</div>
                    <div>
                        <div class="danger-zone-title">Danger Zone</div>
                        <div class="danger-zone-subtitle">Irreversible destructive actions</div>
                    </div>
                </div>
                <div class="danger-zone-desc">
                    Resetting portfolio data will permanently clear <strong>all holdings, orders, and trade history</strong>.
                    Your cash balance will return to <strong>₹1,00,00,000</strong>. This action cannot be undone.
                </div>
                <div class="danger-zone-confirm-label">⌨️ Type RESET below to unlock the confirm button</div>
            </div>
            """, unsafe_allow_html=True)
            danger_confirm = st.text_input(
                "", placeholder="Type RESET to confirm",
                key="danger_confirm_input", label_visibility="collapsed"
            )
            reset_ready = danger_confirm.strip().upper() == "RESET"
            if st.button(
                "🚨 Confirm — Reset All Portfolio Data",
                key="settings_data_reset",
                type="secondary" if not reset_ready else "primary",
                use_container_width=False,
                disabled=not reset_ready
            ):
                st.session_state.pt_cash     = 10000000.0
                st.session_state.pt_holdings = {}
                st.session_state.pt_history  = []
                st.session_state.pt_targets  = []
                save_portfolio()
                st.success("✅ Portfolio reset to ₹1 Crore.")
                st.rerun()
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 2 — APPEARANCE
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "appearance":
    
            st.markdown(f"""
            <div class="s-card">
                <div class="s-card-title">🎨 Interface Theme</div>
                <div class="s-row">
                    <div>
                        <div class="s-row-label">Color Mode</div>
                        <div class="s-row-desc">Currently locked to Light — dark mode coming soon</div>
                    </div>
                    <span class="sec-status status-ok">☀️ Light</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
            # Accent color
            accent_now = st.session_state.settings_accent
            st.markdown(f"""
            <div class="s-card">
                <div class="s-card-title">🌈 Accent Color</div>
                <div style="font-size:0.85rem;color:#6B7280;margin-bottom:14px;">Choose the primary color used across charts, buttons, and highlights.</div>
            </div>
            """, unsafe_allow_html=True)
    
            acc_col1, acc_col2, acc_col3, acc_col4 = st.columns(4)
            accent_map = [
                ("🔵 Blue",   "Blue",   acc_col1, "#2563EB"),
                ("🟣 Purple", "Purple", acc_col2, "#8B5CF6"),
                ("🟢 Green",  "Green",  acc_col3, "#059669"),
                ("🟠 Orange", "Orange", acc_col4, "#EA580C"),
            ]
            for label, key_val, col, _ in accent_map:
                with col:
                    is_sel = accent_now == key_val
                    if st.button(label, key=f"accent_btn_{key_val.lower()}", type="primary" if is_sel else "secondary", use_container_width=True):
                        st.session_state.settings_accent = key_val
                        save_preferences()
                        st.rerun()
    
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    
            # Font size
            font_now = st.session_state.settings_font_size
            st.markdown(f"""
            <div class="s-card">
                <div class="s-card-title">🔤 Font Size</div>
                <div style="font-size:0.85rem;color:#6B7280;margin-bottom:14px;">Controls text size across all dashboard panels and cards.</div>
            </div>
            """, unsafe_allow_html=True)
    
            fc1, fc2, fc3, _ = st.columns([1, 1, 1, 2])
            for label, key_val, col in [("Small", "Small", fc1), ("Medium", "Medium", fc2), ("Large", "Large", fc3)]:
                with col:
                    is_sel = font_now == key_val
                    if st.button(f"{'🔡' if key_val == 'Small' else '🔤' if key_val == 'Medium' else '🔠'} {label}", key=f"font_btn_{key_val.lower()}", type="primary" if is_sel else "secondary", use_container_width=True):
                        st.session_state.settings_font_size = key_val
                        save_preferences()
                        st.rerun()
    
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    
            # Density
            density_now = st.session_state.settings_density
            st.markdown(f"""
            <div class="s-card">
                <div class="s-card-title">📐 UI Spacing Density</div>
                <div style="font-size:0.85rem;color:#6B7280;margin-bottom:14px;">Controls padding and spacing between elements across all pages.</div>
            </div>
            """, unsafe_allow_html=True)
    
            dc1, dc2, dc3, _ = st.columns([1, 1, 1, 2])
            for label, key_val, col in [("Compact", "Compact", dc1), ("Comfortable", "Comfortable", dc2), ("Spacious", "Spacious", dc3)]:
                with col:
                    is_sel = density_now == key_val
                    if st.button(label, key=f"density_btn_{key_val.lower()}", type="primary" if is_sel else "secondary", use_container_width=True):
                        st.session_state.settings_density = key_val
                        save_preferences()
                        st.rerun()
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 3 — NOTIFICATIONS
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "notifications":
    
            nc1, nc2 = st.columns([3, 2], gap="large")
    
            with nc1:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">📡 Alert Channels</div>
                    <div class="notif-row">
                        <div class="notif-left">
                            <div class="notif-icon" style="background:rgba(37,99,235,0.08);">📈</div>
                            <div><div class="notif-title">Market Alerts</div><div class="notif-desc">Nifty / Sensex milestone movements</div></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
                notif_items = [
                    ("notify_market",    "📈", "Market Alerts",     "Nifty / Sensex milestone movements",         "rgba(37,99,235,0.08)"),
                    ("notify_price",     "🎯", "Price Alerts",      "Target price hits on watchlist stocks",       "rgba(22,163,74,0.08)"),
                    ("notify_portfolio", "💼", "Portfolio Alerts",  "P&L changes and portfolio milestones",        "rgba(245,158,11,0.08)"),
                    ("notify_news",      "📰", "News Alerts",       "Sector rotation and market news",             "rgba(139,92,246,0.08)"),
                    ("notify_ai",        "🤖", "AI Alerts",         "Weekly AI insight and analysis updates",      "rgba(14,165,233,0.08)"),
                    ("notify_email",     "📧", "Email Digest",      "Daily portfolio and market summary email",    "rgba(236,72,153,0.08)"),
                    ("notify_push",      "🔔", "Web Push",          "Real-time browser push notifications",        "rgba(99,102,241,0.08)"),
                ]
    
                for key_name, icon, title, desc, icon_bg in notif_items:
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #F1F5F9;">
                            <div style="width:36px;height:36px;border-radius:10px;background:{icon_bg};display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;">{icon}</div>
                            <div>
                                <div style="font-size:0.88rem;font-weight:600;color:#111827;">{title}</div>
                                <div style="font-size:0.73rem;color:#9CA3AF;">{desc}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        st.markdown("<div style='padding-top:18px'></div>", unsafe_allow_html=True)
                        st.toggle("", key=key_name, label_visibility="collapsed")
    
                save_n_col, _ = st.columns([1, 2])
                with save_n_col:
                    if st.button("💾 Save Alert Settings", key="notif_save", type="primary", use_container_width=True):
                        save_preferences()
                        st.toast("Alert settings saved!", icon="🔔")
    
            with nc2:
                # Notification Inbox
                unread = [n for n in st.session_state.notifications if not n["read"]]
                read   = [n for n in st.session_state.notifications if n["read"]]
    
                notif_type_colors = {
                    "price": ("#EFF6FF", "#2563EB", "🎯"),
                    "portfolio": ("#FEF3C7", "#D97706", "💼"),
                    "market": ("#F0FDF4", "#16A34A", "📈"),
                    "ai": ("#FAF5FF", "#9333EA", "🤖"),
                }
    
                st.markdown(f"""
                <div class="s-card" style="padding:20px 20px 12px;">
                    <div class="s-card-title">📬 Inbox
                        {f'<span style="background:#EF4444;color:white;border-radius:10px;padding:2px 7px;font-size:0.65rem;margin-left:4px;">{unread_cnt}</span>' if unread_cnt > 0 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
                if not unread and not read:
                    st.markdown('<div style="text-align:center;padding:30px;color:#9CA3AF;font-size:0.9rem;">📭 Inbox is empty</div>', unsafe_allow_html=True)
                else:
                    if unread:
                        st.markdown('<div style="font-size:0.7rem;font-weight:800;color:#6B7280;letter-spacing:0.05em;margin-bottom:8px;">UNREAD</div>', unsafe_allow_html=True)
                        for notif in unread:
                            bg, accent, icon = notif_type_colors.get(notif.get("type", "market"), ("#F8FAFC", "#6B7280", "🔔"))
                            with st.container():
                                r1, r2 = st.columns([5, 1])
                                with r1:
                                    st.markdown(f"""
                                    <div style="background:{bg};border-left:3px solid {accent};border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                                        <div style="font-weight:700;font-size:0.82rem;color:#111827;">{notif['title']}</div>
                                        <div style="font-size:0.72rem;color:#6B7280;margin-top:2px;">{notif['desc']}</div>
                                        <div style="font-size:0.65rem;color:#9CA3AF;margin-top:4px;">🕐 {notif['time']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                with r2:
                                    st.markdown("<div style='padding-top:10px'></div>", unsafe_allow_html=True)
                                    if st.button("✓", key=f"mark_read_{notif['id']}", help="Mark as read"):
                                        for n in st.session_state.notifications:
                                            if n["id"] == notif["id"]:
                                                n["read"] = True
                                        st.rerun()
    
                    if read:
                        st.markdown('<div style="font-size:0.7rem;font-weight:800;color:#9CA3AF;letter-spacing:0.05em;margin:12px 0 8px;">READ</div>', unsafe_allow_html=True)
                        for notif in read:
                            st.markdown(f'<div style="padding:8px 0;border-bottom:1px solid #F1F5F9;font-size:0.78rem;color:#9CA3AF;"><b style="color:#6B7280;">{notif["title"]}</b> — {notif["desc"]}</div>', unsafe_allow_html=True)
                        if st.button("🗑️ Clear All Read", key="clear_read_notifs", use_container_width=True):
                            st.session_state.notifications = [n for n in st.session_state.notifications if not n["read"]]
                            st.rerun()
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 4 — SECURITY
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "security":
    
            sc1, sc2 = st.columns([2, 3], gap="large")
    
            with sc1:
                # Security status card
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">🛡️ Security Status</div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-green">🔒</div>
                        <div>
                            <div class="sec-item-title">Session</div>
                            <div class="sec-item-desc">Active & secured</div>
                        </div>
                        <span class="sec-status status-ok">Secure</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-green">✅</div>
                        <div>
                            <div class="sec-item-title">Email OTP</div>
                            <div class="sec-item-desc">2FA via email</div>
                        </div>
                        <span class="sec-status status-ok">ON</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-amber">💾</div>
                        <div>
                            <div class="sec-item-title">Data Storage</div>
                            <div class="sec-item-desc">Local only</div>
                        </div>
                        <span class="sec-status status-ok">Local</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-red">📱</div>
                        <div>
                            <div class="sec-item-title">App 2FA</div>
                            <div class="sec-item-desc">Authenticator app</div>
                        </div>
                        <span class="sec-status status-off">OFF</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
                # Privacy toggles
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">🔏 Privacy Settings</div>
                </div>
                """, unsafe_allow_html=True)
                st.toggle("Share anonymous usage stats", value=False, key="priv_usage")
                st.toggle("Allow crash reports", value=True, key="priv_crash")
                st.toggle("Enable session logging", value=True, key="priv_log")
    
            with sc2:
                # Password change card
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title-lg">🔑 Change Password</div>
                    <div class="s-card-subtitle">Choose a strong password with at least 8 characters, numbers, and symbols.</div>
                </div>
                """, unsafe_allow_html=True)
    
                old_pass  = st.text_input("Current Password",     type="password", key="sec_old_pass",  placeholder="Enter current password")
                new_pass  = st.text_input("New Password",         type="password", key="sec_new_pass",  placeholder="Enter new password (min 6 chars)")
                conf_pass = st.text_input("Confirm New Password", type="password", key="sec_conf_pass", placeholder="Re-enter new password")
    
                btn_col, _ = st.columns([1, 2])
                with btn_col:
                    if st.button("🔐 Update Password", key="sec_save", type="primary", use_container_width=True):
                        import hashlib
                        current_hash = st.secrets.get("APP_PASSWORD_HASH", "")
                        if not old_pass or not new_pass or not conf_pass:
                            st.warning("Please fill in all fields.")
                        elif hashlib.sha256(old_pass.encode()).hexdigest() != current_hash:
                            st.error("❌ Current password is incorrect.")
                        elif new_pass != conf_pass:
                            st.error("❌ New passwords do not match.")
                        elif len(new_pass) < 6:
                            st.error("❌ Password must be at least 6 characters.")
                        else:
                            new_hash = hashlib.sha256(new_pass.encode()).hexdigest()
                            st.success("✅ Password verified! Update secrets.toml with the hash below:")
                            st.code(f'APP_PASSWORD_HASH = "{new_hash}"', language="toml")
                            st.toast("Password verification successful!", icon="🔐")
    
                # Active sessions
                st.markdown(f"""
                <div class="s-card" style="margin-top:16px;">
                    <div class="s-card-title">💻 Active Sessions</div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-blue">🖥️</div>
                        <div>
                            <div class="sec-item-title">Windows PC — Chrome</div>
                            <div class="sec-item-desc">localhost:8501 · {ist_now().strftime('%d %b %Y, %I:%M %p')}</div>
                        </div>
                        <span class="sec-status status-ok">Current</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 5 — AI PREFERENCES
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "ai":
    
            ai1, ai2 = st.columns([3, 2], gap="large")
    
            with ai1:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title-lg">🤖 AI Analytics Preferences</div>
                    <div class="s-card-subtitle">Configure how the AI engine analyses your portfolio and generates insights.</div>
                </div>
                """, unsafe_allow_html=True)
    
                st.selectbox("Analysis Depth", ["Quick Scan", "Standard", "Deep Analysis"], index=1, key="ai_mode_pref")
                st.selectbox("Response Language", ["English", "Hinglish", "Hindi"], key="ai_lang_pref")
                st.selectbox("Chart Insight Style", ["Technical", "Fundamental", "Hybrid"], key="ai_chart_style")
    
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">⚙️ AI Behaviour</div>
                </div>
                """, unsafe_allow_html=True)
    
                st.toggle("Auto-analyse on portfolio load", value=False, key="ai_auto_pref")
                st.toggle("Show confidence scores on signals", value=True, key="ai_confidence")
                st.toggle("Include macro factors in analysis", value=True, key="ai_macro")
                st.toggle("Enable sector rotation alerts", value=False, key="ai_sector_alert")
    
                save_ai_col, _ = st.columns([1, 2])
                with save_ai_col:
                    if st.button("💾 Save AI Preferences", key="ai_pref_save", type="primary", use_container_width=True):
                        st.toast("AI preferences saved!", icon="🤖")
    
            with ai2:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">📊 AI Engine Status</div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-green">⚡</div>
                        <div>
                            <div class="sec-item-title">RSI Engine</div>
                            <div class="sec-item-desc">14-period momentum</div>
                        </div>
                        <span class="sec-status status-ok">Active</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-blue">📉</div>
                        <div>
                            <div class="sec-item-title">MA Signals</div>
                            <div class="sec-item-desc">20 / 50 day SMA</div>
                        </div>
                        <span class="sec-status status-ok">Active</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-amber">🧠</div>
                        <div>
                            <div class="sec-item-title">Sentiment NLP</div>
                            <div class="sec-item-desc">Keyword-based</div>
                        </div>
                        <span class="sec-status status-ok">Active</span>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-red">🔮</div>
                        <div>
                            <div class="sec-item-title">ML Predictor</div>
                            <div class="sec-item-desc">Linear regression</div>
                        </div>
                        <span class="sec-status status-ok">Active</span>
                    </div>
                </div>
    
                <div class="s-card" style="margin-top:12px;">
                    <div class="s-card-title">🧬 Model Info</div>
                    <div class="s-row">
                        <div class="s-row-label">Algorithm</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Rule-based + Regression</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Data Source</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Yahoo Finance + News RSS</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">No External LLM</div>
                        <div style="font-size:0.8rem;color:#16A34A;font-weight:700;">✓ Privacy-first</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 6 — DASHBOARD CONFIG
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "dashboard":
    
            d1, d2 = st.columns([3, 2], gap="large")
    
            with d1:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title-lg">📊 Dashboard Configuration</div>
                    <div class="s-card-subtitle">Control which widgets and panels appear on your main dashboard view.</div>
                </div>
                """, unsafe_allow_html=True)
    
                dash_widgets = [
                    ("dash_pnl",    "💰 P&L Banner",              "Show live P&L summary at top",             True),
                    ("dash_ticker", "📺 Live Ticker Strip",        "Scrolling index prices below header",       True),
                    ("dash_news",   "📰 News Panel",               "Market news on dashboard home",             True),
                    ("dash_cal",    "📅 Calendar Events",          "Upcoming RBI / F&O events widget",          True),
                ]
                for key_n, title, desc, default in dash_widgets:
                    col_lbl, col_tog = st.columns([4, 1])
                    with col_lbl:
                        st.markdown(f"""
                        <div style="padding:10px 0;border-bottom:1px solid #F1F5F9;">
                            <div style="font-size:0.88rem;font-weight:600;color:#111827;">{title}</div>
                            <div style="font-size:0.73rem;color:#9CA3AF;">{desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_tog:
                        st.markdown("<div style='padding-top:16px'></div>", unsafe_allow_html=True)
                        st.toggle("", value=default, key=key_n, label_visibility="collapsed")
    
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.selectbox("Default Chart Type", ["Candlestick", "Line", "Area", "OHLC"], key="dash_chart")
    
                save_d_col, _ = st.columns([1, 2])
                with save_d_col:
                    if st.button("💾 Save Dashboard Settings", key="dash_save", type="primary", use_container_width=True):
                        st.toast("Dashboard settings saved!", icon="✅")
    
            with d2:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">🔢 Layout Info</div>
                    <div class="s-row">
                        <div class="s-row-label">Current Layout</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Wide / Desktop</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Sidebar</div>
                        <div style="font-size:0.8rem;color:#6B7280;">260px fixed</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Content Area</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Fluid, max 1200px</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Auto Refresh</div>
                        <div style="font-size:0.8rem;color:#16A34A;font-weight:700;">60s (market hours)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 7 — PREFERENCES
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "preferences":
    
            landing_options = {
                "home": "Dashboard", "portfolio": "Portfolio", "watchlist": "Watchlist",
                "market": "Market", "news": "News", "screener": "Screener", "calendar": "Calendar"
            }
            current_landing = st.session_state.get("pref_landing", "home")
            if current_landing not in landing_options:
                current_landing = "home"
            landing_keys   = list(landing_options.keys())
            landing_labels = list(landing_options.values())
            try:
                default_idx = landing_keys.index(current_landing)
            except ValueError:
                default_idx = 0
    
            p1, p2 = st.columns([3, 2], gap="large")
    
            with p1:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title-lg">🌐 App Preferences</div>
                    <div class="s-card-subtitle">Personalise your default app experience and data display options.</div>
                </div>
                """, unsafe_allow_html=True)
    
                selected_landing_label = st.selectbox("Default Landing Page", landing_labels, index=default_idx, key="pref_landing_select")
                st.selectbox("Currency Display", ["INR (₹)", "USD ($)", "EUR (€)"], key="pref_currency")
                st.selectbox("Date Format", ["DD MMM YYYY", "DD/MM/YYYY", "MM/DD/YYYY"], key="pref_date")
                st.selectbox("Default Watchlist Sort", ["Ticker A-Z", "Price High-Low", "Change % High", "Change % Low"], key="pref_watchlist_sort")
                st.selectbox("Default Chart View", ["Candlestick", "Line", "Area"], key="pref_chart_view")
    
                pref_save_col, _ = st.columns([1, 2])
                with pref_save_col:
                    if st.button("💾 Save Preferences", key="pref_save", type="primary", use_container_width=True):
                        selected_key = landing_keys[landing_labels.index(selected_landing_label)]
                        st.session_state.pref_landing = selected_key
                        save_preferences()
                        st.toast("Preferences saved!", icon="✅")
    
            with p2:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">⭐ Visible Dashboard Cards</div>
                </div>
                """, unsafe_allow_html=True)
                card_opts = ["Portfolio Value", "Daily P&L", "Cash Balance", "Total Invested", "Win Rate", "Active Holdings"]
                visible_cards = st.session_state.get("pref_visible_cards", ["Portfolio Value", "Daily P&L", "Cash Balance", "Total Invested"])
                new_visible = st.multiselect("Show on dashboard", card_opts, default=visible_cards, key="pref_visible_cards_sel", label_visibility="collapsed")
    
        # ════════════════════════════════════════════════════════════════════════════
        # PANEL 8 — HELP & SUPPORT
        # ════════════════════════════════════════════════════════════════════════════
        elif sub_tab == "help":
    
            h1, h2 = st.columns([3, 2], gap="large")
    
            with h1:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title-lg">❓ Help & Support</div>
                    <div class="s-card-subtitle">Frequently asked questions and usage guides for FintechHub.</div>
                </div>
                """, unsafe_allow_html=True)
    
                faqs = [
                    ("📋 How do I track my portfolio?",
                     "Go to Portfolio → click Buy → enter stock symbol, quantity, and price → confirm. Holdings update in real time."),
                    ("🔔 How do I set price alerts?",
                     "Go to Watchlist → click the ⚡ action button on any stock → set your target price for auto-execution."),
                    ("📊 Where does market data come from?",
                     "Live prices are fetched from Yahoo Finance (yfinance). News comes from Google News RSS filtered for Indian markets."),
                    ("🤖 How does AI analysis work?",
                     "AI uses RSI(14), Moving Averages (20/50 day), Volume Ratio, and sentiment scoring. It is fully rule-based — no external LLM."),
                    ("⚙️ Can I reset portfolio data?",
                     "Yes — Settings → Account → Danger Zone → Reset All Portfolio Data. Cash resets to ₹1 Crore, all trades cleared."),
                    ("📱 Is it mobile friendly?",
                     "The app is responsive and adapts to laptop, tablet, and mobile viewports. For best experience, use desktop."),
                ]
    
                for q, a in faqs:
                    with st.expander(q):
                        st.markdown(f'<div style="font-size:0.85rem;color:#4B5563;line-height:1.6;">{a}</div>', unsafe_allow_html=True)
    
            with h2:
                st.markdown(f"""
                <div class="s-card">
                    <div class="s-card-title">📬 Contact Support</div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-blue">📧</div>
                        <div>
                            <div class="sec-item-title">Email</div>
                            <div class="sec-item-desc">nitin@fintech.com</div>
                        </div>
                    </div>
                    <div class="sec-item">
                        <div class="sec-icon sec-icon-green">⚡</div>
                        <div>
                            <div class="sec-item-title">Response Time</div>
                            <div class="sec-item-desc">Within 24 hours</div>
                        </div>
                    </div>
                </div>
    
                <div class="s-card" style="margin-top:12px;">
                    <div class="s-card-title">ℹ️ About FintechHub</div>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                        <div style="width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#2563EB,#60A5FA);color:white;display:flex;align-items:center;justify-content:center;font-size:1.3rem;">💎</div>
                        <div>
                            <div style="font-weight:800;font-size:0.95rem;color:#111827;">FintechHub v2.0</div>
                            <div style="font-size:0.75rem;color:#6B7280;">Stock Market Simulator & Visualizer</div>
                        </div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Framework</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Streamlit</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Data</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Yahoo Finance, Google RSS</div>
                    </div>
                    <div class="s-row">
                        <div class="s-row-label">Charts</div>
                        <div style="font-size:0.8rem;color:#6B7280;">Plotly</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
elif tab in ("defence", "broking", "renewable", "ev_tech", "banking"):
    st.session_state.last_sector_tab = tab

    # ── Sector pill-selector — ek hi jagah se sab 5 sectors switch karo ───────
    _sector_options = [
        ("defence",   "🪖 Defence"),
        ("broking",   "🏦 Broking"),
        ("renewable", "☀️ Renewable"),
        ("ev_tech",   "⚡ EV & Tech"),
        ("banking",   "🏧 Banking"),
    ]
    _pc = st.columns(5)
    for _pcol, (_skey, _slabel) in zip(_pc, _sector_options):
        with _pcol:
            if st.button(_slabel, key=f"sector_pill_{_skey}", width='stretch',
                         type="primary" if tab == _skey else "secondary"):
                st.session_state.active_tab = _skey
                st.session_state.last_sector_tab = _skey
                st.rerun()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

if tab == "defence":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    OLIVE  = "#7c9a3a"; STEEL = "#4a7fa5"; SAFFRON = "#f97316"
    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, GREEN, RED, BLUE
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f1f0a,#0a1520);
                border:1px solid #7c9a3a55;border-radius:16px;padding:18px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.2rem;">🪖</div>
        <div>
          <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">
            India Defence Budget & Order Tracker
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
            FY22–FY26 budget trend · Company-wise orders · Stock impact analysis
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── DATA ─────────────────────────────────────────────────────────────────

    # India Defence Budget (₹ Crore)
    budget_data = {
        "FY22": {"total": 478195, "capital": 153763, "revenue": 324432, "gdp_pct": 2.1},
        "FY23": {"total": 525166, "capital": 162600, "revenue": 362566, "gdp_pct": 2.0},
        "FY24": {"total": 593537, "capital": 172000, "revenue": 421537, "gdp_pct": 1.9},
        "FY25": {"total": 621541, "capital": 196422, "revenue": 425119, "gdp_pct": 1.9},
        "FY26": {"total": 681210, "capital": 227000, "revenue": 454210, "gdp_pct": 1.9},
    }

    # Company order books (₹ Crore) — approximate public data
    company_orders = {
        # ── Large Cap Defence PSUs ────────────────────────────────────────────
        "HAL":        {"FY22":83000, "FY23":94000, "FY24":105000,"FY25":130000,"FY26":150000,
                       "color":"#3b82f6","sector":"Aerospace / IAF",
                       "about":"Tejas, LCH, ALH helicopters. India ka sabse bada aerospace PSU.",
                       "ticker":"HAL.NS"},
        "MAZDOCK":    {"FY22":38000, "FY23":42000, "FY24":47000, "FY25":56000, "FY26":65000,
                       "color":"#27ae60","sector":"Naval / Submarines",
                       "about":"P75I submarines, destroyers, frigates. Mumbai shipyard.",
                       "ticker":"MAZDOCK.NS"},
        "GRSE":       {"FY22":12000, "FY23":14000, "FY24":17000, "FY25":20000, "FY26":24000,
                       "color":"#f59e0b","sector":"Naval / Frigates",
                       "about":"ASW corvettes, survey vessels, fast patrol vessels. Kolkata.",
                       "ticker":"GRSE.NS"},
        "COCHINSHIP": {"FY22":5000,  "FY23":6500,  "FY24":9000,  "FY25":12000, "FY26":15000,
                       "color":"#a78bfa","sector":"Naval / Repair",
                       "about":"IAC Vikrant banaya. Ship repair + new build. Kochi.",
                       "ticker":"COCHINSHIP.NS"},
        # ── Mid Cap Defence ───────────────────────────────────────────────────
        "DATAPATTNS": {"FY22":600,   "FY23":900,   "FY24":1400,  "FY25":1900,  "FY26":2600,
                       "color":"#e74c3c","sector":"Radar / Electronics",
                       "about":"Radar warning, EW systems, missile seekers. DRDO supplier.",
                       "ticker":"DATAPATTNS.NS"},
        "ZENTEC":     {"FY22":400,   "FY23":600,   "FY24":900,   "FY25":1300,  "FY26":1800,
                       "color":"#84cc16","sector":"Simulation / Training",
                       "about":"Army combat simulators, tank simulators, drone training.",
                       "ticker":"ZENTEC.NS"},
        "PARAS":      {"FY22":800,   "FY23":1100,  "FY24":1600,  "FY25":2200,  "FY26":3000,
                       "color":"#06b6d4","sector":"Optics / Space",
                       "about":"Space optics, night vision, electro-optic systems.",
                       "ticker":"PARAS.NS"},
        "UNIMECH":    {"FY22":180,   "FY23":280,   "FY24":420,   "FY25":620,   "FY26":900,
                       "color":"#f43f5e","sector":"Aerospace Components",
                       "about":"Precision aero-engine parts, landing gear components. HAL supplier.",
                       "ticker":"UNIMECH.NS"},
        "IDEAFORGE":  {"FY22":120,   "FY23":200,   "FY24":320,   "FY25":480,   "FY26":700,
                       "color":"#fb923c","sector":"Drones / UAV",
                       "about":"India ka #1 drone maker. Army, BSF, NDRF contracts.",
                       "ticker":"IDEAFORGE.NS"},
        "KRISHNADEF": {"FY22":150,   "FY23":220,   "FY24":350,   "FY25":520,   "FY26":750,
                       "color":"#c084fc","sector":"Naval Systems",
                       "about":"Naval gun mounts, deck machinery, ship systems.",
                       "ticker":"KRISHNADEF.NS"},
        # ── Financial / Tech (Defence adjacent) ──────────────────────────────
        "BSE":        {"FY22":0,     "FY23":0,     "FY24":0,     "FY25":0,     "FY26":0,
                       "color":"#64748b","sector":"Financial Exchange",
                       "about":"Stock exchange — defence sector mein indirect play via listings.",
                       "ticker":"BSE.NS"},
        "ANGELONE":   {"FY22":0,     "FY23":0,     "FY24":0,     "FY25":0,     "FY26":0,
                       "color":"#94a3b8","sector":"Broking / Fintech",
                       "about":"Stockbroker — defence rally mein trading volume se benefit.",
                       "ticker":"ANGELONE.NS"},
        "KPITTECH":   {"FY22":800,   "FY23":1100,  "FY24":1600,  "FY25":2200,  "FY26":3000,
                       "color":"#38bdf8","sector":"Defence Software / EV",
                       "about":"Embedded software for aerospace, defence electronics systems.",
                       "ticker":"KPITTECH.NS"},
        "JAINREC":    {"FY22":200,   "FY23":280,   "FY24":400,   "FY25":560,   "FY26":780,
                       "color":"#4ade80","sector":"Recycling / Critical Metals",
                       "about":"Critical metal recycling — defence manufacturing supply chain.",
                       "ticker":"JAINREC.NS"},
    }

    years = ["FY22","FY23","FY24","FY25","FY26"]

    # ── 3 SUB-TABS ────────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(["📈 Budget Trend", "🏭 Company Orders", "📊 Stock Impact", "🚨 Readiness Index"])

    # ════════════════════════════════════════════════════════════════════════
    # SUB-TAB 1 — Budget Trend
    # ════════════════════════════════════════════════════════════════════════
    with t1:
        totals   = [budget_data[y]["total"]   for y in years]
        capitals = [budget_data[y]["capital"] for y in years]
        revenues = [budget_data[y]["revenue"] for y in years]
        gdp_pcts = [budget_data[y]["gdp_pct"] for y in years]

        # KPI strip
        fy26 = budget_data["FY26"]; fy22 = budget_data["FY22"]
        growth = round((fy26["total"] - fy22["total"]) / fy22["total"] * 100, 1)
        cap_growth = round((fy26["capital"] - fy22["capital"]) / fy22["capital"] * 100, 1)

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;">
          <div style="background:{CARD_BG};border:1px solid {OLIVE}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {OLIVE};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">FY26 TOTAL BUDGET</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">₹6.81L Cr</div>
            <div style="font-size:0.65rem;color:{OLIVE};margin-top:2px;">+{growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {STEEL}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {STEEL};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">FY26 CAPITAL OUTLAY</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">₹2.27L Cr</div>
            <div style="font-size:0.65rem;color:{STEEL};margin-top:2px;">+{cap_growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SAFFRON}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {SAFFRON};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">% OF GDP</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">1.9%</div>
            <div style="font-size:0.65rem;color:{SAFFRON};margin-top:2px;">Target: 3% by 2030</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {PURPLE};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">DOMESTIC PROCUREMENT</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">75%</div>
            <div style="font-size:0.65rem;color:{PURPLE};margin-top:2px;">Make in India push</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Stacked bar — Capital vs Revenue
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            name="Capital (New weapons/equipment)",
            x=years, y=capitals,
            marker_color=STEEL,
            text=[f"₹{v//1000:.0f}K Cr" for v in capitals],
            textposition="inside", textfont=dict(size=10, color="white"),
        ))
        fig1.add_trace(go.Bar(
            name="Revenue (Salaries/maintenance)",
            x=years, y=revenues,
            marker_color="#2a3d5a",
            text=[f"₹{v//1000:.0f}K Cr" for v in revenues],
            textposition="inside", textfont=dict(size=10, color="#8b90a0"),
        ))
        # Total line
        fig1.add_trace(go.Scatter(
            name="Total Budget",
            x=years, y=totals,
            mode="lines+markers+text",
            line=dict(color=SAFFRON, width=2.5),
            marker=dict(size=8, color=SAFFRON),
            text=[f"₹{v/100000:.2f}L Cr" for v in totals],
            textposition="top center",
            textfont=dict(size=9, color=SAFFRON),
        ))
        fig1.update_layout(
            barmode="stack",
            paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
            font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
            margin=dict(l=10, r=10, t=30, b=10),
            height=320,
            legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
            xaxis=dict(gridcolor=CHART_GRID),
            yaxis=dict(gridcolor=CHART_GRID, title="₹ Crore"),
            title=dict(text="India Defence Budget FY22–FY26", font=dict(size=13, color=TEXT), x=0.5),
        )
        st.plotly_chart(fig1, width='stretch', key="budget_chart")

        # Key insight cards
        st.markdown(f"""
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;">
          <div style="flex:1;min-width:200px;background:{CARD_BG};border:1px solid {BORDER};
                      border-radius:10px;padding:12px 14px;border-left:3px solid {OLIVE};">
            <div style="font-size:0.7rem;font-weight:700;color:{OLIVE};margin-bottom:4px;">
              🎯 Make in India
            </div>
            <div style="font-size:0.78rem;color:{TEXT};">
              75% capital budget ab domestic companies ke liye reserved — HAL, MAZDOCK, BEL sabse bade beneficiary.
            </div>
          </div>
          <div style="flex:1;min-width:200px;background:{CARD_BG};border:1px solid {BORDER};
                      border-radius:10px;padding:12px 14px;border-left:3px solid {STEEL};">
            <div style="font-size:0.7rem;font-weight:700;color:{STEEL};margin-bottom:4px;">
              🚢 Naval Expansion
            </div>
            <div style="font-size:0.78rem;color:{TEXT};">
              30-year naval plan — 200+ warships, submarines chahiye. MAZDOCK, GRSE, COCHINSHIP ke liye 20+ saal ka order pipeline.
            </div>
          </div>
          <div style="flex:1;min-width:200px;background:{CARD_BG};border:1px solid {BORDER};
                      border-radius:10px;padding:12px 14px;border-left:3px solid {SAFFRON};">
            <div style="font-size:0.7rem;font-weight:700;color:{SAFFRON};margin-bottom:4px;">
              ✈️ IAF Modernisation
            </div>
            <div style="font-size:0.78rem;color:{TEXT};">
              AMCA, Tejas Mk2, 114 fighter jets — HAL ke liye ₹1.5L Cr+ orders pipeline mein hain next 5 years.
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SUB-TAB 2 — Company Orders
    # ════════════════════════════════════════════════════════════════════════
    with t2:
        # Company selector
        sel_companies = st.multiselect(
            "Companies select karo",
            list(company_orders.keys()),
            default=["HAL","MAZDOCK","GRSE","COCHINSHIP","DATAPATTNS","ZENTEC","PARAS","UNIMECH","IDEAFORGE","KRISHNADEF","KPITTECH"],
            key="def_companies",
            label_visibility="collapsed",
        )

        if sel_companies:
            # Line chart — order book trend
            fig2 = go.Figure()
            for comp in sel_companies:
                d = company_orders[comp]
                vals = [d[y] for y in years]
                fig2.add_trace(go.Scatter(
                    name=comp,
                    x=years, y=vals,
                    mode="lines+markers+text",
                    line=dict(color=d["color"], width=2.5),
                    marker=dict(size=7, color=d["color"]),
                    text=[f"₹{v//1000:.0f}K" for v in vals],
                    textposition="top center",
                    textfont=dict(size=8),
                ))
            fig2.update_layout(
                paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
                margin=dict(l=10, r=10, t=30, b=10), height=300,
                legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
                xaxis=dict(gridcolor=CHART_GRID),
                yaxis=dict(gridcolor=CHART_GRID, title="Order Book (₹ Cr)"),
                title=dict(text="Company-wise Order Book Trend", font=dict(size=13, color=TEXT), x=0.5),
            )
            st.plotly_chart(fig2, width='stretch', key="orders_chart")

            # FY26 order share pie
            fig3 = go.Figure(data=[go.Pie(
                labels=sel_companies,
                values=[company_orders[c]["FY26"] for c in sel_companies],
                marker_colors=[company_orders[c]["color"] for c in sel_companies],
                hole=0.45,
                textinfo="label+percent",
                textfont=dict(size=11),
            )])
            fig3.update_layout(
                paper_bgcolor=CHART_PAPER_BG,
                font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
                margin=dict(l=10, r=10, t=30, b=10), height=280,
                title=dict(text="FY26 Order Book Share", font=dict(size=12, color=TEXT), x=0.5),
                showlegend=False,
            )
            st.plotly_chart(fig3, width='stretch', key="pie_chart")

            # Company cards
            st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};'
                        f'letter-spacing:0.1em;margin-bottom:8px;">COMPANY DETAILS</div>',
                        unsafe_allow_html=True)
            for comp in sel_companies:
                d = company_orders[comp]
                fy22_val = d["FY22"]; fy26_val = d["FY26"]
                is_non_defence = fy26_val == 0
                growth_pct = round((fy26_val - fy22_val) / fy22_val * 100, 1) if fy22_val > 0 else 0
                yoy = round((fy26_val - d["FY25"]) / d["FY25"] * 100, 1) if d["FY25"] > 0 else 0

                order_str = (
                    f'₹{fy26_val//1000:.0f},000 Cr' if fy26_val >= 1000
                    else (f'₹{fy26_val} Cr' if fy26_val > 0 else "N/A — Indirect play")
                )
                growth_html = (
                    f'<div><span style="font-size:0.65rem;color:{MUTED};">FY22 se growth</span>'
                    f'<span style="font-size:0.82rem;font-weight:700;color:{GREEN};margin-left:6px;">+{growth_pct}%</span></div>'
                    f'<div><span style="font-size:0.65rem;color:{MUTED};">YoY (FY25→26)</span>'
                    f'<span style="font-size:0.82rem;font-weight:700;color:{GREEN};margin-left:6px;">+{yoy}%</span></div>'
                    if not is_non_defence else
                    f'<div><span style="font-size:0.72rem;color:{MUTED};">Defence sector rally se indirect benefit hota hai</span></div>'
                )
                about_txt = d.get("about","")
                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {d['color']}44;
                            border-radius:12px;padding:14px 16px;margin-bottom:8px;
                            border-left:4px solid {d['color']};">
                  <div style="display:flex;justify-content:space-between;
                              align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">
                    <div>
                      <span style="font-size:1rem;font-weight:800;color:{TEXT};">{comp}</span>
                      <span style="background:{d['color']}22;color:{d['color']};border-radius:4px;
                                   padding:1px 8px;font-size:0.65rem;font-weight:700;margin-left:8px;">
                        {d['sector']}
                      </span>
                    </div>
                    <div style="text-align:right;">
                      <span style="font-size:1.05rem;font-weight:900;color:{d['color']};">
                        {order_str}
                      </span>
                      <span style="font-size:0.7rem;color:{MUTED};margin-left:6px;">FY26 order book</span>
                    </div>
                  </div>
                  <div style="font-size:0.72rem;color:{MUTED};margin-bottom:8px;
                              font-style:italic;">{about_txt}</div>
                  <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    {growth_html}
                  </div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SUB-TAB 3 — Stock Impact
    # ════════════════════════════════════════════════════════════════════════
    with t3:
        st.markdown(f"""
        <div style="font-size:0.7rem;font-weight:800;color:{MUTED};
                    letter-spacing:0.1em;margin-bottom:12px;">
          📊 BUDGET ANNOUNCEMENT PE STOCK REACTION (HISTORICAL)
        </div>""", unsafe_allow_html=True)

        # Historical budget day reactions — sirf Defence stocks
        reactions = [
            {"stock":"HAL",        "fy":"FY26 Budget","1d":"+4.2%","1w":"+8.1%","1m":"+12.3%","trigger":"IAF fighter jet order ₹65,000 Cr","color":BLUE},
            {"stock":"MAZDOCK",    "fy":"FY26 Budget","1d":"+6.8%","1w":"+11.2%","1m":"+18.5%","trigger":"Navy submarine program extended","color":GREEN},
            {"stock":"GRSE",       "fy":"FY26 Budget","1d":"+5.1%","1w":"+9.4%","1m":"+15.2%","trigger":"Next-gen frigate order confirmed","color":SAFFRON},
            {"stock":"COCHINSHIP", "fy":"FY25 Budget","1d":"+3.8%","1w":"+7.2%","1m":"+22.1%","trigger":"Shipyard capacity expansion funded","color":PURPLE},
            {"stock":"DATAPATTNS", "fy":"FY25 Budget","1d":"+7.2%","1w":"+15.8%","1m":"+35.6%","trigger":"Radar & defence electronics order","color":RED},
            {"stock":"ZENTEC",     "fy":"FY25 Budget","1d":"+5.7%","1w":"+12.3%","1m":"+28.4%","trigger":"Army simulation training contract","color":"#84cc16"},
            {"stock":"PARAS",      "fy":"FY25 Budget","1d":"+8.3%","1w":"+14.6%","1m":"+31.2%","trigger":"Night vision + space optics order","color":"#06b6d4"},
            {"stock":"UNIMECH",    "fy":"FY26 Budget","1d":"+9.1%","1w":"+17.4%","1m":"+38.2%","trigger":"HAL aero-engine component supply chain","color":"#f43f5e"},
            {"stock":"IDEAFORGE",  "fy":"FY26 Budget","1d":"+11.4%","1w":"+19.8%","1m":"+42.5%","trigger":"Army drone procurement ₹500 Cr","color":"#fb923c"},
            {"stock":"KRISHNADEF", "fy":"FY25 Budget","1d":"+6.3%","1w":"+13.1%","1m":"+29.7%","trigger":"Naval gun mount & deck machinery order","color":"#c084fc"},
            {"stock":"BEL",        "fy":"FY26 Budget","1d":"+3.9%","1w":"+8.6%","1m":"+16.4%","trigger":"Electronic warfare & radar systems order","color":"#38bdf8"},
            {"stock":"BEML",       "fy":"FY25 Budget","1d":"+4.4%","1w":"+9.8%","1m":"+19.3%","trigger":"Mining + defence vehicle supply contract","color":"#fbbf24"},
            {"stock":"MIDHANI",    "fy":"FY26 Budget","1d":"+5.2%","1w":"+11.0%","1m":"+21.7%","trigger":"Special alloys for missiles & aerospace","color":"#a78bfa"},
            {"stock":"MTAR",       "fy":"FY25 Budget","1d":"+6.7%","1w":"+13.5%","1m":"+27.8%","trigger":"ISRO & DRDO precision component orders","color":"#34d399"},
        ]

        for r in reactions:
            d1c = GREEN if "+" in r["1d"] else RED
            d7c = GREEN if "+" in r["1w"] else RED
            d30c= GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;
                        border-radius:12px;padding:13px 16px;margin-bottom:8px;
                        border-left:4px solid {r['color']};">
              <div style="display:flex;justify-content:space-between;
                          align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{r['stock']}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{r['fy']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  <div style="text-align:center;">
                    <div style="font-size:0.58rem;color:{MUTED};">1 DAY</div>
                    <div style="font-size:0.82rem;font-weight:800;color:{d1c};">{r['1d']}</div>
                  </div>
                  <div style="text-align:center;">
                    <div style="font-size:0.58rem;color:{MUTED};">1 WEEK</div>
                    <div style="font-size:0.82rem;font-weight:800;color:{d7c};">{r['1w']}</div>
                  </div>
                  <div style="text-align:center;">
                    <div style="font-size:0.58rem;color:{MUTED};">1 MONTH</div>
                    <div style="font-size:0.82rem;font-weight:800;color:{d30c};">{r['1m']}</div>
                  </div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};">
                🎯 <span style="color:{r['color']}">{r['trigger']}</span>
              </div>
            </div>""", unsafe_allow_html=True)

        # Next budget countdown
        from datetime import date
        next_budget = date(2026, 2, 1)
        days_left   = (next_budget - date.today()).days
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f1f0a,#0a1520);
                    border:1px solid {OLIVE}55;border-radius:12px;
                    padding:16px 20px;margin-top:14px;text-align:center;">
          <div style="font-size:0.7rem;font-weight:800;color:{OLIVE};
                      letter-spacing:0.1em;margin-bottom:6px;">⏰ NEXT UNION BUDGET</div>
          <div style="font-size:1.8rem;font-weight:900;color:#f0f3ff;">
            {days_left} din baad
          </div>
          <div style="font-size:0.82rem;color:{MUTED};margin-top:4px;">
            1 February 2026 · Defence allocation expected ↑8-10%
          </div>
          <div style="font-size:0.75rem;color:{OLIVE};margin-top:8px;">
            💡 Budget se 2-4 weeks pehle defence stocks mein positioning hoti hai
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SUB-TAB 4 — DEFENCE READINESS INDEX
    # ════════════════════════════════════════════════════════════════════════
    with t4:
        # Header
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a0505,#0a0a1a);
                    border:1px solid #dc262655;border-radius:14px;
                    padding:16px 20px;margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="font-size:2.2rem;">🚨</div>
            <div>
              <div style="font-size:1rem;font-weight:900;color:#f0f3ff;">
                Defence Readiness Index
              </div>
              <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
                Live geopolitical news se automatically calculate hota hai ·
                India-Pakistan · India-China · Border tension · Military alerts
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Refresh
        ri_c1, ri_c2 = st.columns([4, 1])
        with ri_c2:
            if st.button("🔄 Refresh", key="ri_refresh", width='stretch'):
                fetch_readiness_news.clear()
                st.rerun()

        # Fetch
        with st.spinner("🌐 Geopolitical news scan ho rahi hai..."):
            ri = fetch_readiness_news()

        sc    = ri["score"]
        level = ri["level"]
        color = ri["color"]
        bg    = ri["bg"]
        emoji = ri["emoji"]

        # ── Big Score Display ─────────────────────────────────────────────────
        # Gauge bar (0-10 segments)
        filled = int(sc)
        partial= sc - filled
        segments_html = ""
        for i in range(10):
            if i < filled:
                seg_color = color
                opacity   = "1"
            elif i == filled and partial > 0:
                seg_color = color
                opacity   = f"{partial:.1f}"
            else:
                seg_color = "#2a2d3a"
                opacity   = "1"
            segments_html += (
                f'<div style="flex:1;height:14px;background:{seg_color};'
                f'opacity:{opacity};border-radius:3px;margin:0 2px;"></div>'
            )

        st.markdown(f"""
        <div style="background:{bg};border:2px solid {color}55;
                    border-radius:16px;padding:22px 24px;margin-bottom:14px;">
          <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
            <!-- Score -->
            <div style="text-align:center;min-width:110px;">
              <div style="font-size:4rem;font-weight:900;color:{color};
                          line-height:1;letter-spacing:-2px;">{sc}</div>
              <div style="font-size:0.65rem;color:#8b90a0;margin-top:2px;">OUT OF 10</div>
            </div>
            <!-- Details -->
            <div style="flex:1;">
              <div style="font-size:1.1rem;font-weight:900;color:{color};margin-bottom:6px;">
                {emoji} {level} TENSION
              </div>
              <div style="display:flex;gap:2px;margin-bottom:10px;">
                {segments_html}
              </div>
              <div style="font-size:0.82rem;color:#e8eaf0;margin-bottom:8px;">
                {ri['advice']}
              </div>
              <div style="background:{color}22;border:1px solid {color}44;
                          border-radius:8px;padding:6px 12px;display:inline-block;">
                <span style="font-size:0.7rem;font-weight:800;color:{color};">
                  📊 STOCK SIGNAL: {ri['stock_signal']}
                </span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Keyword hits strip ────────────────────────────────────────────────
        if ri["keyword_hits"]:
            kw_html = ""
            sorted_kw = sorted(ri["keyword_hits"].items(), key=lambda x: -x[1])[:8]
            for kw, cnt in sorted_kw:
                intensity = min(cnt * 30, 100)
                kw_html += (
                    f'<span style="background:{color}{intensity:02x};color:{color};'
                    f'border:1px solid {color}55;border-radius:20px;'
                    f'padding:3px 10px;font-size:0.68rem;font-weight:700;margin:2px;">'
                    f'{kw} ×{cnt}</span>'
                )
            st.markdown(f"""
            <div style="margin-bottom:14px;">
              <div style="font-size:0.65rem;color:#8b90a0;font-weight:700;
                          letter-spacing:0.1em;margin-bottom:6px;">
                🔍 DETECTED KEYWORDS
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:4px;">{kw_html}</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Stock impact table ────────────────────────────────────────────────
        st.markdown(f"""
        <div style="font-size:0.68rem;font-weight:800;color:#8b90a0;
                    letter-spacing:0.1em;margin-bottom:8px;">
          📈 AAPKE STOCKS PE EXPECTED IMPACT (Score {sc}/10)
        </div>""", unsafe_allow_html=True)

        STOCK_SENSITIVITY = [
            ("MAZDOCK",    "Naval",     "⭐⭐⭐⭐⭐", 5, "Warships/submarines — war tension pe #1 beneficiary"),
            ("GRSE",       "Naval",     "⭐⭐⭐⭐⭐", 5, "Frigate builder — naval conflict pe direct benefit"),
            ("COCHINSHIP", "Naval",     "⭐⭐⭐⭐",  4, "Ship repair + build — naval mobilization pe rally"),
            ("HAL",        "Aerospace", "⭐⭐⭐⭐⭐", 5, "Fighter jets — IAF alert pe fastest mover"),
            ("IDEAFORGE",  "Drones",    "⭐⭐⭐⭐⭐", 5, "Drones — modern warfare ka sabse important asset"),
            ("PARAS",      "Optics",    "⭐⭐⭐⭐",  4, "Night vision/optics — border patrol demand badhti hai"),
            ("ZENTEC",     "Simulation","⭐⭐⭐",    3, "Army training sims — medium sensitivity"),
            ("DATAPATTNS", "Radar",     "⭐⭐⭐⭐",  4, "Radar/EW systems — air defence demand pe rally"),
            ("UNIMECH",    "Components","⭐⭐⭐",    3, "Aero parts — indirect, HAL order flow pe depend"),
            ("KRISHNADEF", "Naval Sys", "⭐⭐⭐⭐",  4, "Naval gun systems — warship armament demand"),
            ("KPITTECH",   "Software",  "⭐⭐",     2, "Defence software — indirect, low sensitivity"),
            ("BSE",        "Exchange",  "⭐",       1, "Indirect — trading volume badh sakta hai"),
            ("ANGELONE",   "Broking",   "⭐",       1, "Indirect — retail defence trading volume"),
            ("JAINREC",    "Metals",    "⭐⭐",     2, "Critical metals — supply chain mein"),
        ]

        for stk, sector, stars, sens, desc in STOCK_SENSITIVITY:
            # Calculate expected move based on score
            base_move = (sc / 10) * sens * 3  # max 15% for score=10, sens=5
            move_str  = f"+{base_move:.1f}%" if base_move > 0 else "~0%"
            bar_w     = int(sens * 20)
            bar_color = color if sens >= 4 else ("#f59e0b" if sens >= 3 else "#8b90a0")

            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2a2d3a;
                        border-radius:10px;padding:11px 14px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:5px;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-size:0.9rem;font-weight:800;color:#e8eaf0;">{stk}</span>
                  <span style="background:{bar_color}22;color:{bar_color};border-radius:4px;
                               padding:1px 7px;font-size:0.63rem;font-weight:700;">{sector}</span>
                  <span style="font-size:0.72rem;">{stars}</span>
                </div>
                <div style="text-align:right;">
                  <span style="font-size:0.9rem;font-weight:800;
                               color:{'#27ae60' if base_move > 3 else ('#f59e0b' if base_move > 1 else '#8b90a0')};">
                    {move_str}
                  </span>
                  <span style="font-size:0.62rem;color:#8b90a0;margin-left:4px;">expected</span>
                </div>
              </div>
              <div style="background:#13161f;border-radius:3px;height:4px;margin-bottom:5px;">
                <div style="background:{bar_color};width:{bar_w}%;height:4px;border-radius:3px;"></div>
              </div>
              <div style="font-size:0.67rem;color:#5b6380;font-style:italic;">{desc}</div>
            </div>""", unsafe_allow_html=True)

        # ── Live News Feed ────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="font-size:0.68rem;font-weight:800;color:#8b90a0;
                    letter-spacing:0.1em;margin:14px 0 8px;">
          📰 LIVE GEOPOLITICAL NEWS ({ri['total_articles']} articles scanned)
        </div>""", unsafe_allow_html=True)

        if ri["news"]:
            for n in ri["news"][:15]:
                ns = n["item_score"]
                nc = color if ns >= 2 else ("#f59e0b" if ns >= 1 else "#8b90a0")
                score_badge = (
                    f'<span style="background:{nc}22;color:{nc};border:1px solid {nc}44;'
                    f'border-radius:4px;padding:1px 7px;font-size:0.65rem;font-weight:700;">'
                    f'Score +{ns}</span>' if ns > 0 else ""
                )
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid {'#dc262633' if ns>=2 else '#2a2d3a'};
                            border-radius:10px;padding:11px 14px;margin-bottom:6px;
                            border-left:3px solid {nc};">
                  <div style="font-size:0.85rem;font-weight:600;color:#e8eaf0;
                              line-height:1.5;margin-bottom:6px;">{n['title']}</div>
                  <div style="display:flex;justify-content:space-between;
                              align-items:center;flex-wrap:wrap;gap:6px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                      {score_badge}
                      <span style="background:#1a1f30;color:#8b90a0;border-radius:4px;
                                   padding:1px 7px;font-size:0.63rem;">{n['source']}</span>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;">
                      <span style="font-size:0.63rem;color:#5b6380;">🕐 {n['time']}</span>
                      <a href="{n['link']}" target="_blank"
                         style="color:#3b82f6;font-size:0.7rem;font-weight:600;
                                text-decoration:none;">Padho →</a>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:center;padding:40px;color:#8b90a0;">
              <div style="font-size:2rem;">🕊️</div>
              <div style="margin-top:8px;">Koi geopolitical tension news nahi mili</div>
              <div style="font-size:0.75rem;margin-top:4px;">Peaceful situation hai!</div>
            </div>""", unsafe_allow_html=True)

        # Footer note
        st.markdown(f"""
        <div style="text-align:center;margin-top:12px;font-size:0.65rem;color:#2e3347;">
          ⚠️ Ye AI-generated analysis hai — investment advice nahi.
          Score real news se calculate hota hai, 15 min mein auto-refresh.
        </div>""", unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════════
if tab == "broking":
    import plotly.graph_objects as go

    GOLD   = "#f59e0b"; TEAL = "#14b8a6"
    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, GREEN, RED, BLUE
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    _bh, _br = st.columns([5,1])
    with _bh:
        st.markdown('<div class="sec-title">BROKING & FINTECH</div>', unsafe_allow_html=True)
    with _br:
        if st.button("🔄", key="broking_refresh", help="Refresh karo"):
            get_index_quote.clear(); get_batch_quotes.clear(); st.rerun()

    # Live prices — BSE + ANGELONE (your watchlist stocks)
    _bse_q = get_index_quote("BSE.NS")
    _ang_q = get_index_quote("ANGELONE.NS")
    _live_cols = st.columns(2)
    for _col, (_ticker, _name, _q, _border) in zip(_live_cols, [
        ("BSE", "BSE Ltd", _bse_q, "#3b82f6"),
        ("ANGELONE", "Angel One", _ang_q, "#f59e0b"),
    ]):
        with _col:
            if _q:
                _c, _, _chg, _pct = _q
                _clr = "#27ae60" if _chg >= 0 else "#e74c3c"
                _arr = "▲" if _chg >= 0 else "▼"
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid {_border}44;border-radius:10px;
                            padding:10px 14px;margin-bottom:12px;">
                  <div style="font-size:0.65rem;color:#8b90a0;font-weight:700;margin-bottom:2px;">
                    YOUR STOCK
                  </div>
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:0.88rem;font-weight:800;color:#f0f3ff;">{_ticker}</span>
                    <div>
                      <span style="font-size:0.95rem;font-weight:900;color:#f0f3ff;">₹{_c:,.2f}</span>
                      <span style="color:{_clr};font-size:0.75rem;font-weight:700;margin-left:6px;">
                        {_arr}{abs(_pct):.2f}%
                      </span>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f1a2a,#1a1200);
                border:1px solid #f59e0b55;border-radius:16px;padding:18px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.2rem;">🏦</div>
        <div>
          <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">
            India Broking & Fintech Sector Tracker
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
            FY22–FY26 revenue trend · Company-wise metrics · Stock impact analysis
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    revenue_data = {
        "FY22": {"total": 28500, "retail": 18000, "institutional": 10500, "demat_cr": 7.5},
        "FY23": {"total": 31200, "retail": 20000, "institutional": 11200, "demat_cr": 9.8},
        "FY24": {"total": 38600, "retail": 25500, "institutional": 13100, "demat_cr": 13.1},
        "FY25": {"total": 46800, "retail": 31200, "institutional": 15600, "demat_cr": 17.6},
        "FY26": {"total": 56200, "retail": 37800, "institutional": 18400, "demat_cr": 22.0},
    }

    company_data_b = {
        "BSE":      {"FY22":850,  "FY23":1100, "FY24":1650, "FY25":2400, "FY26":3100,
                     "color":BLUE,"sector":"Stock Exchange","ticker":"BSE.NS",
                     "about":"India's oldest exchange. SME IPOs, derivatives, mutual fund platform."},
        "ANGELONE": {"FY22":1200, "FY23":1600, "FY24":2100, "FY25":2800, "FY26":3200,
                     "color":GOLD,"sector":"Discount Broking","ticker":"ANGELONE.NS",
                     "about":"Top 3 discount broker. 22M+ clients. AI-powered trading platform."},
        "CDSL":     {"FY22":480,  "FY23":680,  "FY24":900,  "FY25":1200, "FY26":1550,
                     "color":TEAL,"sector":"Depository","ticker":"CDSL.NS",
                     "about":"India's #1 depository. 13 Cr+ demat accounts. Monopoly-like position."},
        "MCX":      {"FY22":380,  "FY23":420,  "FY24":560,  "FY25":720,  "FY26":900,
                     "color":PURPLE,"sector":"Commodity Exchange","ticker":"MCX.NS",
                     "about":"India's largest commodity derivatives exchange. Gold, crude, metals."},
        "BROKERNET":{"FY22":290,  "FY23":380,  "FY24":490,  "FY25":640,  "FY26":820,
                     "color":"#f43f5e","sector":"Full-Service Broking","ticker":"5PAISA.NS",
                     "about":"Growing discount broker with fintech ambitions. Retail focused."},
    }

    years = ["FY22","FY23","FY24","FY25","FY26"]
    bk_t1, bk_t2, bk_t3 = st.tabs(["📈 Sector Trend", "🏭 Company Tracker", "📊 Stock Impact"])
    t1, t2, t3 = bk_t1, bk_t2, bk_t3

    with t1:
        fy26 = revenue_data["FY26"]; fy22 = revenue_data["FY22"]
        growth = round((fy26["total"]-fy22["total"])/fy22["total"]*100,1)
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;">
          <div style="background:{CARD_BG};border:1px solid {GOLD}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {GOLD};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 TOTAL REVENUE</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['total']//100:,}K Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {BLUE}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {BLUE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">RETAIL BROKING</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['retail']//100:,}K Cr</div>
            <div style="font-size:0.72rem;color:{MUTED};">67% of total</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {TEAL}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {TEAL};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">DEMAT ACCOUNTS</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['demat_cr']}Cr+</div>
            <div style="font-size:0.72rem;color:{GREEN};">India ka financialization</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:12px;
                      padding:14px;text-align:center;border-top:3px solid {PURPLE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">INSTITUTIONAL</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['institutional']//100:,}K Cr</div>
            <div style="font-size:0.72rem;color:{MUTED};">FII + DII combined</div>
          </div>
        </div>""", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Retail Broking", x=years, y=[revenue_data[y]["retail"] for y in years],
                             marker_color=BLUE, text=[f"₹{v//100:,}K Cr" for v in [revenue_data[y]["retail"] for y in years]],
                             textposition="inside", textfont=dict(size=10,color="#fff")))
        fig.add_trace(go.Bar(name="Institutional", x=years, y=[revenue_data[y]["institutional"] for y in years],
                             marker_color=TEAL, text=[f"₹{v//100:,}K Cr" for v in [revenue_data[y]["institutional"] for y in years]],
                             textposition="inside", textfont=dict(size=10,color="#fff")))
        fig.add_trace(go.Scatter(name="Total Revenue", x=years, y=[revenue_data[y]["total"] for y in years],
                                  mode="lines+markers+text", line=dict(color=GOLD,width=2.5),
                                  marker=dict(size=9,color=GOLD),
                                  text=[f"₹{v//100:,}K Cr" for v in [revenue_data[y]["total"] for y in years]],
                                  textposition="top center", textfont=dict(size=10,color=GOLD)))
        fig.update_layout(barmode="stack", paper_bgcolor=CHART_PAPER_BG, plot_bgcolor=CHART_PLOT_BG,
                          font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"), height=380,
                          margin=dict(l=60,r=20,t=40,b=40), bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Broking & Fintech Revenue FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor=CHART_GRID), yaxis=dict(gridcolor=CHART_GRID,tickprefix="₹"))
        st.plotly_chart(fig, width='stretch')

        for note in [
            (GOLD, "Retail Boom", "India mein 22 Cr+ demat accounts. Gen Z aur millennials stock market mein aa rahe hain."),
            (BLUE, "Zero Commission War", "Zerodha, Angel, Groww — discount brokers ne full-service ko disrupt kiya. Volumes 10x."),
            (TEAL, "Financialization", "Mutual fund SIP ₹20,000 Cr/month cross kiya. CDSL/BSE direct beneficiary."),
        ]:
            st.markdown(f"""
            <div style="background:{CARD_BG};border-left:4px solid {note[0]};border-radius:0 10px 10px 0;
                        padding:12px 16px;margin-bottom:8px;">
              <div style="font-size:0.78rem;font-weight:700;color:{note[0]};margin-bottom:4px;">
                💡 {note[1]}
              </div>
              <div style="font-size:0.78rem;color:{MUTED};">{note[2]}</div>
            </div>""", unsafe_allow_html=True)

    with t2:
        selected_cos = st.multiselect("Companies chuno", list(company_data.keys()), default=list(company_data.keys())[:4], key="brk_cos")
        if selected_cos:
            fig2 = go.Figure()
            for co in selected_cos:
                d = company_data_b[co]
                fig2.add_trace(go.Scatter(name=co, x=years, y=[d[y] for y in years],
                                           mode="lines+markers", line=dict(color=d["color"],width=2),
                                           marker=dict(size=8,color=d["color"])))
            fig2.update_layout(paper_bgcolor=CHART_PAPER_BG,plot_bgcolor=CHART_PLOT_BG,font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),
                               height=350,margin=dict(l=60,r=20,t=40,b=40),
                               title=dict(text="Company Revenue FY22–FY26 (₹ Cr)",font=dict(size=13,color=MUTED),x=0),
                               xaxis=dict(gridcolor=CHART_GRID),yaxis=dict(gridcolor=CHART_GRID,tickprefix="₹"))
            st.plotly_chart(fig2, width='stretch')

        for co, d in company_data.items():
            vals = [d[y] for y in years]
            gr = round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {d['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{co}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{d['sector']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  {"".join([f'<div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">{y}</div><div style="font-size:0.78rem;font-weight:700;color:{TEXT};">₹{d[y]:,}</div></div>' for y in years])}
                  <div style="text-align:center;">
                    <div style="font-size:0.58rem;color:{MUTED};">GROWTH</div>
                    <div style="font-size:0.78rem;font-weight:700;color:{GREEN};">+{gr}%</div>
                  </div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};margin-top:6px;">💡 {d['about']}</div>
            </div>""", unsafe_allow_html=True)

    with t3:
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};letter-spacing:.1em;margin-bottom:12px;">📊 MARKET EVENT PE STOCK REACTION</div>', unsafe_allow_html=True)
        reactions = [
            {"stock":"BSE",      "event":"SME IPO Boom FY25","1d":"+8.2%","1w":"+14.3%","1m":"+28.5%","trigger":"SME IPO listings 200+ in FY25. BSE ka revenue 3x hua.","color":BLUE},
            {"stock":"ANGELONE", "event":"F&O Volume Surge","1d":"+6.4%","1w":"+11.8%","1m":"+22.3%","trigger":"NSE F&O volumes ₹500 lakh Cr/day cross kiye. Angel One ko direct benefit.","color":GOLD},
            {"stock":"CDSL",     "event":"Demat 10Cr Milestone","1d":"+5.1%","1w":"+9.6%","1m":"+18.7%","trigger":"India ne 10 Cr demat accounts cross kiye. CDSL ke 70%+ market share.","color":TEAL},
            {"stock":"MCX",      "event":"Gold Rally FY24","1d":"+4.8%","1w":"+8.9%","1m":"+16.4%","trigger":"Gold ₹65,000/10g cross kiya. MCX gold trading volumes record high.","color":PURPLE},
            {"stock":"BSE",      "event":"RBI Rate Cut Signal","1d":"+3.9%","1w":"+7.2%","1m":"+14.1%","trigger":"Rate cut expectation se retail investors equity mein shift. Volumes up.","color":BLUE},
        ]
        for r in reactions:
            d1c = GREEN if "+" in r["1d"] else RED
            d7c = GREEN if "+" in r["1w"] else RED
            d30c= GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {r['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{r['stock']}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{r['event']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 DAY</div><div style="font-size:0.82rem;font-weight:800;color:{d1c};">{r['1d']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 WEEK</div><div style="font-size:0.82rem;font-weight:800;color:{d7c};">{r['1w']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 MONTH</div><div style="font-size:0.82rem;font-weight:800;color:{d30c};">{r['1m']}</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};">🎯 <span style="color:{r['color']};">{r['trigger']}</span></div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB — RENEWABLE ENERGY
# ══════════════════════════════════════════════════════════════════════════════
if tab == "renewable":
    import plotly.graph_objects as go

    SOLAR  = "#fbbf24"; WIND="#10b981"; HYDRO="#38bdf8"
    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, GREEN, RED, BLUE
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    _rh, _rr = st.columns([5,1])
    with _rh:
        st.markdown('<div class="sec-title">RENEWABLE ENERGY</div>', unsafe_allow_html=True)
    with _rr:
        if st.button("🔄", key="renewable_refresh", help="Refresh karo"):
            get_index_quote.clear(); get_batch_quotes.clear(); st.rerun()

    # Live price — JAINREC (your watchlist stock)
    _jq = get_index_quote("JAINREC.NS")
    if _jq:
        _jc, _jp, _jchg, _jpct = _jq
        _jclr = "#27ae60" if _jchg >= 0 else "#e74c3c"
        _jarr = "▲" if _jchg >= 0 else "▼"
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #fbbf2444;border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;
                    display:flex;justify-content:space-between;align-items:center;">
          <div>
            <span style="font-size:0.7rem;color:#8b90a0;font-weight:700;">YOUR STOCK</span>
            <span style="font-size:0.9rem;font-weight:800;color:#f0f3ff;margin-left:8px;">JAINREC</span>
            <span style="font-size:0.65rem;color:#8b90a0;margin-left:4px;">Jain Irrigation</span>
          </div>
          <div style="text-align:right;">
            <span style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">₹{_jc:,.2f}</span>
            <span style="color:{_jclr};font-size:0.8rem;font-weight:700;margin-left:8px;">
              {_jarr} {abs(_jpct):.2f}%
            </span>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f1a0a,#1a1500);
                border:1px solid #fbbf2455;border-radius:16px;padding:18px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.2rem;">☀️</div>
        <div>
          <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">
            India Renewable Energy Sector Tracker
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
            FY22–FY26 capacity trend · Company-wise orders · Stock impact analysis
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    capacity_data = {
        "FY22": {"total_gw":160, "solar_gw":56,  "wind_gw":42,  "other_gw":62,  "budget_cr":19500},
        "FY23": {"total_gw":179, "solar_gw":67,  "wind_gw":44,  "other_gw":68,  "budget_cr":35000},
        "FY24": {"total_gw":203, "solar_gw":82,  "wind_gw":47,  "other_gw":74,  "budget_cr":35000},
        "FY25": {"total_gw":230, "solar_gw":100, "wind_gw":50,  "other_gw":80,  "budget_cr":35000},
        "FY26": {"total_gw":265, "solar_gw":125, "wind_gw":55,  "other_gw":85,  "budget_cr":40000},
    }

    company_data = {
        "JAINREC":    {"FY22":420, "FY23":580, "FY24":820, "FY25":1150,"FY26":1600,
                       "color":SOLAR,"sector":"EPC / Recycling","ticker":"JAINREC.NS",
                       "about":"Solar EPC + critical metal recycling. Govt renewable projects supplier."},
        "ADANIGREEN": {"FY22":8200,"FY23":11000,"FY24":15000,"FY25":20000,"FY26":26000,
                       "color":GREEN,"sector":"Solar / Wind Power","ticker":"ADANIGREEN.NS",
                       "about":"India ka #1 renewable energy company. 10,000+ MW capacity target."},
        "NTPC":       {"FY22":6800,"FY23":7500,"FY24":8800,"FY25":10200,"FY26":12000,
                       "color":WIND,"sector":"Renewables + Thermal","ticker":"NTPC.NS",
                       "about":"PSU giant transitioning to renewables. 50 GW target by 2032."},
        "SJVN":       {"FY22":1200,"FY23":1500,"FY24":1900,"FY25":2500,"FY26":3200,
                       "color":HYDRO,"sector":"Hydro + Solar","ticker":"SJVN.NS",
                       "about":"Hydro PSU expanding into solar. Massive order book from govt."},
        "BOROSIL":    {"FY22":280, "FY23":380, "FY24":520, "FY25":720, "FY26":1000,
                       "color":PURPLE,"sector":"Solar Glass","ticker":"BOROSIL.NS",
                       "about":"Solar glass manufacturer. Only listed solar glass company in India."},
    }

    years = ["FY22","FY23","FY24","FY25","FY26"]
    t1, t2, t3 = st.tabs(["📈 Capacity Trend", "🏭 Company Orders", "📊 Stock Impact"])

    with t1:
        fy26 = capacity_data["FY26"]; fy22 = capacity_data["FY22"]
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;">
          <div style="background:{CARD_BG};border:1px solid {SOLAR}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {SOLAR};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 TOTAL CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['total_gw']} GW</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['total_gw']-fy22['total_gw'])/fy22['total_gw']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SOLAR}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {SOLAR};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">SOLAR CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['solar_gw']} GW</div>
            <div style="font-size:0.72rem;color:{MUTED};">Target: 500 GW by 2030</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {WIND}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {WIND};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">WIND CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['wind_gw']} GW</div>
            <div style="font-size:0.72rem;color:{MUTED};">Offshore wind starting</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {HYDRO}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {HYDRO};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">GOVT BUDGET</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['budget_cr']//1000}K Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">Green Energy Corridor</div>
          </div>
        </div>""", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Solar GW", x=years, y=[capacity_data[y]["solar_gw"] for y in years], marker_color=SOLAR))
        fig.add_trace(go.Bar(name="Wind GW",  x=years, y=[capacity_data[y]["wind_gw"]  for y in years], marker_color=WIND))
        fig.add_trace(go.Bar(name="Other GW", x=years, y=[capacity_data[y]["other_gw"] for y in years], marker_color=HYDRO))
        fig.add_trace(go.Scatter(name="Total GW", x=years, y=[capacity_data[y]["total_gw"] for y in years],
                                  mode="lines+markers+text", line=dict(color="#f97316",width=2.5),
                                  marker=dict(size=9), text=[f"{v} GW" for v in [capacity_data[y]["total_gw"] for y in years]],
                                  textposition="top center", textfont=dict(size=10,color="#f97316")))
        fig.update_layout(barmode="stack",paper_bgcolor=CHART_PAPER_BG,plot_bgcolor=CHART_PLOT_BG,
                          font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),height=380,margin=dict(l=60,r=20,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Renewable Energy Capacity FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor=CHART_GRID),yaxis=dict(gridcolor=CHART_GRID,ticksuffix=" GW"))
        st.plotly_chart(fig, width='stretch')

    with t2:
        for co, d in company_data.items():
            vals=[d[y] for y in years]; gr=round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {d['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{co}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{d['sector']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  {"".join([f'<div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">{y}</div><div style="font-size:0.78rem;font-weight:700;color:{TEXT};">₹{d[y]:,}</div></div>' for y in years])}
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">GROWTH</div><div style="font-size:0.78rem;font-weight:700;color:{GREEN};">+{gr}%</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};margin-top:6px;">💡 {d['about']}</div>
            </div>""", unsafe_allow_html=True)

    with t3:
        reactions = [
            {"stock":"JAINREC",   "event":"Solar Mission FY26","1d":"+7.2%","1w":"+13.8%","1m":"+29.4%","trigger":"PM Solar Mission 300 GW target. JAINREC EPC orders surge.","color":SOLAR},
            {"stock":"ADANIGREEN","event":"RE Budget Hike FY24","1d":"+9.1%","1w":"+17.2%","1m":"+38.6%","trigger":"Budget mein ₹35,000 Cr renewable allocation. Adani Green record high.","color":GREEN},
            {"stock":"NTPC",      "event":"Green NTPC Demerger","1d":"+5.4%","1w":"+10.2%","1m":"+19.8%","trigger":"NTPC Renewable Energy demerger plans. Unlocking green value.","color":WIND},
            {"stock":"SJVN",      "event":"Hydro Policy FY25","1d":"+6.8%","1w":"+12.4%","1m":"+24.7%","trigger":"Govt ne hydro ko renewable status diya. SJVN mega projects cleared.","color":HYDRO},
            {"stock":"BOROSIL",   "event":"PLI Solar Glass","1d":"+11.3%","1w":"+21.6%","1m":"+45.2%","trigger":"PLI scheme mein solar glass included. Borosil only beneficiary.","color":PURPLE},
        ]
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};letter-spacing:.1em;margin-bottom:12px;">📊 POLICY ANNOUNCEMENT PE STOCK REACTION</div>', unsafe_allow_html=True)
        for r in reactions:
            d1c=GREEN if "+" in r["1d"] else RED; d7c=GREEN if "+" in r["1w"] else RED; d30c=GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {r['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{r['stock']}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{r['event']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 DAY</div><div style="font-size:0.82rem;font-weight:800;color:{d1c};">{r['1d']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 WEEK</div><div style="font-size:0.82rem;font-weight:800;color:{d7c};">{r['1w']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 MONTH</div><div style="font-size:0.82rem;font-weight:800;color:{d30c};">{r['1m']}</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};">🎯 <span style="color:{r['color']};">{r['trigger']}</span></div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB — EV & AUTO TECH
# ══════════════════════════════════════════════════════════════════════════════
if tab == "ev_tech":
    import plotly.graph_objects as go

    ELEC   = "#22d3ee"; AUTO="#a3e635"; SOFT="#f472b6"
    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, GREEN, RED, BLUE
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    _eh, _er = st.columns([5,1])
    with _eh:
        st.markdown('<div class="sec-title">EV & AUTO TECH</div>', unsafe_allow_html=True)
    with _er:
        if st.button("🔄", key="ev_refresh", help="Refresh karo"):
            get_index_quote.clear(); get_batch_quotes.clear(); st.rerun()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a1520,#0f1a0a);
                border:1px solid #22d3ee55;border-radius:16px;padding:18px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.2rem;">⚡</div>
        <div>
          <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">
            India EV & Auto Tech Sector Tracker
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
            FY22–FY26 EV sales trend · Company-wise revenue · Stock impact analysis
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    ev_data = {
        "FY22": {"ev_sales_lakh":4.3,  "2w_lakh":2.3,  "4w_lakh":0.18, "budget_cr":2908},
        "FY23": {"ev_sales_lakh":10.2, "2w_lakh":6.8,  "4w_lakh":0.48, "budget_cr":5172},
        "FY24": {"ev_sales_lakh":16.8, "2w_lakh":10.9, "4w_lakh":0.90, "budget_cr":10000},
        "FY25": {"ev_sales_lakh":24.5, "2w_lakh":16.2, "4w_lakh":1.40, "budget_cr":16000},
        "FY26": {"ev_sales_lakh":35.0, "2w_lakh":23.0, "4w_lakh":2.10, "budget_cr":20000},
    }

    company_data_ev = {
        "KPITTECH":  {"FY22":900,  "FY23":1350, "FY24":1900, "FY25":2600, "FY26":3400,
                      "color":ELEC,"sector":"EV Software / Embedded","ticker":"KPITTECH.NS",
                      "about":"EV powertrain software, AUTOSAR, SDV. BMW, Renault, Cummins clients."},
        "TMPV":{"FY22":68000,"FY23":84000,"FY24":105000,"FY25":125000,"FY26":145000,
                      "color":AUTO,"sector":"EV OEM","ticker":"TMPV.NS",
                      "about":"Tata Nexon EV India ka bestseller. JLR turnaround. 14+ EV models pipeline."},
        "MOTHERSON": {"FY22":58000,"FY23":63000,"FY24":71000,"FY25":80000,"FY26":91000,
                      "color":SOFT,"sector":"Auto Components","ticker":"MOTHERSON.NS",
                      "about":"Global auto component giant. EV wiring harness, sensors, vision systems."},
        "MINDA":     {"FY22":8200, "FY23":9800, "FY24":11500,"FY25":13500,"FY26":16000,
                      "color":PURPLE,"sector":"EV Components","ticker":"MINDACORP.NS",
                      "about":"Switches, sensors, alloy wheels, EV charging controllers."},
        "EXIDEIND":  {"FY22":11200,"FY23":12800,"FY24":14500,"FY25":16500,"FY26":19000,
                      "color":"#fb923c","sector":"EV Batteries","ticker":"EXIDEIND.NS",
                      "about":"Li-ion battery cell manufacturing plant. EV battery pack leader."},
    }

    years = ["FY22","FY23","FY24","FY25","FY26"]
    t1, t2, t3 = st.tabs(["📈 Sector Trend", "🏭 Company Tracker", "📊 Stock Impact"])

    with t1:
        fy26=ev_data["FY26"]; fy22=ev_data["FY22"]
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;">
          <div style="background:{CARD_BG};border:1px solid {ELEC}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {ELEC};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 EV SALES</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['ev_sales_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['ev_sales_lakh']-fy22['ev_sales_lakh'])/fy22['ev_sales_lakh']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {AUTO}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {AUTO};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">2-WHEELER EV</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['2w_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{MUTED};">Ola, TVS, Bajaj</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SOFT}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {SOFT};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">4-WHEELER EV</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['4w_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{MUTED};">Tata, MG, Hyundai</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {PURPLE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FAME-3 BUDGET</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['budget_cr']//1000}K Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">EV subsidy scheme</div>
          </div>
        </div>""", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="2-Wheeler EV",x=years,y=[ev_data[y]["2w_lakh"] for y in years],marker_color=AUTO))
        fig.add_trace(go.Bar(name="4-Wheeler EV",x=years,y=[ev_data[y]["4w_lakh"] for y in years],marker_color=SOFT))
        fig.add_trace(go.Scatter(name="Total EV Sales",x=years,y=[ev_data[y]["ev_sales_lakh"] for y in years],
                                  mode="lines+markers+text",line=dict(color=ELEC,width=2.5),marker=dict(size=9),
                                  text=[f"{v}L" for v in [ev_data[y]["ev_sales_lakh"] for y in years]],
                                  textposition="top center",textfont=dict(size=10,color=ELEC)))
        fig.update_layout(barmode="stack",paper_bgcolor=CHART_PAPER_BG,plot_bgcolor=CHART_PLOT_BG,
                          font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),height=380,margin=dict(l=60,r=20,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India EV Sales FY22–FY26 (Lakh Units)",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor=CHART_GRID),yaxis=dict(gridcolor=CHART_GRID))
        st.plotly_chart(fig, width='stretch', key="ev_sector_trend_chart")

        # Insight boxes — Defence jaisa
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            st.markdown(f"""<div style="background:{CARD_BG};border:1px solid {GREEN}44;border-left:3px solid {GREEN};
                        border-radius:10px;padding:14px;">
              <div style="font-size:0.82rem;font-weight:800;color:{GREEN};">🎯 FAME-3 Scheme</div>
              <div style="font-size:0.76rem;color:{MUTED};margin-top:6px;">₹20K Cr subsidy budget FY26 — 2W aur 4W EV adoption ko boost karne ke liye Make in India push ke saath.</div>
            </div>""", unsafe_allow_html=True)
        with ic2:
            st.markdown(f"""<div style="background:{CARD_BG};border:1px solid {ELEC}44;border-left:3px solid {ELEC};
                        border-radius:10px;padding:14px;">
              <div style="font-size:0.82rem;font-weight:800;color:{ELEC};">🔋 2-Wheeler Dominance</div>
              <div style="font-size:0.76rem;color:{MUTED};margin-top:6px;">EV sales mein 2-wheelers ka 65%+ share — Ola, TVS, Bajaj jaise players retail demand drive kar rahe.</div>
            </div>""", unsafe_allow_html=True)
        with ic3:
            st.markdown(f"""<div style="background:{CARD_BG};border:1px solid {SOFT}44;border-left:3px solid {SOFT};
                        border-radius:10px;padding:14px;">
              <div style="font-size:0.82rem;font-weight:800;color:{SOFT};">🚗 4-Wheeler Growth</div>
              <div style="font-size:0.76rem;color:{MUTED};margin-top:6px;">Tata, MG, Hyundai EV models se 4W segment FY22 se 11x grow hua — luxury se mass-market shift.</div>
            </div>""", unsafe_allow_html=True)

    with t2:
        for co, d in company_data_ev.items():
            vals=[d[y] for y in years]; gr=round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {d['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{co}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{d['sector']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  {"".join([f'<div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">{y}</div><div style="font-size:0.78rem;font-weight:700;color:{TEXT};">₹{d[y]:,}</div></div>' for y in years])}
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">GROWTH</div><div style="font-size:0.78rem;font-weight:700;color:{GREEN};">+{gr}%</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};margin-top:6px;">💡 {d['about']}</div>
            </div>""", unsafe_allow_html=True)

        # Live price strip for your watchlist stock
        st.markdown("<br>", unsafe_allow_html=True)
        _kq = get_index_quote("KPITTECH.NS")
        if _kq:
            _kc, _kp, _kchg, _kpct = _kq
            _kclr = GREEN if _kchg >= 0 else RED
            _karr = "▲" if _kchg >= 0 else "▼"
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {ELEC}44;border-radius:10px;
                        padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <span style="font-size:0.7rem;color:{MUTED};font-weight:700;">YOUR WATCHLIST STOCK</span>
                <span style="font-size:0.9rem;font-weight:800;color:{TEXT};margin-left:8px;">KPIT Technologies</span>
              </div>
              <div style="text-align:right;">
                <span style="font-size:1.1rem;font-weight:900;color:{TEXT};">₹{_kc:,.2f}</span>
                <span style="color:{_kclr};font-size:0.8rem;font-weight:700;margin-left:8px;">{_karr} {abs(_kpct):.2f}%</span>
              </div>
            </div>""", unsafe_allow_html=True)

    with t3:
        reactions = [
            {"stock":"KPITTECH",   "event":"FAME-3 Budget FY26","1d":"+8.4%","1w":"+15.6%","1m":"+32.1%","trigger":"EV software demand boom. KPIT ke global auto client revenue 2x.","color":ELEC},
            {"stock":"TMPV", "event":"Nexon EV 1L deliveries","1d":"+6.2%","1w":"+11.4%","1m":"+22.8%","trigger":"Tata Nexon EV ne 1 lakh deliveries complete ki. Market share 65%.","color":AUTO},
            {"stock":"MINDA",      "event":"EV Component PLI","1d":"+9.8%","1w":"+18.2%","1m":"+38.4%","trigger":"PLI scheme auto components. Minda EV switch + sensor orders 3x.","color":PURPLE},
            {"stock":"EXIDEIND",   "event":"Li-ion Plant Commencement","1d":"+12.1%","1w":"+22.4%","1m":"+48.6%","trigger":"Exide Li-ion battery plant Bangalore. India first indigenous cell mfg.","color":"#fb923c"},
            {"stock":"MOTHERSON",  "event":"EV Wiring Contracts","1d":"+5.1%","1w":"+9.8%","1m":"+18.9%","trigger":"BMW, Stellantis EV wiring harness orders. ₹8,000 Cr contract.","color":SOFT},
        ]
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};letter-spacing:.1em;margin-bottom:12px;">📊 EV POLICY & NEWS PE STOCK REACTION</div>', unsafe_allow_html=True)
        for r in reactions:
            d1c=GREEN if "+" in r["1d"] else RED; d7c=GREEN if "+" in r["1w"] else RED; d30c=GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {r['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{r['stock']}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{r['event']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 DAY</div><div style="font-size:0.82rem;font-weight:800;color:{d1c};">{r['1d']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 WEEK</div><div style="font-size:0.82rem;font-weight:800;color:{d7c};">{r['1w']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 MONTH</div><div style="font-size:0.82rem;font-weight:800;color:{d30c};">{r['1m']}</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};">🎯 <span style="color:{r['color']};">{r['trigger']}</span></div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB — BANKING & NBFC
# ══════════════════════════════════════════════════════════════════════════════
if tab == "banking":
    import plotly.graph_objects as go

    BANKBLUE="#2563eb"; NBFC="#7c3aed"; NPA="#ef4444"
    # Using global theme variables for CARD_BG, BORDER, TEXT, MUTED, GREEN, RED, BLUE
    PURPLE = "#a78bfa" if st.session_state.dark_mode else "#8B5CF6"

    _bnkh, _bnkr = st.columns([5,1])
    with _bnkh:
        st.markdown('<div class="sec-title">BANKING & NBFC</div>', unsafe_allow_html=True)
    with _bnkr:
        if st.button("🔄", key="banking_refresh", help="Refresh karo"):
            get_index_quote.clear(); get_batch_quotes.clear(); st.rerun()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a1020,#0f0a20);
                border:1px solid #2563eb55;border-radius:16px;padding:18px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.2rem;">🏧</div>
        <div>
          <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">
            India Banking & NBFC Sector Tracker
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;margin-top:3px;">
            FY22–FY26 credit growth trend · Company-wise metrics · Stock impact analysis
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    banking_data = {
        "FY22": {"credit_lakh_cr":115, "npa_pct":5.9, "roe_pct":8.2,  "casa_pct":45.2},
        "FY23": {"credit_lakh_cr":136, "npa_pct":3.9, "roe_pct":11.8, "casa_pct":44.1},
        "FY24": {"credit_lakh_cr":159, "npa_pct":2.8, "roe_pct":14.2, "casa_pct":42.8},
        "FY25": {"credit_lakh_cr":182, "npa_pct":2.4, "roe_pct":15.6, "casa_pct":41.5},
        "FY26": {"credit_lakh_cr":210, "npa_pct":2.1, "roe_pct":16.8, "casa_pct":40.8},
    }

    company_data = {
        "HDFCBANK":    {"FY22":154000,"FY23":185000,"FY24":215000,"FY25":245000,"FY26":278000,
                        "color":BANKBLUE,"sector":"Private Bank","ticker":"HDFCBANK.NS",
                        "about":"India ka #1 private bank. Merger with HDFC complete. 8,000+ branches."},
        "ICICIBANK":   {"FY22":98000, "FY23":128000,"FY24":158000,"FY25":188000,"FY26":218000,
                        "color":"#06b6d4","sector":"Private Bank","ticker":"ICICIBANK.NS",
                        "about":"Digital banking leader. iMobile 14M+ users. ROE 18%+ consistently."},
        "SBIN":        {"FY22":178000,"FY23":205000,"FY24":235000,"FY25":265000,"FY26":298000,
                        "color":GREEN,"sector":"PSU Bank","ticker":"SBIN.NS",
                        "about":"India ka sabse bada bank. 22,000+ branches. Jan Dhan backbone."},
        "BAJFINANCE":  {"FY22":38000, "FY23":48000, "FY24":62000, "FY25":78000, "FY26":95000,
                        "color":NBFC,"sector":"NBFC","ticker":"BAJFINANCE.NS",
                        "about":"India ka #1 NBFC. Consumer loans, EMI cards, fixed deposits. Pan-India."},
        "KOTAKBANK":   {"FY22":68000, "FY23":82000, "FY24":98000, "FY25":112000,"FY26":128000,
                        "color":"#f59e0b","sector":"Private Bank","ticker":"KOTAKBANK.NS",
                        "about":"High-quality loan book. 811 digital bank pioneer. NIM consistently high."},
    }

    years = ["FY22","FY23","FY24","FY25","FY26"]
    t1, t2, t3 = st.tabs(["📈 Credit Growth", "🏭 Company Metrics", "📊 Stock Impact"])

    with t1:
        fy26=banking_data["FY26"]; fy22=banking_data["FY22"]
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;">
          <div style="background:{CARD_BG};border:1px solid {BANKBLUE}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {BANKBLUE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 CREDIT OUTSTANDING</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['credit_lakh_cr']}L Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['credit_lakh_cr']-fy22['credit_lakh_cr'])/fy22['credit_lakh_cr']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {NPA}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {NPA};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">GROSS NPA</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['npa_pct']}%</div>
            <div style="font-size:0.72rem;color:{GREEN};">From {fy22['npa_pct']}% in FY22 ↓</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {GREEN}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {GREEN};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">SECTOR ROE</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['roe_pct']}%</div>
            <div style="font-size:0.72rem;color:{GREEN};">Best in a decade</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {NBFC}44;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {NBFC};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">CASA RATIO</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['casa_pct']}%</div>
            <div style="font-size:0.72rem;color:{MUTED};">Low cost deposits</div>
          </div>
        </div>""", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Credit Outstanding (₹L Cr)",x=years,
                             y=[banking_data[y]["credit_lakh_cr"] for y in years],marker_color=BANKBLUE,
                             text=[f"₹{v}L Cr" for v in [banking_data[y]["credit_lakh_cr"] for y in years]],
                             textposition="inside",textfont=dict(size=10,color="#fff")))
        fig.add_trace(go.Scatter(name="NPA %",x=years,y=[banking_data[y]["npa_pct"] for y in years],
                                  mode="lines+markers+text",line=dict(color=NPA,width=2.5,dash="dot"),
                                  marker=dict(size=9),yaxis="y2",
                                  text=[f"{v}%" for v in [banking_data[y]["npa_pct"] for y in years]],
                                  textposition="top center",textfont=dict(size=10,color=NPA)))
        fig.update_layout(paper_bgcolor=CHART_PAPER_BG,plot_bgcolor=CHART_PLOT_BG,
                          font=dict(color=TEXT, size=11, family="Outfit, Inter, sans-serif" if not st.session_state.dark_mode else "Inter, sans-serif"),height=380,margin=dict(l=60,r=60,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Banking Credit Growth & NPA FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor=CHART_GRID),
                          yaxis=dict(gridcolor=CHART_GRID,tickprefix="₹",title="Credit (₹L Cr)"),
                          yaxis2=dict(overlaying="y",side="right",title="NPA %",ticksuffix="%",showgrid=False))
        st.plotly_chart(fig, width='stretch')

    with t2:
        for co, d in company_data.items():
            vals=[d[y] for y in years]; gr=round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {d['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{co}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{d['sector']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  {"".join([f'<div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">{y}</div><div style="font-size:0.78rem;font-weight:700;color:{TEXT};">₹{d[y]//1000:,}K</div></div>' for y in years])}
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">GROWTH</div><div style="font-size:0.78rem;font-weight:700;color:{GREEN};">+{gr}%</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};margin-top:6px;">💡 {d['about']}</div>
            </div>""", unsafe_allow_html=True)

    with t3:
        reactions = [
            {"stock":"HDFCBANK",  "event":"HDFC Merger FY24","1d":"+5.2%","1w":"+9.8%","1m":"+18.4%","trigger":"HDFC + HDFC Bank merger complete. Balance sheet ₹35L Cr+. Re-rating.","color":BANKBLUE},
            {"stock":"ICICIBANK", "event":"RBI Rate Cut Signal","1d":"+4.8%","1w":"+8.9%","1m":"+16.2%","trigger":"Rate cut cycle start. NIM compression fear gone. ICICI outperforms.","color":"#06b6d4"},
            {"stock":"SBIN",      "event":"Budget PSU Bank Recap","1d":"+6.4%","1w":"+12.1%","1m":"+24.8%","trigger":"₹15,000 Cr PSU bank recap in budget. SBI biggest beneficiary.","color":GREEN},
            {"stock":"BAJFINANCE","event":"RBI Rate Cut -50bps","1d":"+7.8%","1w":"+14.6%","1m":"+31.2%","trigger":"Rate cut se NBFC cost of funds down. Bajaj Finance NIM expansion.","color":NBFC},
            {"stock":"KOTAKBANK", "event":"811 Digital Milestone","1d":"+3.9%","1w":"+7.4%","1m":"+14.8%","trigger":"Kotak 811 ne 2 Cr accounts. Digital cost ratio best-in-class.","color":"#f59e0b"},
        ]
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};letter-spacing:.1em;margin-bottom:12px;">📊 RBI POLICY & BUDGET PE STOCK REACTION</div>', unsafe_allow_html=True)
        for r in reactions:
            d1c=GREEN if "+" in r["1d"] else RED; d7c=GREEN if "+" in r["1w"] else RED; d30c=GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:12px;
                        padding:13px 16px;margin-bottom:8px;border-left:4px solid {r['color']};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                <div>
                  <span style="font-size:0.95rem;font-weight:800;color:{TEXT};">{r['stock']}</span>
                  <span style="font-size:0.7rem;color:{MUTED};margin-left:8px;">{r['event']}</span>
                </div>
                <div style="display:flex;gap:10px;">
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 DAY</div><div style="font-size:0.82rem;font-weight:800;color:{d1c};">{r['1d']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 WEEK</div><div style="font-size:0.82rem;font-weight:800;color:{d7c};">{r['1w']}</div></div>
                  <div style="text-align:center;"><div style="font-size:0.58rem;color:{MUTED};">1 MONTH</div><div style="font-size:0.82rem;font-weight:800;color:{d30c};">{r['1m']}</div></div>
                </div>
              </div>
              <div style="font-size:0.72rem;color:{MUTED};">🎯 <span style="color:{r['color']};">{r['trigger']}</span></div>
            </div>""", unsafe_allow_html=True)

