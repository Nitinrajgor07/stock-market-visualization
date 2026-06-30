import os
import time
import json
import base64
import requests
import pytz
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta

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
# 🎨 DESIGN SYSTEM — Zerodha Kite-style: minimal, sharp, professional.
# Single source of truth for font, colors, spacing, and native Streamlit
# widget styling. Loaded once, very early, so it applies everywhere.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
--kt-bg:        #0f1116;
--kt-card:      #1a1d27;
--kt-card-alt:  #1e2130;
--kt-border:    #262a38;
--kt-text:      #e8eaf0;
--kt-muted:     #8b90a0;
--kt-blue:      #387ed1;
--kt-green:     #2cb96a;
--kt-red:       #e6483f;
--kt-radius-sm: 6px;
--kt-radius-md: 8px;
--kt-radius-lg: 10px;
--kt-space-1: 4px;  --kt-space-2: 8px;  --kt-space-3: 12px;
--kt-space-4: 16px; --kt-space-5: 24px;
}

/* Kite jaisa minimal sans-serif everywhere, including Streamlit's own DOM */
html, body, [class*="css"], button, input, select, textarea {
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
h1, h2, h3, h4, h5, h6 { font-weight: 700 !important; letter-spacing: -0.01em; }

/* ── Streamlit BUTTONS — sharp, minimal, no heavy rounding/shadow ──────────── */
div[data-testid="stButton"] button,
div[data-testid="stFormSubmitButton"] button {
border-radius: var(--kt-radius-sm) !important;
border: 1px solid var(--kt-border) !important;
background: var(--kt-card) !important;
color: var(--kt-text) !important;
font-weight: 600 !important;
font-size: 0.85rem !important;
box-shadow: none !important;
transition: border-color .15s ease, background .15s ease;
}
div[data-testid="stButton"] button:hover {
border-color: var(--kt-blue) !important;
background: var(--kt-card-alt) !important;
color: var(--kt-text) !important;
}
div[data-testid="stButton"] button[kind="primary"] {
background: var(--kt-blue) !important;
border-color: var(--kt-blue) !important;
color: #ffffff !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover { filter: brightness(1.08); }

/* ── TABS — underline style, Kite jaisa, no big rounded pill chrome ────────── */
div[data-testid="stTabs"] button[role="tab"] {
font-family: 'Inter', sans-serif !important;
font-weight: 600 !important;
font-size: 0.85rem !important;
color: var(--kt-muted) !important;
background: transparent !important;
border: none !important;
border-bottom: 2px solid transparent !important;
padding: 8px 14px !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
color: var(--kt-blue) !important;
border-bottom: 2px solid var(--kt-blue) !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: transparent !important; }
div[data-testid="stTabs"] [data-baseweb="tab-border"] { background: var(--kt-border) !important; }

/* ── EXPANDER — flat card, matches app cards instead of default chrome ────── */
div[data-testid="stExpander"] {
border: 1px solid var(--kt-border) !important;
border-radius: var(--kt-radius-md) !important;
background: var(--kt-card) !important;
}
div[data-testid="stExpander"] summary {
color: var(--kt-text) !important;
font-weight: 600 !important;
font-size: 0.85rem !important;
}

/* ── METRIC — tighten up Streamlit's oversized default metric styling ─────── */
div[data-testid="stMetric"] {
background: var(--kt-card) !important;
border: 1px solid var(--kt-border) !important;
border-radius: var(--kt-radius-md) !important;
padding: 12px 14px !important;
}
div[data-testid="stMetricLabel"] {
font-size: 0.68rem !important; color: var(--kt-muted) !important;
font-weight: 600 !important; letter-spacing: 0.05em !important;
text-transform: uppercase !important;
}
div[data-testid="stMetricValue"] {
font-size: 1.25rem !important; font-weight: 800 !important; color: var(--kt-text) !important;
}

/* ── SELECTBOX / RADIO / CHECKBOX / TEXT INPUT — match dark theme ─────────── */
div[data-testid="stSelectbox"] > div,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {
background: var(--kt-card) !important;
border: 1px solid var(--kt-border) !important;
border-radius: var(--kt-radius-sm) !important;
color: var(--kt-text) !important;
}
div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label {
color: var(--kt-text) !important; font-size: 0.85rem !important;
}

/* ── Subtle, consistent card elevation app-wide (Kite uses very flat, ──────── */
/* ── faint shadows — not glossy) ───────────────────────────────────────────── */
.port-card, .kpi-card, .order-card, .topbar, div[data-testid="stExpander"] {
box-shadow: 0 1px 2px rgba(0,0,0,0.25) !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: var(--kt-border); border-radius: 2px; }

/* ── BUY / SELL action buttons — solid green/red, Kite jaisa, no emoji ────── */
[class*="st-key-buybtn_"] button, [class*="st-key-execbuybtn"] button {
background: var(--kt-green) !important;
border-color: var(--kt-green) !important;
color: #ffffff !important;
}
[class*="st-key-buybtn_"] button:hover, [class*="st-key-execbuybtn"] button:hover { filter: brightness(1.08); }
[class*="st-key-sellbtn_"] button, [class*="st-key-execsellbtn"] button {
background: var(--kt-red) !important;
border-color: var(--kt-red) !important;
color: #ffffff !important;
}
[class*="st-key-sellbtn_"] button:hover, [class*="st-key-execsellbtn"] button:hover { filter: brightness(1.08); }

/* ── SPACING AUDIT — consistent vertical rhythm app-wide ───────────────────── */
/* Streamlit ka default gap between stacked elements (st.markdown/columns/   */
/* widgets) was inconsistent across sections (kabhi 0, kabhi 2rem). Yeh sab  */
/* ek consistent rhythm pe le aata hai, har element-block ke beech same gap. */
div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
margin-bottom: var(--kt-space-3) !important;
}
div[data-testid="stHorizontalBlock"] {
gap: var(--kt-space-3) !important;
}
.block-container {
padding-left: var(--kt-space-4) !important;
padding-right: var(--kt-space-4) !important;
}
/* Section titles already have their own padding — avoid double-spacing */
.sec-title { margin-top: var(--kt-space-2) !important; margin-bottom: 0 !important; }
/* Cards inside the same group should sit closer together than two different */
/* sections — tightens the "everything floating randomly" feel.            */
.port-card, .kpi-card, .order-card { margin: var(--kt-space-2) 0 !important; }
</style>
""", unsafe_allow_html=True)


# BUG FIX: pehle st.markdown() ke andar <script> tag daala tha — lekin browsers
# st.markdown/innerHTML se inserted <script> tags ko EXECUTE nahi karte (yeh
# standard browser/React behavior hai, Streamlit-specific nahi). Isliye PWA
# install option kabhi dikha hi nahi — JS kabhi chala hi nahi tha.
#
# FIX: components.html() use karo — wo iframe ke andar real <script> tag
# render karta hai jo ACTUALLY chalta hai. Iframe se parent page ke <head> tak
# pahunchne ke liye window.parent.document use kar rahe hain (same-origin hai,
# isliye cross-origin issue nahi aayega).
#
# ZAROORI: Ye kaam karega ONLY agar:
#   1. .streamlit/config.toml mein [server] enableStaticServing = true ho
#   2. static/manifest.json, static/sw.js, static/icon-192.png,
#      static/icon-512.png — ye 4 files repo ke root mein "static/" folder mein ho
components.html("""
<script>
(function() {
    try {
        var pDoc = window.parent.document;
        var pWin = window.parent;

        // 1. Manifest link
        if (!pDoc.querySelector('link[rel="manifest"]')) {
            var link = pDoc.createElement('link');
            link.rel = 'manifest';
            link.href = '/app/static/manifest.json';
            pDoc.head.appendChild(link);
        }
        // 2. Theme color (status bar / browser chrome color match)
        if (!pDoc.querySelector('meta[name="theme-color"]')) {
            var meta = pDoc.createElement('meta');
            meta.name = 'theme-color';
            meta.content = '#0d1117';
            pDoc.head.appendChild(meta);
        }
        // 3. iOS-specific tags — Safari manifest.json ko poora support nahi
        // karta, isliye Apple ke apne meta tags bhi chahiye "Add to Home Screen" ke liye
        if (!pDoc.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
            var appleCapable = pDoc.createElement('meta');
            appleCapable.name = 'apple-mobile-web-app-capable';
            appleCapable.content = 'yes';
            pDoc.head.appendChild(appleCapable);

            var appleStatusBar = pDoc.createElement('meta');
            appleStatusBar.name = 'apple-mobile-web-app-status-bar-style';
            appleStatusBar.content = 'black-translucent';
            pDoc.head.appendChild(appleStatusBar);

            var appleTitle = pDoc.createElement('meta');
            appleTitle.name = 'apple-mobile-web-app-title';
            appleTitle.content = 'Markets';
            pDoc.head.appendChild(appleTitle);

            var appleIcon = pDoc.createElement('link');
            appleIcon.rel = 'apple-touch-icon';
            appleIcon.href = '/app/static/icon-192.png';
            pDoc.head.appendChild(appleIcon);
        }

        // 4. Service worker register — PARENT window ke context mein register
        // karna zaroori hai (iframe ke context mein nahi), warna scope galat
        // page se bind ho jaata hai aur installability criteria pura nahi hota.
        if ('serviceWorker' in pWin.navigator) {
            pWin.navigator.serviceWorker.register('/app/static/sw.js').catch(function(err) {
                console.log('SW registration skipped:', err);
            });
        }
    } catch (e) {
        console.log('PWA setup skipped:', e);
    }
})();
</script>
""", height=0, width=0)

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
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark" 

if not st.session_state.authenticated:
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main {
        background: #080b14 !important;
    }
    [data-testid="stHeader"] { display:none !important; }
    footer                   { display:none !important; }
    #MainMenu                { display:none !important; }
    .block-container         { padding-top:0 !important; max-width:100% !important; }

    /* Kill label + all its wrappers = no box above input */
    [data-testid="stTextInput"] label { display:none !important; }
    [data-testid="stTextInput"] > div:first-child { display:none !important; }
    [data-testid="stTextInput"] > div:first-child * { display:none !important; }

    /* Input field */
    [data-testid="stTextInput"] input {
        background: #12151f !important;
        color: #e8eaf0 !important;
        border: 1.5px solid #252840 !important;
        border-radius:10px !important;
        font-size: 1rem !important;
        padding: 13px 16px !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #5b8dee !important;
        box-shadow: 0 0 0 3px rgba(91,141,238,0.15) !important;
        outline: none !important;
    }

    /* Login button */
    [data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg,#5b8dee,#3a6fd8) !important;
        color:#fff !important; border:none !important;
        border-radius:10px !important; font-size:1rem !important;
        font-weight:700 !important; padding:13px 0 !important;
        box-shadow:0 6px 24px rgba(91,141,238,0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center;margin-bottom:24px;">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:72px;height:72px;border-radius:20px;
                      background:linear-gradient(145deg,#1c2d50,#0d1626);
                      border:1px solid #2a3d60;
                      box-shadow:0 8px 32px rgba(91,141,238,0.22);
                      font-size:2rem;margin-bottom:12px;">📈</div>
          <div style="font-size:1.75rem;font-weight:900;color:#f0f3ff;letter-spacing:-0.02em;">
            Market Dashboard
          </div>
          <div style="font-size:0.83rem;color:#3d4460;margin-top:6px;">
            Apna password daalo aage badhne ke liye
          </div>
        </div>
        <div style="background:rgba(14,17,28,0.97);border:1px solid #1c2040;
                    border-radius:20px;padding:22px 20px 20px;
                    box-shadow:0 20px 60px rgba(0,0,0,0.7);">
        </div>
        """, unsafe_allow_html=True)

        pwd_input = st.text_input(
            "p", type="password",
            placeholder="Password daalo...",
            label_visibility="collapsed",
            key="pwd_field",
            value="",
        )

        # Clear autofill + kill autocomplete
        st.markdown("""
        <script>
        (function() {
            var n = 0;
            var iv = setInterval(function() {
                var el = document.querySelector('input[type="password"]');
                if (el) {
                    el.value = '';
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.setAttribute('autocomplete', 'off');
                    el.setAttribute('name', 'pwd_' + Math.random());
                    clearInterval(iv);
                }
                if (++n > 30) clearInterval(iv);
            }, 100);
        })();
        </script>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        login_btn = st.button("🔓  Login karo", use_container_width=True,
                              type="primary", key="login_btn")

        if login_btn:
            if check_password(pwd_input, CORRECT_HASH):
                st.session_state.authenticated = True
                st.session_state.login_failed = False
                st.rerun()
            else:
                st.session_state.login_failed = True
                st.rerun()

        if st.session_state.get("login_failed"):
            st.markdown("""
            <div style="background:#1c0808;border:1px solid rgba(231,76,60,0.38);
                        border-radius:10px;padding:10px 14px;margin-top:10px;
                        display:flex;align-items:center;gap:8px;">
              <span>❌</span>
              <span style="color:#e05c4b;font-size:0.87rem;font-weight:600;">
                Galat password! Dobara try karo.
              </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:0.69rem;color:#1e2235;">
          🔒 Sirf authorized users ke liye
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ── IST / market helpers ───────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)


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

# ── CSS — Zerodha dark style ───────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stSidebar"],
[data-testid="stMain"], section.main {
    background-color: #0f1116 !important;
    color: #e8eaf0 !important;
}
/* ── Safety net: kabhi bhi koi element poori app ko sideways scroll na kar ── */
/* ── paaye (phone par yahi sabse zyada layout todta hai). Andar ke widgets ── */
/* ── jinhe horizontal scroll chahiye (ticker, chips) apna khud ka overflow-x: ── */
/* ── auto rakhte hain, woh isse affected nahi honge. ──────────────────────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container {
    overflow-x: hidden !important;
    max-width: 100vw !important;
}
/* Hide default Streamlit header/footer/sidebar toggle */
[data-testid="stHeader"]          { display:none !important; }
[data-testid="collapsedControl"]  { display:none !important; }
footer                            { display:none !important; }
#MainMenu                         { display:none !important; }

/* Remove default top padding */
.block-container { padding-top: 0px !important; padding-bottom: 80px !important; }

/* ── TOP BAR ── */
.topbar {
    position: sticky; top: 36px; z-index: 999;
    background: #1a1d27;
    border-bottom: 1px solid #2a2d3a;
    padding: 10px 0 10px 20px;
    display: flex; align-items: center; justify-content: space-between;
    max-width: 100%;
    overflow: hidden;
}
.topbar-left {
    display:flex; align-items:center; gap:14px;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    scrollbar-width: none;
    padding-right: 12px;
}
.topbar-left::-webkit-scrollbar { display:none; }
.topbar-title { flex: 0 0 auto; }
.topbar-title { font-size:1rem; font-weight:700; color:#e8eaf0; }
.index-chip {
    display:inline-flex; flex-direction:column; flex:0 0 auto;
    background: #22253a; border-radius:8px;
    padding: 4px 14px; cursor:pointer;
}
.index-chip .ic-name  { font-size:0.68rem; color:#8b90a0; }
.index-chip .ic-val   { font-size:0.92rem; font-weight:700; color:#e8eaf0; }
.index-chip .ic-chg-g { font-size:0.72rem; color:#27ae60; font-weight:600; }
.index-chip .ic-chg-r { font-size:0.72rem; color:#e74c3c; font-weight:600; }

.live-dot {
    display:inline-block; width:8px; height:8px;
    background:#27ae60; border-radius:50%; margin-right:6px;
    animation: blink 1.2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.closed-dot {
    display:inline-block; width:8px; height:8px;
    background:#e74c3c; border-radius:50%; margin-right:6px;
}
.status-text { font-size:0.72rem; color:#8b90a0; }

/* ── 📱 MOBILE RESPONSIVE FIX — Holdings table phone pe stacked card ──────── */
/* ── ban jaaye, desktop wala 8-column grid waisa hi rahe (untouched). ─────── */
@media (max-width: 640px) {
  .holdings-grid {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  .holdings-header { display: none !important; }  /* header row redundant ho jaata hai, har value ka apna label hai */
  .holdings-grid > div { width: 100% !important; text-align: left !important; }
  .holdings-grid > div.hg-half { width: calc(50% - 4px) !important; }
  .holdings-grid > div.hg-full-pnl { width: 100% !important; }
  .holdings-grid > div[data-label]::before {
    content: attr(data-label);
    display: block;
    font-size: 0.6rem;
    color: #8b90a0;
    letter-spacing: 0.05em;
    margin-bottom: 3px;
  }
}

.countdown-badge {
    font-size:0.7rem; font-weight:700; padding:3px 10px;
    border:1px solid; border-radius:20px; background:#22253a;
    white-space:nowrap;
}
.countdown-urgent { animation: countdown-pulse 1.1s infinite; }
@keyframes countdown-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }

/* ── LIVE SCROLLING TICKER — news channel jaisa, page ke bilkul upar ── */
.ticker-wrap {
    position: sticky; top: 0; z-index: 1001;
    background: #0d0f17;
    border-bottom: 1px solid #2a2d3a;
    overflow: hidden;
    white-space: nowrap;
    padding: 7px 0;
}
.ticker-track {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 35s linear infinite;
}
.ticker-wrap:hover .ticker-track {
    animation-play-state: paused;
}
@keyframes ticker-scroll {
    0%   { transform: translateX(0%); }
    100% { transform: translateX(-50%); }
}
.ticker-item {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 0 28px;
    font-size: 0.82rem; font-weight: 600;
    border-right: 1px solid #2a2d3a;
}
.ticker-item .ti-name { color: #8b90a0; font-weight: 700; letter-spacing: .03em; }
.ticker-item .ti-val  { color: #e8eaf0; }
.ticker-item .ti-up   { color: #27ae60; }
.ticker-item .ti-down { color: #e74c3c; }

/* ── BOTTOM NAV ── */
.bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
    background: #1a1d27;
    border-top: 1px solid #2a2d3a;
    display: flex; justify-content: space-around; align-items: center;
    padding: 8px 0 12px 0;
}
.nav-item {
    display:flex; flex-direction:column; align-items:center;
    font-size:0.65rem; color:#8b90a0; cursor:pointer;
    padding: 4px 16px; border-radius:8px;
    transition: all 0.15s;
}
.nav-item.active { color:#3b82f6; }
.nav-item .nav-icon { font-size:1.3rem; margin-bottom:2px; }

/* ── WATCHLIST ROWS ── */
.wl-row {
    display:flex; justify-content:space-between; align-items:center;
    padding: 12px 16px;
    border-bottom: 1px solid #1e2130;
    transition: background 0.12s;
}
.wl-row:hover { background: #1e2130; }
.wl-name  { font-size:0.9rem; font-weight:600; color:#e8eaf0; }
.wl-ticker{ font-size:0.7rem; color:#8b90a0; margin-top:1px; }
.wl-price { font-size:0.95rem; font-weight:700; color:#e8eaf0; text-align:right; }
.wl-chg-g { font-size:0.75rem; color:#27ae60; font-weight:600; text-align:right; }
.wl-chg-r { font-size:0.75rem; color:#e74c3c; font-weight:600; text-align:right; }

/* ── SECTION TITLE ── */
.sec-title {
    font-size:0.78rem; font-weight:600; color:#8b90a0;
    letter-spacing:0.08em; text-transform:uppercase;
    padding: 14px 16px 6px 16px;
}

/* ── PORTFOLIO CARD ── */
.port-card {
    background:#1a1d27; border-radius:10px;
    padding:16px; margin:8px;
    border:1px solid #2a2d3a;
}
.port-label { font-size:0.72rem; color:#8b90a0; margin-bottom:4px; }
.port-val   { font-size:1.3rem; font-weight:700; color:#e8eaf0; }
.port-sub   { font-size:0.78rem; color:#8b90a0; margin-top:2px; }
.pnl-green  { color:#27ae60 !important; }
.pnl-red    { color:#e74c3c !important; }

/* ── ORDER CARD ── */
.order-card {
    background:#1a1d27; border-radius:10px;
    padding:14px 16px; margin-bottom:8px;
    border:1px solid #2a2d3a;
    display:flex; justify-content:space-between; align-items:center;
}
.order-left .o-ticker { font-size:0.92rem; font-weight:700; color:#e8eaf0; }
.order-left .o-detail { font-size:0.72rem; color:#8b90a0; margin-top:2px; }
.order-right { text-align:right; }
.order-right .o-price { font-size:0.92rem; font-weight:600; color:#e8edf0; }
.badge-buy  { background:#0d3320; color:#27ae60; border-radius:4px; padding:2px 8px; font-size:0.68rem; font-weight:700; }
.badge-sell { background:#330d0d; color:#e74c3c; border-radius:4px; padding:2px 8px; font-size:0.68rem; font-weight:700; }

/* ── GAINER/LOSER ROW ── */
.mover-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:10px 16px; border-bottom:1px solid #1e2130;
}
.mover-name  { font-size:0.88rem; font-weight:600; color:#e8eaf0; }
.mover-price { font-size:0.88rem; font-weight:600; color:#e8eaf0; }
.mover-pct-g { font-size:0.78rem; font-weight:700; color:#27ae60; }
.mover-pct-r { font-size:0.78rem; font-weight:700; color:#e74c3c; }

/* Streamlit widget tweaks */
[data-testid="metric-container"] {
    background:#1a1d27; border:1px solid #2a2d3a;
    border-radius:10px; padding:12px 16px !important;
}
[data-baseweb="tab-list"]  { background:#1a1d27; border-radius:8px; }
[data-baseweb="tab"]       { color:#8b90a0 !important; }
[aria-selected="true"]     { color:#3b82f6 !important; border-bottom:2px solid #3b82f6; }
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background:#1a1d27; color:#e8eaf0; border:1px solid #2a2d3a; border-radius:8px;
}
div[data-testid="stSelectbox"] > div { background:#1a1d27; color:#e8eaf0; }
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-thumb { background:#2a2d3a; border-radius:2px; }
</style>
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
if "active_tab"   not in st.session_state: st.session_state.active_tab   = "home"
if "show_balance" not in st.session_state: st.session_state.show_balance = False
if "order_ticker" not in st.session_state: st.session_state.order_ticker = "RELIANCE.NS"
if "order_action" not in st.session_state: st.session_state.order_action = "BUY"
if "expanded_stock" not in st.session_state: st.session_state.expanded_stock = None
if "dark_mode"    not in st.session_state: st.session_state.dark_mode    = True
if "wl_search"    not in st.session_state: st.session_state.wl_search    = ""
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
                        ("TATAMOTORS.NS","Tata Motors"), ("BAJAJ-AUTO.NS","Bajaj Auto"),
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
            ("JAINREC.NS","Jain Resource Recycling"),
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

@st.cache_data(ttl=60 if is_market_open() else 3600)
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

@st.cache_data(ttl=60 if is_market_open() else 3600)
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

@st.cache_data(ttl=60 if is_market_open() else 3600)
def get_batch_quotes(tickers_tuple):
    import yfinance as yf
    import math
    results = {}
    if is_market_open():
        for tkr in tickers_tuple:
            try:
                info = yf.Ticker(tkr).fast_info
                cur  = float(info.last_price)
                prev = float(info.previous_close)
                if math.isnan(cur) or math.isnan(prev) or prev == 0:
                    raise ValueError("nan price")
                chg  = cur - prev
                pct  = (chg / prev) * 100
                results[tkr] = (cur, prev, chg, pct)
            except Exception:
                # Fallback: try hist
                try:
                    hist = yf.Ticker(tkr).history(period="2d", interval="1d")
                    if len(hist) >= 2:
                        prev = float(hist["Close"].iloc[-2])
                        cur  = float(hist["Close"].iloc[-1])
                        if not (math.isnan(cur) or math.isnan(prev)) and prev > 0:
                            chg = cur - prev
                            pct = (chg / prev) * 100
                            results[tkr] = (cur, prev, chg, pct)
                except Exception:
                    continue
    else:
        # Market closed — use history per ticker (more reliable than batch download)
        for tkr in tickers_tuple:
            try:
                hist = yf.Ticker(tkr).history(period="5d", interval="1d")
                hist = hist.dropna(subset=["Close"])
                if len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
                    cur  = float(hist["Close"].iloc[-1])
                    import math
                    if not (math.isnan(cur) or math.isnan(prev)) and prev > 0:
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
@st.cache_data(ttl=60 if is_market_open() else 3600)
def get_holdings_live_prices(holdings_tuple):
    """holdings_tuple = ((ticker, shares, avg_price), ...) — hashable, cache key ban sake."""
    import yfinance as _yf
    results = {}
    for tkr, _shares, _avg in holdings_tuple:
        try:
            info = _yf.Ticker(tkr).info
            prev_c = info.get("previousClose")
            live_c = (info.get("currentPrice") or info.get("regularMarketPrice")
                      or prev_c)
            results[tkr] = {"prev_close": prev_c, "live_price": live_c}
        except Exception:
            results[tkr] = {"prev_close": None, "live_price": None}
    return results

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=1800)
def get_batch_volume_spike(tickers_tuple):
    """
    Volume Spike Detector — aaj ka volume vs pichle 20-din ka average volume.
    2x+ matlab kuch unusual ho raha hai (institutional buying, breakout se
    pehle ka sign), chahe price abhi zyada move na bhi kiya ho. RSI/52W-range
    jaisa hi proven batch+cache pattern.
    """
    import yfinance as yf
    results = {}
    try:
        df = yf.download(
            " ".join(tickers_tuple), period="30d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True
        )
        for tkr in tickers_tuple:
            try:
                sub = df[tkr]["Volume"] if len(tickers_tuple) > 1 else df["Volume"]
                vols = sub.dropna().values.astype(float)
                if len(vols) < 6: continue
                today_vol = float(vols[-1])
                avg_vol   = float(vols[:-1][-20:].mean())  # aaj se pehle ka 20-din avg
                if avg_vol <= 0: continue
                ratio = today_vol / avg_vol
                results[tkr] = dict(ratio=round(ratio, 2), today_vol=int(today_vol),
                                    avg_vol=int(avg_vol))
            except Exception:
                continue
    except Exception:
        pass
    return results

@st.cache_data(ttl=60 if is_market_open() else 3600)
def get_stock_chart(ticker: str, period: str = "3mo", interval: str = "1d"):
    """
    Candlestick chart with volume.
    period/interval combos:
      Intraday: period="1d" interval="1m"  (1min candles, live)
                period="1d" interval="5m"  (5min candles)
                period="5d" interval="15m" (15min candles)
      Daily:    period="1mo"/"3mo"/"6mo"/"1y" interval="1d"
    """
    import yfinance as yf
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import pandas as pd
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        df.reset_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        # x-axis label
        x_col = "Datetime" if "Datetime" in df.columns else "Date"

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
        )

        # ── Candlestick ──────────────────────────────────────────────────────
        fig.add_trace(go.Candlestick(
            x=df[x_col],
            open=df["Open"], high=df["High"],
            low=df["Low"],   close=df["Close"],
            increasing_line_color="#27ae60",
            decreasing_line_color="#e74c3c",
            increasing_fillcolor="#27ae60",
            decreasing_fillcolor="#e74c3c",
            name=ticker,
            showlegend=False,
        ), row=1, col=1)

        # ── 20-period MA line ─────────────────────────────────────────────────
        if len(df) >= 20:
            df["MA20"] = df["Close"].rolling(20).mean()
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["MA20"],
                line=dict(color="#f59e0b", width=1.5, dash="dot"),
                name="MA20", showlegend=True,
            ), row=1, col=1)

        # ── Volume bars ───────────────────────────────────────────────────────
        vol_colors = ["#27ae60" if c >= o else "#e74c3c"
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(
            x=df[x_col], y=df["Volume"],
            marker_color=vol_colors,
            opacity=0.7,
            name="Volume", showlegend=False,
        ), row=2, col=1)

        # ── Layout ────────────────────────────────────────────────────────────
        is_intraday = interval in ("1m", "5m", "15m", "30m")
        fig.update_layout(
            paper_bgcolor="#0f1116",
            plot_bgcolor="#0f1116",
            font=dict(color="#e8eaf0", size=11),
            margin=dict(l=10, r=10, t=20, b=10),
            height=340,
            legend=dict(
                orientation="h", x=0, y=1.02,
                font=dict(size=10, color="#8b90a0"),
                bgcolor="rgba(0,0,0,0)",
            ),
            xaxis=dict(
                gridcolor="#1e2130", showgrid=True,
                rangeslider_visible=False,
                type="date" if not is_intraday else "-",
            ),
            yaxis=dict(gridcolor="#1e2130", showgrid=True),
            xaxis2=dict(gridcolor="#1e2130", showgrid=False),
            yaxis2=dict(gridcolor="#1e2130", showgrid=False,
                        title="Vol", title_font=dict(size=9)),
        )
        return fig
    except Exception:
        return None


@st.cache_data(ttl=300 if is_market_open() else 3600)
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
        "BAJAJFINSV.NS","HCLTECH.NS","TATAMOTORS.NS","TATASTEEL.NS","POWERGRID.NS",
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

@st.cache_data(ttl=300 if is_market_open() else 3600)
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
    BASE_POOL = [
        "MAZDOCK.NS","HAL.NS","GRSE.NS","COCHINSHIP.NS","DATAPATTNS.NS","ZENTEC.NS",
        "PARAS.NS","UNIMECH.NS","IDEAFORGE.NS","KRISHNADEF.NS","BSE.NS","ANGELONE.NS",
        "KPITTECH.NS","JAINREC.NS","NETWEB.NS","THYROCARE.NS",
    ]
    SCREENER_POOL = list(dict.fromkeys(BASE_POOL + list(holding_tickers)))
    results = []
    for tkr in SCREENER_POOL:
        try:
            t    = yf.Ticker(tkr)
            info = t.info
            fi   = t.fast_info
            price   = fi.last_price or 0
            w52h    = info.get("fiftyTwoWeekHigh")  or fi.year_high or 0
            w52l    = info.get("fiftyTwoWeekLow")   or fi.year_low  or 0
            volume  = info.get("volume") or fi.three_month_average_volume or 0
            avg_vol = info.get("averageVolume") or fi.three_month_average_volume or volume or 1
            pe      = info.get("trailingPE")
            pb      = info.get("priceToBook")
            mktcap  = info.get("marketCap") or 0
            sector  = info.get("sector") or "—"
            name    = info.get("shortName") or tkr.replace(".NS","")
            prev    = info.get("previousClose") or price
            chg_pct = ((price - prev) / prev * 100) if prev else 0
            from_52h = ((price - w52h) / w52h * 100) if w52h else 0
            from_52l = ((price - w52l) / w52l * 100) if w52l else 0
            vol_ratio = (volume / avg_vol) if avg_vol else 1
            results.append({
                "ticker": tkr, "name": name, "sector": sector,
                "price": round(price, 2),
                "chg_pct": round(chg_pct, 2),
                "pe": round(pe, 1) if pe else None,
                "pb": round(pb, 2) if pb else None,
                "w52h": round(w52h, 2), "w52l": round(w52l, 2),
                "from_52h": round(from_52h, 1),
                "from_52l": round(from_52l, 1),
                "volume": int(volume),
                "avg_volume": int(avg_vol),
                "vol_ratio": round(vol_ratio, 2),
                "mktcap": mktcap,
            })
        except Exception:
            continue
    return results

@st.cache_data(ttl=900)   # 15 min cache
@st.cache_data(ttl=600)
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
        if st.button(":material/refresh: Refresh", key=f"ri_{widget_key}", use_container_width=True):
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
    try:
        df = yf.download(ticker, start=start, end=end,
                         interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty: return pd.DataFrame()
        df.reset_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        if "Datetime" in df.columns:
            df.rename(columns={"Datetime": "Date"}, inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

# ── Light mode CSS override ────────────────────────────────────────────────────
if not st.session_state.dark_mode:
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"], [data-testid="stSidebar"],
    [data-testid="stMain"], section.main {
        background-color: #f5f6fa !important;
        color: #1a1d27 !important;
    }
    .topbar, .bottom-nav { background:#ffffff !important; border-color:#e0e3ef !important; }
    .topbar-title { color:#1a1d27 !important; }
    .index-chip { background:#f0f2fa !important; }
    .ic-val { color:#1a1d27 !important; }
    .wl-name { color:#1a1d27 !important; }
    .wl-price { color:#1a1d27 !important; }
    .sec-title { color:#555 !important; }
    .port-card, .order-card { background:#ffffff !important; border-color:#e0e3ef !important; }
    .port-val, .o-ticker, .o-price { color:#1a1d27 !important; }
    [data-testid="metric-container"] { background:#ffffff !important; border-color:#e0e3ef !important; }
    [data-baseweb="tab-list"] { background:#ffffff !important; }
    div[style*="background:#1a1d27"] { background:#ffffff !important; }
    div[style*="background:#0f1116"] { background:#f5f6fa !important; }
    </style>
    """, unsafe_allow_html=True)

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

status_dot  = f'<span class="live-dot"></span>' if mkt_open else f'<span class="closed-dot"></span>'
status_txt  = f"LIVE · {time_str}" if mkt_open else f"CLOSED · {time_str}"

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

st.markdown(f"""
<div class="topbar">
  <div class="topbar-left">
    <span class="topbar-title"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" style="vertical-align:-2px;margin-right:5px;"><path d="M3 3v18h18"/><path d="M7 16l4-6 3 4 5-8"/></svg>Market</span>
    {chip_html("NIFTY 50", n50)}
    {chip_html("BANK NIFTY", bnk)}
    {chip_html("SENSEX", snsx)}
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    {status_dot}<span class="status-text">{status_txt}</span>
    <span class="countdown-badge {_countdown_cls}" style="color:{_countdown_color};border-color:{_countdown_color}55;">
      {_countdown_txt}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# Dark/Light toggle — right side
_, tog_col = st.columns([8, 1])
with tog_col:
    mode_icon = ":material/light_mode:" if st.session_state.dark_mode else ":material/dark_mode:"
    mode_tip  = "Light mode" if st.session_state.dark_mode else "Dark mode"
    if st.button(mode_icon, key="toggle_mode", help=mode_tip, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM NAV — tab selector buttons (hidden label, icon + text)
# ══════════════════════════════════════════════════════════════════════════════
tab = st.session_state.active_tab

# ── Pending target orders check karo — har page load pe (market open + ────────
# ── 3:30 PM expiry dono yahan se handle hote hain) ─────────────────────────────
process_target_orders()

# Row 0 — Home (full width, sabse important entry point)
if st.button(":material/home: Home", key="nav_home", use_container_width=True,
             type="primary" if tab=="home" else "secondary"):
    st.session_state.active_tab = "home"; st.rerun()

# ══ MODERN TAB-BAR NAVIGATION (FIXED — no fake JS layer, no hidden-button hack) ══
_sector_tabs = {"defence", "broking", "renewable", "ev_tech", "banking"}
_active_key = tab if tab not in _sector_tabs else "sectors"

_ALL_TABS = [
    ("Watchlist",   "watchlist",   ":material/visibility:"),
    ("Orders",      "orders",      ":material/receipt_long:"),
    ("Portfolio",   "portfolio",   ":material/work:"),
    ("Balance",     "balance",     ":material/account_balance_wallet:"),
    ("News",        "news",        ":material/newspaper:"),
    ("Market",      "market",      ":material/bar_chart:"),
    ("Breadth",     "breadth",     ":material/trending_up:"),
    ("Screener",    "screener",    ":material/search:"),
    ("Calendar",    "calendar",    ":material/calendar_month:"),
    ("AI Analysis", "ai_analysis", ":material/smart_toy:"),
    ("Sectors",     "sectors",     ":material/apartment:"),
]

_isdark = st.session_state.get("theme_mode", "dark") == "dark"
_bg     = "#1a1d27" if _isdark else "#ffffff"
_bdr    = "#2a2d3a" if _isdark else "#dde1eb"
_muted  = "#8b90a0" if _isdark else "#6b7280"
_txt    = "#e8eaf0" if _isdark else "#1a1d27"

# Style the REAL Streamlit buttons inside this container to look like pills.
# Scoped via st.container(key=...) -> Streamlit renders a stable class
# "st-key-navbar_real" on the wrapper div (Streamlit >= 1.36).
# Works on every browser/WebView since it's plain CSS, no :has(), no JS.
st.markdown(f"""
<style>
.st-key-navbar_real {{
    background:{_bg};
    border:1px solid {_bdr};
    border-radius:10px;
    padding:6px 8px;
    margin-bottom:16px;
    overflow-x:auto;
    scrollbar-width:none;
}}
.st-key-navbar_real::-webkit-scrollbar {{ display:none; }}

/* Force the column row to stay in one line and scroll instead of wrapping */
.st-key-navbar_real div[data-testid="stHorizontalBlock"] {{
    flex-wrap:nowrap !important;
    gap:4px !important;
    width:max-content;
}}
.st-key-navbar_real div[data-testid="column"] {{
    width:auto !important;
    flex:0 0 auto !important;
    min-width:0 !important;
}}

/* Pill button look — overrides Streamlit's default button chrome */
.st-key-navbar_real button {{
    background:transparent !important;
    border:none !important;
    border-radius:10px !important;
    color:{_muted} !important;
    font-weight:600 !important;
    font-size:0.82rem !important;
    padding:8px 16px !important;
    white-space:nowrap !important;
    box-shadow:none !important;
    transition:all 0.15s ease;
}}
.st-key-navbar_real button:hover {{
    background:{'#1e2130' if _isdark else '#f0f2f5'} !important;
    color:{_txt} !important;
}}
/* Active tab = Streamlit "primary" button type, restyled as a highlighted pill */
.st-key-navbar_real button[kind="primary"] {{
    background:#3b82f622 !important;
    color:#3b82f6 !important;
    border-bottom:2px solid #3b82f6 !important;
    border-radius:10px 10px 0 0 !important;
}}
</style>
""", unsafe_allow_html=True)

with st.container(key="navbar_real"):
    _nb_cols = st.columns(len(_ALL_TABS))
    for _i, (_lbl, _key, _ico) in enumerate(_ALL_TABS):
        with _nb_cols[_i]:
            if st.button(
                f"{_ico} {_lbl}", key=f"navb_{_key}",
                type="primary" if _active_key == _key else "secondary"
            ):
                if _key == "sectors":
                    st.session_state.active_tab = st.session_state.get("last_sector_tab", "defence")
                else:
                    st.session_state.active_tab = _key
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Helper — Watchlist 2/3 ke stocks ke liye lightweight sector dashboard
# ══════════════════════════════════════════════════════════════════════════════
def render_watch_sector(icon, title, tagline, stocks, refresh_key, sector_key=None):
    """stocks = list of (ticker, display_name, about_text). Live price/% se banta hai,
    6 sub-tabs ke saath — Defence tab jaisa full structure."""
    _CARD = "#1a1d27"; _BORD = "#2a2d3a"; _TXT = "#e8eaf0"; _MUT = "#8b90a0"
    _GRN  = "#27ae60"; _RED  = "#e74c3c"
    sector_key = sector_key or refresh_key.replace("_refresh", "")

    sh, sr = st.columns([5, 1])
    with sh:
        st.markdown(f'<div class="sec-title">{title.upper()}</div>', unsafe_allow_html=True)
    with sr:
        if st.button(":material/refresh:", key=refresh_key, help="Prices refresh karo"):
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
                paper_bgcolor="#0f1116", plot_bgcolor="#0f1116",
                font=dict(color=_TXT, size=11, family="Inter, sans-serif"), height=380,
                margin=dict(l=40, r=60, t=44, b=40),
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.2, font=dict(size=9.5), bgcolor="rgba(0,0,0,0)"),
                title=dict(text="📈 Last 1 mahine ka % trend — sabhi stocks", font=dict(size=13.5, color=_TXT), x=0),
                xaxis=dict(gridcolor="#1c2030", showgrid=True, zeroline=False, tickfont=dict(size=10),
                           showline=True, linecolor="#2a2d3a"),
                yaxis=dict(gridcolor="#1c2030", ticksuffix="%", zeroline=False, tickfont=dict(size=10),
                           showline=False),
                hoverlabel=dict(bgcolor="#1a1d27", bordercolor="#2a2d3a", font=dict(color=_TXT, size=11)),
            )
            st.plotly_chart(fig2, use_container_width=True, key=f"trend_{refresh_key}",
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
                    border:1px solid #ffffff22;border-radius:10px;
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
    HCARD = "#1a1d27"; HBORDER = "#2a2d3a"; HTEXT = "#e8eaf0"; HMUTED = "#8b90a0"
    HGREEN = "#27ae60"; HRED = "#e74c3c"; HBLUE = "#3b82f6"

    home_h, home_r = st.columns([5, 1])
    with home_h:
        st.markdown('<div class="sec-title">🏠 AAJ KA OVERVIEW</div>', unsafe_allow_html=True)
    with home_r:
        if st.button(":material/refresh:", key="home_refresh", help="Prices refresh karo"):
            get_holdings_live_prices.clear()
            st.session_state["_ar_home"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh (Home — Portfolio tab jaisa hi) ──────
    _home_elapsed = time.time() - st.session_state.get("_ar_home", 0)
    if _home_elapsed >= _AUTO_REFRESH_SECS:
        st.session_state["_ar_home"] = time.time()
        st.rerun()

    # ── ⏰ Market Countdown — same badge jo top bar mein hai ─────────────────────
    st.markdown(f"""
    <div style="display:inline-flex;align-items:center;gap:8px;margin-bottom:14px;">
      {status_dot}<span style="font-size:0.78rem;color:{HMUTED};">{status_txt}</span>
      <span class="countdown-badge {_countdown_cls}"
            style="color:{_countdown_color};border-color:{_countdown_color}55;">
        {_countdown_txt}
      </span>
    </div>""", unsafe_allow_html=True)

    # ── 1. Portfolio P&L summary ────────────────────────────────────────────────
    # ── PERMANENT PERF FIX: Portfolio tab jaisa hi shared CACHED function use ──
    # ── karo (get_holdings_live_prices) — isse (1) Home tab khud fast hota hai ──
    # ── 60s cache ke andar, aur (2) Portfolio tab ke saath same cache share hota ─
    # ── hai, matlab dono jagah same data ke liye double network calls nahi hote.─
    total_invested = 0.0
    total_current  = 0.0
    day_pnl_home   = 0.0
    prev_total_val_home = 0.0
    movers = []  # (ticker, pct, pnl_value)

    # ── Market abhi khula nahi (9:15 se pehle) — Day's P&L ₹0 hona chahiye, ──────
    # ── kyunki aaj abhi tak koi trading hui hi nahi hai. ──────────────────────────
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
                # Market khulne wala hai — aaj ka movement abhi shuru hi nahi hua
                day_pct_row = 0.0
                day_pnl_row = 0.0
            else:
                day_pct_row = ((cur_price - prev_c) / prev_c * 100) if prev_c else 0.0
                day_pnl_row = (cur_price - prev_c) * h["shares"] if prev_c else 0.0

            day_pnl_home += day_pnl_row
            prev_total_val_home += (prev_c or cur_price) * h["shares"]
            movers.append((tkr, day_pct_row, cur_val - invested))
        except Exception:
            total_current += invested  # price na mile to fallback invested value

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
    pnl_color = HGREEN if total_pnl >= 0 else HRED
    pnl_arrow = "▲" if total_pnl >= 0 else "▼"

    day_pnl_pct_home = (day_pnl_home / prev_total_val_home * 100) if prev_total_val_home else 0.0
    day_color_home = HGREEN if day_pnl_home >= 0 else HRED
    day_arrow_home = "▲" if day_pnl_home >= 0 else "▼"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#1a1d27);border:1px solid {HBORDER};
                border-radius:16px;padding:18px 20px;margin-bottom:14px;">
      <div style="display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:10px;">
        <div>
          <div style="font-size:0.62rem;color:{HMUTED};font-weight:700;letter-spacing:0.08em;">
            CURRENT VALUE
          </div>
          <div style="font-size:1.4rem;font-weight:900;color:{HTEXT};margin-top:4px;">
            ₹{total_current:,.0f}
          </div>
          <div style="font-size:0.68rem;color:{HMUTED};margin-top:2px;">
            ₹{total_invested:,.0f} invested
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.62rem;color:{HMUTED};font-weight:700;letter-spacing:0.08em;">
            DAY'S P&amp;L
          </div>
          <div style="font-size:1.05rem;font-weight:900;color:{day_color_home};margin-top:4px;">
            {day_arrow_home} ₹{abs(day_pnl_home):,.0f}
          </div>
          <div style="font-size:0.68rem;color:{day_color_home};margin-top:2px;">
            {day_pnl_pct_home:+.2f}%
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.62rem;color:{HMUTED};font-weight:700;letter-spacing:0.08em;">
            TOTAL P&amp;L
          </div>
          <div style="font-size:1.05rem;font-weight:900;color:{pnl_color};margin-top:4px;">
            {pnl_arrow} ₹{abs(total_pnl):,.0f}
          </div>
          <div style="font-size:0.68rem;color:{pnl_color};margin-top:2px;">
            {total_pnl_pct:+.2f}%
          </div>
        </div>
      </div>
      <div style="font-size:0.68rem;color:{HMUTED};margin-top:10px;border-top:1px solid {HBORDER};padding-top:8px;">
        Cash available ₹{st.session_state.pt_cash:,.0f}
        {(" · Market abhi khula nahi — Day ka P&L 9:15 AM ke baad update hoga") if _pre_market else ""}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── 2. Top movers from holdings (sorted by abs day %) ───────────────────────
    if movers:
        movers_sorted = sorted(movers, key=lambda m: abs(m[1]), reverse=True)[:3]
        st.markdown(f'<div style="font-size:0.68rem;font-weight:800;color:{HMUTED};'
                    f'letter-spacing:0.08em;margin-bottom:8px;">📊 AAJ KE TOP MOVERS (TUMHARE HOLDINGS)</div>',
                    unsafe_allow_html=True)
        mv_cols = st.columns(len(movers_sorted))
        for col, (tkr, pct, pnl_val) in zip(mv_cols, movers_sorted):
            mcolor = HGREEN if pct >= 0 else HRED
            marrow = "▲" if pct >= 0 else "▼"
            with col:
                st.markdown(f"""
                <div style="background:{HCARD};border:1px solid {mcolor}44;border-radius:10px;
                            padding:12px 14px;text-align:center;border-top:3px solid {mcolor};">
                  <div style="font-size:0.85rem;font-weight:800;color:{HTEXT};">{tkr.replace('.NS','')}</div>
                  <div style="font-size:1rem;font-weight:900;color:{mcolor};margin-top:4px;">
                    {marrow} {abs(pct):.2f}%
                  </div>
                  <div style="font-size:0.65rem;color:{HMUTED};margin-top:2px;">today</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:{HCARD};border:1px solid {HBORDER};border-radius:10px;
                    padding:16px;text-align:center;color:{HMUTED};font-size:0.8rem;margin-bottom:8px;">
          Abhi koi holding nahi hai — Portfolio tab se shuru karo.
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── 3. Pending target orders ─────────────────────────────────────────────────
    _pending = st.session_state.get("pt_targets", [])
    st.markdown(f'<div style="font-size:0.68rem;font-weight:800;color:{HMUTED};'
                f'letter-spacing:0.08em;margin-bottom:8px;">⏱ PENDING TARGET ORDERS</div>',
                unsafe_allow_html=True)
    if _pending:
        for tgt in _pending[:4]:
            st.markdown(f"""
            <div style="background:{HCARD};border:1px solid {HBORDER};border-radius:10px;
                        padding:10px 14px;margin-bottom:6px;display:flex;
                        justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
              <div>
                <span style="font-size:0.85rem;font-weight:800;color:{HTEXT};">{tgt['ticker'].replace('.NS','')}</span>
                <span style="font-size:0.7rem;color:{HMUTED};margin-left:8px;">{tgt['action']} {tgt['qty']} shares</span>
              </div>
              <span style="font-size:0.82rem;font-weight:700;color:{HBLUE};">@ ₹{tgt['target_price']:,.2f}</span>
            </div>""", unsafe_allow_html=True)
        if len(_pending) > 4:
            st.markdown(f'<div style="font-size:0.7rem;color:{HMUTED};">+{len(_pending)-4} more — Orders tab mein dekho</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:{HCARD};border:1px solid {HBORDER};border-radius:10px;
                    padding:12px;text-align:center;color:{HMUTED};font-size:0.78rem;">
          Koi pending target order nahi hai.
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── 4. Aaj/kal ka important calendar event ──────────────────────────────────
    _today = ist_now().date()
    _upcoming_events = sorted(
        [e for e in get_calendar_events() if e["date"] >= _today],
        key=lambda e: e["date"]
    )[:2]
    if _upcoming_events:
        st.markdown(f'<div style="font-size:0.68rem;font-weight:800;color:{HMUTED};'
                    f'letter-spacing:0.08em;margin-bottom:8px;">📅 AAGE KYA AANE WALA HAI</div>',
                    unsafe_allow_html=True)
        for ev in _upcoming_events:
            days_away = (ev["date"] - _today).days
            when_str = "Aaj" if days_away == 0 else ("Kal" if days_away == 1 else f"{days_away} din mein")
            st.markdown(f"""
            <div style="background:{HCARD};border:1px solid {ev['color']}44;border-radius:10px;
                        padding:10px 14px;margin-bottom:6px;border-left:3px solid {ev['color']};">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <span style="font-size:0.82rem;font-weight:700;color:{HTEXT};">{ev['icon']} {ev['title']}</span>
                <span style="font-size:0.68rem;color:{ev['color']};font-weight:700;">{when_str}</span>
              </div>
              <div style="font-size:0.7rem;color:{HMUTED};margin-top:3px;">{ev['desc']}</div>
            </div>""", unsafe_allow_html=True)

    # ── 5. Quick links — Home se seedha kahin bhi jump karo ────────────────────
    st.markdown(f'<div style="font-size:0.68rem;font-weight:800;color:{HMUTED};'
                f'letter-spacing:0.08em;margin:14px 0 8px;">🔗 QUICK JUMP</div>',
                unsafe_allow_html=True)
    qj1, qj2, qj3 = st.columns(3)
    with qj1:
        if st.button("💼 Portfolio", key="home_qj_port", use_container_width=True):
            st.session_state.active_tab = "portfolio"; st.rerun()
    with qj2:
        if st.button("📋 Orders", key="home_qj_ord", use_container_width=True):
            st.session_state.active_tab = "orders"; st.rerun()
    with qj3:
        if st.button("📰 News", key="home_qj_news", use_container_width=True):
            st.session_state.active_tab = "news"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
if tab == "watchlist":

    # ── Watchlist GROUP tabs (Zerodha jaisa — multiple watchlists) ─────────────
    # Custom watchlists (Watchlist 1/2/3 + user-created) aur 13 Sector watchlists
    # ko alag-alag dikhate hain, taaki list lambi hone par bhi organised rahe.
    all_group_names    = list(st.session_state.watchlist_groups.keys())
    sector_names_set   = set(SECTOR_WATCHLISTS.keys())
    custom_group_names = [g for g in all_group_names if g not in sector_names_set]
    sector_group_names = [g for g in all_group_names if g in sector_names_set]

    def _render_group_row(names, per_row=4, key_prefix="wlgrp"):
        """names ke buttons ko per_row ke hisaab se multiple rows mein wrap karke render karo."""
        for start in range(0, len(names), per_row):
            chunk = names[start:start + per_row]
            cols  = st.columns(per_row)
            for ci, gname in enumerate(chunk):
                with cols[ci]:
                    is_active = (gname == st.session_state.active_watchlist_group)
                    if st.button(gname, key=f"{key_prefix}_{gname}", use_container_width=True,
                                 type="primary" if is_active else "secondary"):
                        st.session_state.active_watchlist_group = gname
                        st.session_state.expanded_stock = None
                        st.rerun()
            # Baaki khaali columns ko khaali hi rehne do (agar last row poori na bhare)

    st.markdown('<div class="sec-title" style="padding:6px 4px 4px;">MY WATCHLISTS</div>',
                unsafe_allow_html=True)
    _render_group_row(custom_group_names, per_row=3, key_prefix="wlgrp")

    add_col, _sp = st.columns([1, 3])
    with add_col:
        if st.button("➕ Naya Watchlist", key="wlgrp_new_toggle", use_container_width=True,
                     help="Naya watchlist group banao"):
            st.session_state.show_new_group = not st.session_state.get("show_new_group", False)
            st.rerun()

    if sector_group_names:
        st.markdown('<div class="sec-title" style="padding:10px 4px 4px;">🧭 SECTOR WATCHLISTS</div>',
                    unsafe_allow_html=True)
        _render_group_row(sector_group_names, per_row=4, key_prefix="wlsec")

    if st.session_state.get("show_new_group", False):
        ng1, ng2 = st.columns([3, 1])
        with ng1:
            new_group_name = st.text_input(
                "Naya group ka naam", key="new_group_name_input",
                placeholder="e.g. Watchlist 3", label_visibility="collapsed"
            ).strip()
        with ng2:
            if st.button("✅ Banao", key="confirm_new_group", use_container_width=True):
                if not new_group_name:
                    st.error("Naam dalo!")
                elif new_group_name in st.session_state.watchlist_groups:
                    st.warning(f"⚠️ '{new_group_name}' already hai!")
                else:
                    st.session_state.watchlist_groups[new_group_name] = []
                    st.session_state.active_watchlist_group = new_group_name
                    st.session_state.custom_watchlist = st.session_state.watchlist_groups[new_group_name]
                    st.session_state.show_new_group = False
                    st.rerun()

    # ── Header row ────────────────────────────────────────────────────────────
    h1, h3, h4 = st.columns([4, 1, 1])
    with h1:
        st.markdown('<div class="sec-title">MY WATCHLIST</div>', unsafe_allow_html=True)
    with h3:
        if st.button("➕ Add", key="wl_add_btn", use_container_width=True):
            st.session_state.show_add_stock = not st.session_state.get("show_add_stock", False)
            st.rerun()
    with h4:
        if st.button(":material/refresh:", key="wl_refresh", use_container_width=True):
            get_batch_quotes.clear()
            get_index_quote.clear()
            st.session_state["_ar_watchlist"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh (watchlist) ─────────────────────────
    _wl_elapsed = time.time() - st.session_state.get("_ar_watchlist", 0)
    if _wl_elapsed >= _AUTO_REFRESH_SECS:
        get_batch_quotes.clear()
        get_index_quote.clear()
        st.session_state["_ar_watchlist"] = time.time()
        st.rerun()

    # ── Add stock panel ───────────────────────────────────────────────────────
    if st.session_state.get("show_add_stock", False):
        st.markdown("""
        <div style="background:#0d2015;border:1px solid #27ae60;border-radius:10px;padding:12px 16px;margin-bottom:8px;">
          <span style="color:#27ae60;font-weight:700;font-size:0.85rem;">➕ STOCK ADD KARO WATCHLIST MEIN</span>
        </div>""", unsafe_allow_html=True)
        a1, a2, a3 = st.columns([2, 2, 1])
        with a1:
            new_ticker = st.text_input("NSE Ticker (e.g. MARUTI.NS)", key="new_stock_ticker",
                                        placeholder="TATAMOTORS.NS").upper().strip()
        with a2:
            new_name = st.text_input("Display Name (e.g. Tata Motors)", key="new_stock_name",
                                      placeholder="Tata Motors")
        with a3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Add", key="confirm_add", use_container_width=True):
                if new_ticker and new_name:
                    existing = [t for t, _ in st.session_state.custom_watchlist]
                    if new_ticker in existing:
                        st.warning(f"⚠️ {new_ticker} already watchlist mein hai!")
                    else:
                        st.session_state.custom_watchlist.append((new_ticker, new_name))
                        st.session_state.show_add_stock = False
                        st.success(f"✅ {new_name} add ho gaya!")
                        st.rerun()
                else:
                    st.error("Ticker aur naam dono chahiye!")

    # ── Search bar ────────────────────────────────────────────────────────────
    search_query = st.text_input(
        "", placeholder="🔍 Watchlist mein dhundo... (BSE, HDFC, Reliance)",
        key="wl_search_input", label_visibility="collapsed"
    ).strip().lower()

    # Filter watchlist based on search
    filtered_wl = [
        (tkr, name) for tkr, name in st.session_state.custom_watchlist
        if (search_query == "" or search_query in name.lower() or search_query in tkr.lower())
    ]

    if not filtered_wl and search_query:
        st.markdown(f"""
        <div style="text-align:center;padding:24px;color:#8b90a0;">
          <div style="font-size:1.5rem;">🔍</div>
          <div style="margin-top:6px;">"{search_query}" nahi mila watchlist mein</div>
          <div style="font-size:0.78rem;margin-top:4px;">➕ Add button se naya stock jodo</div>
        </div>""", unsafe_allow_html=True)

    all_tickers = tuple(t for t, _ in filtered_wl) if filtered_wl else ()
    if all_tickers:
        with st.spinner("Loading prices & signals…"):
            batch     = get_batch_quotes(all_tickers)
            batch_rsi = get_batch_rsi(all_tickers)
            batch_52w = get_batch_52w_range(all_tickers)
            batch_vol = get_batch_volume_spike(all_tickers)
    else:
        batch     = {}
        batch_rsi = {}
        batch_52w = {}
        batch_vol = {}

    for tkr, name in filtered_wl:
        q            = batch.get(tkr)
        owned_shares = st.session_state.pt_holdings.get(tkr, {}).get("shares", 0)
        is_expanded  = st.session_state.expanded_stock == tkr

        # Build RSI signal HTML first
        sig = batch_rsi.get(tkr) if batch_rsi else None
        if sig:
            sc       = sig["color"]
            ma_arrow = "▲" if sig["above_ma"] else "▼"
            ma_clr   = "#27ae60" if sig["above_ma"] else "#e74c3c"
            signal_html = (
                f'<div style="display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap;">'
                f'<span style="background:{sc}22;color:{sc};border:1px solid {sc}55;'
                f'border-radius:20px;padding:2px 10px;font-size:0.68rem;font-weight:800;">{sig["label"]}</span>'
                f'<span style="font-size:0.65rem;color:#8b90a0;">RSI <b style="color:{sc};">{sig["rsi"]}</b></span>'
                f'<span style="font-size:0.65rem;color:#8b90a0;">MA20 <b style="color:{ma_clr};">{ma_arrow}{abs(sig["ma_dist"])}%</b></span>'
                f'<span style="font-size:0.63rem;color:#5b6380;font-style:italic;">&nbsp;{sig["detail"]}</span>'
                f'</div>'
            )
        else:
            signal_html = ""

        # ── 52-Week Range bar — stock apne saal ke range mein kahan khada hai ───
        w52 = batch_52w.get(tkr) if batch_52w else None
        if w52:
            pos = w52["pos_pct"]
            if pos >= 90:
                bar_color, bar_note = "#e74c3c", "52W HIGH ke bahut kareeb"
            elif pos >= 70:
                bar_color, bar_note = "#f97316", "Momentum zone"
            elif pos <= 10:
                bar_color, bar_note = "#06b6d4", "52W LOW ke bahut kareeb"
            elif pos <= 30:
                bar_color, bar_note = "#84cc16", "Value zone"
            else:
                bar_color, bar_note = "#8b90a0", "Mid-range"
            range_html = (
                f'<div style="margin-top:6px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:0.6rem;color:#5b6380;margin-bottom:2px;">'
                f'<span>₹{w52["w52_low"]:,.0f}</span>'
                f'<span style="color:{bar_color};font-weight:700;">{bar_note} ({w52["from_high_pct"]:+.1f}% from high)</span>'
                f'<span>₹{w52["w52_high"]:,.0f}</span>'
                f'</div>'
                f'<div style="position:relative;height:6px;background:#2a2d3a;border-radius:4px;">'
                f'<div style="position:absolute;left:{pos}%;top:-2px;width:3px;height:10px;'
                f'background:{bar_color};border-radius:2px;"></div>'
                f'</div></div>'
            )
            signal_html += range_html

        # ── Volume Spike badge — aaj ka volume normal se kitna zyada hai ────────
        vol = batch_vol.get(tkr) if batch_vol else None
        if vol and vol["ratio"] >= 1.5:
            if vol["ratio"] >= 3:
                vol_color, vol_label = "#e74c3c", "🔥 EXTREME spike"
            elif vol["ratio"] >= 2:
                vol_color, vol_label = "#f97316", "🔥 Volume Spike"
            else:
                vol_color, vol_label = "#f59e0b", "📊 Above-avg volume"
            signal_html += (
                f'<div style="margin-top:6px;background:{vol_color}15;border:1px solid {vol_color}55;'
                f'border-radius:8px;padding:5px 10px;font-size:0.68rem;color:{vol_color};font-weight:700;">'
                f'{vol_label}: aaj ka volume normal se <b>{vol["ratio"]}x</b> zyada hai — '
                f'kuch unusual ho sakta hai'
                f'</div>'
            )

        # Columns: info | 📊 | B | S | 🗑
        row_col, chart_col, b_col, s_col, del_col = st.columns([5.5, 0.8, 0.8, 0.8, 0.6])

        # ── Info card — ONLY st.markdown here, no buttons ─────────────────────
        with row_col:
            if q:
                cur, _, chg, pct = q
                chg_c = "#27ae60" if chg >= 0 else "#e74c3c"
                arrow = "▲" if chg >= 0 else "▼"
                owned_badge = (
                    f'&nbsp;<span style="background:#0d2340;color:#3b82f6;'
                    f'border-radius:4px;padding:1px 6px;font-size:0.68rem;">'
                    f'{owned_shares} owned</span>'
                ) if owned_shares > 0 else ''
                expand_icon = "▾" if is_expanded else "▸"
                st.markdown(
                    f'<div style="background:#1a1d27;border:1px solid {"#3b82f6" if is_expanded else "#2a2d3a"};'
                    f'border-radius:10px;padding:10px 16px;margin-bottom:4px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div><span style="font-size:0.72rem;color:#8b90a0;">{expand_icon}</span>'
                    f'&nbsp;<span style="font-size:0.92rem;font-weight:700;color:#e8eaf0;">{name}</span>'
                    f'&nbsp;<span style="font-size:0.72rem;color:#8b90a0;">{tkr.replace(".NS","")}</span>'
                    f'{owned_badge}</div>'
                    f'<div style="text-align:right;">'
                    f'<span style="font-size:0.95rem;font-weight:700;color:#e8eaf0;">₹{cur:,.2f}</span>'
                    f'&nbsp;<span style="color:{chg_c};font-size:0.75rem;font-weight:600;">{arrow}{abs(pct):.2f}%</span>'
                    f'</div></div>'
                    f'{signal_html}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div style="background:#1a1d27;border:1px solid #2a2d3a;'
                    f'border-radius:10px;padding:10px 16px;margin-bottom:4px;">'
                    f'<span style="font-size:0.92rem;font-weight:700;color:#e8eaf0;">{name}</span>'
                    f'&nbsp;<span style="font-size:0.72rem;color:#8b90a0;">{tkr.replace(".NS","")} — Loading…</span>'
                    f'{signal_html}</div>',
                    unsafe_allow_html=True
                )

        # ── Buttons — each in its own column ──────────────────────────────────
        with chart_col:
            if st.button("📊" if not is_expanded else "✕",
                         key=f"wlexp_{tkr}", use_container_width=True):
                st.session_state.expanded_stock = None if is_expanded else tkr
                st.rerun()
        with b_col:
            with st.container(key=f"buybtn_{tkr}"):
                if st.button(":material/add: Buy", key=f"wlb_{tkr}", use_container_width=True, type="primary"):
                    st.session_state.order_ticker = tkr
                    st.session_state.order_action = "BUY"
                    st.session_state.active_tab   = "orders"
                    st.rerun()
        with s_col:
            with st.container(key=f"sellbtn_{tkr}"):
                if st.button(":material/remove: Sell", key=f"wls_{tkr}", use_container_width=True, type="secondary"):
                    st.session_state.order_ticker = tkr
                    st.session_state.order_action = "SELL"
                    st.session_state.active_tab   = "orders"
                    st.rerun()
        with del_col:
            if st.button("🗑", key=f"wldel_{tkr}", use_container_width=True):
                st.session_state.custom_watchlist = [
                    (t, n) for t, n in st.session_state.custom_watchlist if t != tkr
                ]
                st.session_state.watchlist_groups[st.session_state.active_watchlist_group] = \
                    st.session_state.custom_watchlist
                if st.session_state.expanded_stock == tkr:
                    st.session_state.expanded_stock = None
                st.rerun()

        # ── Expanded panel: Chart + 52W + P/E + MarketCap ─────────────────────
        if is_expanded:
            with st.spinner(f"{name} ka data load ho raha hai…"):
                info  = get_stock_info(tkr)
                chart = get_stock_chart(tkr)

            # 52W + P/E + MarketCap strip
            w52h  = f"₹{info['w52_high']:,.2f}"  if info.get("w52_high")  else "—"
            w52l  = f"₹{info['w52_low']:,.2f}"   if info.get("w52_low")   else "—"
            pe    = f"{info['pe']:.1f}x"          if info.get("pe")        else "—"
            mcap  = info.get("mktcap")
            if mcap:
                if mcap >= 1e12:   mcap_str = f"₹{mcap/1e12:.2f}T"
                elif mcap >= 1e9:  mcap_str = f"₹{mcap/1e9:.2f}B"
                else:              mcap_str = f"₹{mcap/1e7:.1f}Cr"
            else:
                mcap_str = "—"
            div_y = f"{info['div_yield']*100:.2f}%" if info.get("div_yield") else "—"
            sector = info.get("sector", "—")

            st.markdown(f"""
            <div style="background:#13161f;border:1px solid #2a2d3a;border-radius:10px;
                        padding:12px 16px;margin:0 0 8px 0;">
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
                <div style="flex:1;min-width:80px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">52W HIGH</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#27ae60;">{w52h}</div>
                </div>
                <div style="flex:1;min-width:80px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">52W LOW</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#e74c3c;">{w52l}</div>
                </div>
                <div style="flex:1;min-width:80px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">P/E RATIO</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#e8eaf0;">{pe}</div>
                </div>
                <div style="flex:1;min-width:80px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">MKT CAP</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#e8eaf0;">{mcap_str}</div>
                </div>
                <div style="flex:1;min-width:80px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">DIV YIELD</div>
                  <div style="font-size:0.88rem;font-weight:700;color:#e8eaf0;">{div_y}</div>
                </div>
                <div style="flex:2;min-width:120px;background:#1a1d27;border-radius:8px;padding:8px 12px;text-align:center;">
                  <div style="font-size:0.65rem;color:#8b90a0;">SECTOR</div>
                  <div style="font-size:0.82rem;font-weight:600;color:#8b9ef0;">{sector}</div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

            # ── Chart timeframe selector ──────────────────────────────────────
            market_open = is_market_open()

            # Label → (period, interval)
            if market_open:
                tf_options = {
                    "⚡ 1min": ("1d",  "1m"),
                    "📊 5min": ("1d",  "5m"),
                    "🕐 15min":("5d",  "15m"),
                    "1M":      ("1mo", "1d"),
                    "3M":      ("3mo", "1d"),
                    "6M":      ("6mo", "1d"),
                    "1Y":      ("1y",  "1d"),
                }
                default_idx = 0   # live 1min when market open
            else:
                tf_options = {
                    "📊 5min": ("1d",  "5m"),
                    "🕐 15min":("5d",  "15m"),
                    "1M":      ("1mo", "1d"),
                    "3M":      ("3mo", "1d"),
                    "6M":      ("6mo", "1d"),
                    "1Y":      ("1y",  "1d"),
                }
                default_idx = 2   # 1M when market closed

            tf_labels = list(tf_options.keys())
            sel_tf = st.radio(
                "Timeframe", tf_labels,
                index=default_idx,
                horizontal=True,
                key=f"tf_{tkr}",
                label_visibility="collapsed",
            )

            sel_period, sel_interval = tf_options[sel_tf]
            is_intraday = sel_interval in ("1m", "5m", "15m")

            # Live badge when intraday + market open
            if is_intraday and market_open:
                st.markdown(
                    '<span style="background:#27ae6022;color:#27ae60;border:1px solid #27ae6055;'
                    'border-radius:20px;padding:2px 10px;font-size:0.68rem;font-weight:700;">'
                    '🔴 LIVE — Auto data</span>',
                    unsafe_allow_html=True
                )
            elif is_intraday and not market_open:
                st.markdown(
                    '<span style="background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b55;'
                    'border-radius:20px;padding:2px 10px;font-size:0.68rem;font-weight:700;">'
                    '🕐 Market Closed — Last session data</span>',
                    unsafe_allow_html=True
                )

            # TTL: 1min refresh for live intraday, else cache
            @st.cache_data(ttl=60 if (is_intraday and market_open) else 3600)
            def _load_chart(t, p, iv):
                return get_stock_chart(t, p, iv)

            with st.spinner("Chart load ho raha hai..."):
                chart = _load_chart(tkr, sel_period, sel_interval)

            if chart:
                st.plotly_chart(chart, use_container_width=True,
                                key=f"chart_{tkr}_{sel_tf}")
            else:
                st.info("Chart data available nahi hai.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ORDERS
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "orders":

    # ── Header with Refresh ───────────────────────────────────────────────────
    ord_h, ord_r = st.columns([5, 1])
    with ord_h:
        st.markdown('<div class="sec-title">PLACE ORDER</div>', unsafe_allow_html=True)
    with ord_r:
        if st.button(":material/refresh:", key="orders_refresh", help="Price refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            st.session_state["_ar_orders"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh (orders) ────────────────────────────
    _ord_elapsed = time.time() - st.session_state.get("_ar_orders", 0)
    if _ord_elapsed >= _AUTO_REFRESH_SECS:
        get_index_quote.clear()
        get_batch_quotes.clear()
        st.session_state["_ar_orders"] = time.time()
        st.rerun()

    # ── Position Sizing Calculator se "fill qty" hua ho to widget render se ────
    # ── PEHLE apply karo (Streamlit rule: render ke baad direct set nahi kar sakte) ──
    if "_psc_pending_qty" in st.session_state:
        st.session_state.pt_qty = st.session_state.pop("_psc_pending_qty")

    def avg_color_word(change):
        """Averaging calculator ke liye chhota helper — average kam/zyada hua, kितने se."""
        if change is None:
            return ""
        if change < 0:
            return f"₹{abs(change):,.2f} kam hua (accha hai)"
        elif change > 0:
            return f"₹{change:,.2f} zyada hua"
        return "same raha"

    # ── Pre-fill from watchlist click ─────────────────────────────────────────
    wl_names   = [name for _, name in WATCHLIST]
    wl_tickers = [tkr  for tkr, _ in WATCHLIST]
    try:
        def_idx = wl_tickers.index(st.session_state.get("order_ticker", wl_tickers[0]))
    except ValueError:
        def_idx = 0

    # ── Order form — clean, no section header ─────────────────────────────────
    sel_col, qty_col = st.columns([3, 1])
    with sel_col:
        chosen_name   = st.selectbox("Stock", options=wl_names, index=def_idx, key="order_stock_select", label_visibility="collapsed")
        chosen_ticker = wl_tickers[wl_names.index(chosen_name)]
    with qty_col:
        pt_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="pt_qty", label_visibility="collapsed")

    pt_quote = get_index_quote(chosen_ticker)
    if pt_quote:
        pt_price  = pt_quote[0]
        total_val = round(pt_price * pt_qty, 2)
        chg_c  = "#27ae60" if pt_quote[2] >= 0 else "#e74c3c"
        arrow  = "▲" if pt_quote[2] >= 0 else "▼"
        owned  = st.session_state.pt_holdings.get(chosen_ticker, {}).get("shares", 0)
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;
                    padding:10px 16px;margin:6px 0 10px 0;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <div>
            <span style="font-size:1.2rem;font-weight:800;color:#e8eaf0;">₹{pt_price:,.2f}</span>
            &nbsp;<span style="color:{chg_c};font-size:0.82rem;font-weight:600;">{arrow} {abs(pt_quote[2]):,.2f} ({pt_quote[3]:+.2f}%)</span>
          </div>
          <div style="font-size:0.78rem;color:#8b90a0;">
            Value: <b style="color:#e8eaf0;">₹{total_val:,.2f}</b> &nbsp;|&nbsp;
            Cash: <b style="color:#3b82f6;">₹{st.session_state.pt_cash:,.0f}</b> &nbsp;|&nbsp;
            Holdings: <b style="color:#e8eaf0;">{owned} shares</b>
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        pt_price  = None
        total_val = 0
        st.warning("⚠️ Price fetch nahi hui. Thodi der mein try karo.")

    b_col, s_col = st.columns(2)
    with b_col:
        with st.container(key="execbuybtn"):
            do_buy  = st.button(":material/add_circle: BUY", key="exec_buy",  type="primary",   use_container_width=True)
    with s_col:
        with st.container(key="execsellbtn"):
            do_sell = st.button(":material/remove_circle: SELL", key="exec_sell", type="secondary", use_container_width=True)

    if pt_price and do_buy:
        holding = st.session_state.pt_holdings.get(chosen_ticker, {"shares": 0, "avg_price": 0.0})
        if total_val > st.session_state.pt_cash:
            st.error(f"❌ Balance kam hai! Chahiye ₹{total_val:,.2f}, hai ₹{st.session_state.pt_cash:,.0f}")
        else:
            new_shares = holding["shares"] + pt_qty
            new_avg    = round((holding["shares"] * holding["avg_price"] + total_val) / new_shares, 2)
            # Pehli baar buy ho rahi hai to date set karo; agar already hai (averaging up)
            # to purani date hi rakho — holding continue hi ho rahi hai
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

    if pt_price and do_sell:
        holding = st.session_state.pt_holdings.get(chosen_ticker, {"shares": 0, "avg_price": 0.0})
        if holding["shares"] == 0:
            st.error(f"❌ {chosen_name} ke koi shares nahi hain!")
        elif holding["shares"] < pt_qty:
            st.error(f"❌ Sirf {holding['shares']} shares hain!")
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

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # 🎯 POSITION SIZING CALCULATOR — Disciplined trading ke liye
    # "Agar sirf X% capital risk karna hai, to kितne shares kharidne chahiye
    # stop-loss ke hisaab se" — naya trade lagane se pehle yeh dekh lo
    # ══════════════════════════════════════════════════════════════════════════
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
                help="Default: aapka current net worth (cash + invested). Chahe to badal lo."
            )
        with psc_c2:
            psc_risk_pct = st.slider(
                "Risk per trade (%)", min_value=0.5, max_value=10.0, value=5.0, step=0.5,
                key="psc_risk_pct",
                help="Total capital ka kितना % aap is ek trade mein risk karna chahte ho."
            )

        psc_c3, psc_c4 = st.columns(2)
        with psc_c3:
            psc_entry = st.number_input(
                "Entry Price (₹)", min_value=0.01,
                value=float(pt_price) if pt_price else 100.0,
                step=0.05, key="psc_entry",
                help="Jis price pe BUY karne ka plan hai (default: upar selected stock ka current price)."
            )
        with psc_c4:
            psc_default_sl = round(psc_entry * 0.95, 2) if psc_entry else 95.0
            psc_stoploss = st.number_input(
                "Stop-Loss Price (₹)", min_value=0.01,
                value=psc_default_sl, step=0.05, key="psc_stoploss",
                help="Jis price pe aap loss book karke nikal jaoge."
            )

        # ── Calculation ──────────────────────────────────────────────────────────
        psc_risk_amount    = psc_capital * (psc_risk_pct / 100)
        psc_risk_per_share = psc_entry - psc_stoploss

        if psc_risk_per_share <= 0:
            st.error("❌ Stop-Loss Entry Price se kam hona chahiye (BUY ke liye). Values check karo.")
        else:
            psc_shares      = int(psc_risk_amount // psc_risk_per_share)
            psc_actual_cost = round(psc_shares * psc_entry, 2)
            psc_actual_risk = round(psc_shares * psc_risk_per_share, 2)
            psc_risk_of_cap = (psc_actual_risk / psc_capital * 100) if psc_capital else 0
            psc_sl_pct      = (psc_risk_per_share / psc_entry * 100) if psc_entry else 0

            if psc_shares == 0:
                st.warning("⚠️ Is risk amount mein 1 share bhi nahi ban raha — risk % badhao ya stop-loss entry ke paas rakho.")
            else:
                exceeds_cash = psc_actual_cost > st.session_state.pt_cash
                cash_note = (f'<div style="font-size:0.72rem;color:#e74c3c;margin-top:8px;">'
                            f'⚠️ Yeh cost aapki available cash (₹{st.session_state.pt_cash:,.0f}) se zyada hai.</div>'
                            if exceeds_cash else "")
                st.markdown(f"""
                <div style="background:#0d1626;border:1px solid #3b82f655;border-radius:10px;
                            padding:18px 20px;margin-top:10px;">
                  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;">
                    <div>
                      <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">SHARES KHARIDO</div>
                      <div style="font-size:2.2rem;font-weight:900;color:#3b82f6;line-height:1.1;">{psc_shares:,}</div>
                      <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">stop-loss ke hisaab se</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">TOTAL INVESTMENT</div>
                      <div style="font-size:1.3rem;font-weight:700;color:#e8eaf0;">₹{psc_actual_cost:,.0f}</div>
                      <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">{(psc_actual_cost/psc_capital*100 if psc_capital else 0):.1f}% of capital</div>
                    </div>
                  </div>
                  <div style="height:1px;background:#2a2d3a;margin:14px 0;"></div>
                  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;">
                    <div>
                      <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">MAX LOSS (stop-loss hit hone par)</div>
                      <div style="font-size:1.15rem;font-weight:700;color:#e74c3c;">▼ ₹{psc_actual_risk:,.0f}</div>
                      <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">= {psc_risk_of_cap:.2f}% of total capital</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">STOP-LOSS DISTANCE</div>
                      <div style="font-size:1.15rem;font-weight:700;color:#e8eaf0;">₹{psc_risk_per_share:,.2f}</div>
                      <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">{psc_sl_pct:.2f}% entry se neeche</div>
                    </div>
                  </div>
                  {cash_note}
                </div>
                """, unsafe_allow_html=True)

                if st.button("📋 Yeh Qty Order Form mein bhar do", key="psc_fill_qty", use_container_width=True):
                    st.session_state._psc_pending_qty = psc_shares
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # 📉 AVERAGING / PYRAMID CALCULATOR — loss wale stock ko average karne ka
    # "agar ₹X pe aur Y shares lo, to naya average price Z hoga"
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("📉 Averaging Calculator — naya average price kya hoga?", expanded=False):
        st.caption("Loss mein chal rahe stock mein aur shares lekar average kam karne ka calculator — "
                   "dekho naya average kya banega, aur breakeven tak kitna % uthna hoga.")

        _existing = st.session_state.pt_holdings.get(chosen_ticker)

        avg_c1, avg_c2 = st.columns(2)
        with avg_c1:
            avg_old_qty = st.number_input(
                "Purani Qty (already holding)", min_value=0,
                value=int(_existing["shares"]) if _existing else 0,
                step=1, key="avg_old_qty",
                help="Default: upar selected stock ki aapki current holding qty."
            )
        with avg_c2:
            avg_old_price = st.number_input(
                "Purana Avg Price (₹)", min_value=0.0,
                value=float(_existing["avg_price"]) if _existing else 0.0,
                step=0.05, key="avg_old_price",
                help="Default: upar selected stock ka aapka current average cost."
            )

        avg_c3, avg_c4 = st.columns(2)
        with avg_c3:
            avg_new_qty = st.number_input(
                "Nayi Qty (kितने aur lene hain)", min_value=1, value=int(avg_old_qty) if avg_old_qty else 100,
                step=1, key="avg_new_qty"
            )
        with avg_c4:
            avg_new_price = st.number_input(
                "Naye Shares ka Price (₹)", min_value=0.01,
                value=float(pt_price) if pt_price else 100.0,
                step=0.05, key="avg_new_price",
                help="Jis price pe aur shares lene ka plan hai (default: current price)."
            )

        # ── Calculation ──────────────────────────────────────────────────────────
        avg_total_qty = avg_old_qty + avg_new_qty
        avg_old_inv   = avg_old_qty * avg_old_price
        avg_new_inv   = avg_new_qty * avg_new_price
        avg_total_inv = avg_old_inv + avg_new_inv
        avg_new_avg   = (avg_total_inv / avg_total_qty) if avg_total_qty else 0

        avg_change      = avg_new_avg - avg_old_price if avg_old_qty else None
        avg_cur_price   = float(pt_price) if pt_price else avg_new_price
        avg_breakeven_pct = ((avg_new_avg - avg_cur_price) / avg_cur_price * 100) if avg_cur_price else 0

        avg_color = "#27ae60" if (avg_change is not None and avg_change < 0) else "#e74c3c"
        exceeds_cash_avg = avg_new_inv > st.session_state.pt_cash
        cash_note_avg = (f'<div style="font-size:0.72rem;color:#e74c3c;margin-top:8px;">'
                        f'⚠️ Yeh additional investment (₹{avg_new_inv:,.0f}) aapki available cash '
                        f'(₹{st.session_state.pt_cash:,.0f}) se zyada hai.</div>'
                        if exceeds_cash_avg else "")

        st.markdown(f"""
        <div style="background:#1a1626;border:1px solid #a78bfa55;border-radius:10px;
                    padding:18px 20px;margin-top:10px;">
          <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;">
            <div>
              <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">NAYA AVERAGE PRICE</div>
              <div style="font-size:2.2rem;font-weight:900;color:#a78bfa;line-height:1.1;">₹{avg_new_avg:,.2f}</div>
              <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">
                {f"purana ₹{avg_old_price:,.2f} se {avg_color_word(avg_change)}" if avg_change is not None else "pehli baar khareed rahe ho"}
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">TOTAL QTY (baad mein)</div>
              <div style="font-size:1.3rem;font-weight:700;color:#e8eaf0;">{avg_total_qty:,}</div>
              <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">shares</div>
            </div>
          </div>
          <div style="height:1px;background:#2a2d3a;margin:14px 0;"></div>
          <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;">
            <div>
              <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">ADDITIONAL INVESTMENT</div>
              <div style="font-size:1.15rem;font-weight:700;color:#e8eaf0;">₹{avg_new_inv:,.0f}</div>
              <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">{avg_new_qty:,} shares @ ₹{avg_new_price:,.2f}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">TOTAL INVESTMENT (baad mein)</div>
              <div style="font-size:1.15rem;font-weight:700;color:#e8eaf0;">₹{avg_total_inv:,.0f}</div>
              <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">{avg_total_qty:,} shares @ avg ₹{avg_new_avg:,.2f}</div>
            </div>
          </div>
          <div style="height:1px;background:#2a2d3a;margin:14px 0;"></div>
          <div>
            <div style="font-size:0.62rem;color:#8b90a0;font-weight:700;letter-spacing:.08em;">BREAKEVEN TAK KITNA DOOR</div>
            <div style="font-size:1.15rem;font-weight:700;color:{'#27ae60' if avg_breakeven_pct<=0 else '#e74c3c'};">
              {'Already upar hai' if avg_breakeven_pct<=0 else f'+{avg_breakeven_pct:.2f}%'}
            </div>
            <div style="font-size:0.72rem;color:#8b90a0;margin-top:2px;">
              Current price ₹{avg_cur_price:,.2f} se naye average ₹{avg_new_avg:,.2f} tak
            </div>
          </div>
          {cash_note_avg}
        </div>
        """, unsafe_allow_html=True)

    # ── Zerodha-style 4 tabs: Open / Executed / GTT / Baskets ────────────────
    open_tab, exec_tab, gtt_tab, basket_tab = st.tabs(["📋 Open", "✅ Executed", "⏱ GTT", "🧺 Baskets"])

    # ── OPEN tab (pending orders — paper trading mein sab market order hain so instant execute) ──
    with open_tab:
        st.markdown("""
        <div style="text-align:center;padding:50px 20px;color:#8b90a0;">
          <div style="font-size:3rem;">📋</div>
          <div style="font-size:1.1rem;font-weight:600;color:#e8eaf0;margin-top:12px;">No pending orders</div>
          <div style="font-size:0.82rem;margin-top:6px;">Place an order from your watchlist</div>
        </div>""", unsafe_allow_html=True)

    # ── EXECUTED tab ──────────────────────────────────────────────────────────
    with exec_tab:
        if st.session_state.pt_history:
            total_trades = len(st.session_state.pt_history)
            buy_count    = sum(1 for t in st.session_state.pt_history if t["Action"] == "BUY")
            sell_count   = total_trades - buy_count
            realized_pnl = sum(t["P&L"] for t in st.session_state.pt_history if t.get("P&L") is not None)
            pnl_color    = "#27ae60" if realized_pnl >= 0 else "#e74c3c"

            st.markdown(f"""
            <div style="display:flex;gap:10px;margin:10px 0 14px 0;flex-wrap:wrap;">
              <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:8px;
                          padding:8px 16px;flex:1;text-align:center;">
                <div style="font-size:0.68rem;color:#8b90a0;">TOTAL</div>
                <div style="font-size:1.2rem;font-weight:700;color:#e8eaf0;">{total_trades}</div>
              </div>
              <div style="background:#0d3320;border:1px solid #27ae60;border-radius:8px;
                          padding:8px 16px;flex:1;text-align:center;">
                <div style="font-size:0.68rem;color:#8b90a0;">BUY</div>
                <div style="font-size:1.2rem;font-weight:700;color:#27ae60;">{buy_count}</div>
              </div>
              <div style="background:#330d0d;border:1px solid #e74c3c;border-radius:8px;
                          padding:8px 16px;flex:1;text-align:center;">
                <div style="font-size:0.68rem;color:#8b90a0;">SELL</div>
                <div style="font-size:1.2rem;font-weight:700;color:#e74c3c;">{sell_count}</div>
              </div>
              <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:8px;
                          padding:8px 16px;flex:1;text-align:center;">
                <div style="font-size:0.68rem;color:#8b90a0;">REALISED P&L</div>
                <div style="font-size:1.2rem;font-weight:700;color:{pnl_color};">₹{realized_pnl:+,.0f}</div>
              </div>
            </div>""", unsafe_allow_html=True)

            for trade in reversed(st.session_state.pt_history):
                badge = '<span class="badge-buy">BUY</span>' if trade["Action"] == "BUY" \
                        else '<span class="badge-sell">SELL</span>'
                pnl_html = ""
                if trade.get("P&L") is not None:
                    pc = "#27ae60" if trade["P&L"] >= 0 else "#e74c3c"
                    pnl_html = f'&nbsp;<span style="color:{pc};font-size:0.72rem;font-weight:700;">P&L ₹{trade["P&L"]:+,.2f}</span>'
                st.markdown(f"""
                <div class="order-card">
                  <div class="order-left">
                    <div class="o-ticker">{badge} &nbsp; <b>{trade.get('Name', trade['Ticker'].replace('.NS',''))}</b></div>
                    <div class="o-detail">{trade['Shares']} shares · {trade['Time']}{pnl_html}</div>
                  </div>
                  <div class="order-right">
                    <div class="o-price">₹{trade['Price']:,.2f}</div>
                    <div style="color:#8b90a0;font-size:0.72rem;">₹{trade['Value']:,.0f}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Clear History", key="clear_hist"):
                st.session_state.pt_history = []
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center;padding:50px 20px;color:#8b90a0;">
              <div style="font-size:3rem;">✅</div>
              <div style="font-size:1.1rem;font-weight:600;color:#e8eaf0;margin-top:12px;">No executed orders</div>
              <div style="font-size:0.82rem;margin-top:6px;">Completed trades yahan dikhenge</div>
            </div>""", unsafe_allow_html=True)

    # ── GTT tab — TARGET ORDERS (market hours only, 3:30 PM auto-expire) ───────
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
                    else:
                        st.session_state.pt_targets.append({
                            "ticker": gtt_ticker, "name": gtt_name, "action": "SELL",
                            "qty": gtt_qty, "target_price": gtt_target_price,
                            "placed_date": ist_now().strftime("%Y-%m-%d"),
                            "placed_time": ist_now().strftime("%I:%M %p"),
                        })
                        save_portfolio()
                        st.success(f"✅ SELL target lag gaya: {gtt_qty} × {gtt_name} @ ₹{gtt_target_price:,.2f}")
                        st.rerun()
                else:  # BUY
                    est_cost = gtt_target_price * gtt_qty
                    if est_cost > st.session_state.pt_cash:
                        st.error(f"❌ Balance kam hai! Target hit hone par chahiye ₹{est_cost:,.2f}, hai ₹{st.session_state.pt_cash:,.0f}")
                    else:
                        st.session_state.pt_targets.append({
                            "ticker": gtt_ticker, "name": gtt_name, "action": "BUY",
                            "qty": gtt_qty, "target_price": gtt_target_price,
                            "placed_date": ist_now().strftime("%Y-%m-%d"),
                            "placed_time": ist_now().strftime("%I:%M %p"),
                        })
                        save_portfolio()
                        st.success(f"✅ BUY target lag gaya: {gtt_qty} × {gtt_name} @ ₹{gtt_target_price:,.2f}")
                        st.rerun()

        st.markdown("---")

        # ── Pending targets list ────────────────────────────────────────────────
        today_targets = [t for t in st.session_state.pt_targets
                          if t["placed_date"] == ist_now().strftime("%Y-%m-%d")]

        if today_targets:
            st.markdown('<div class="sec-title">PENDING TARGET ORDERS (aaj ke liye)</div>', unsafe_allow_html=True)
            for idx, t in enumerate(today_targets):
                gq = get_index_quote(t["ticker"])
                live_p = gq[0] if gq else None
                live_str = f"₹{live_p:,.2f}" if live_p is not None else "—"
                badge = '<span class="badge-buy">BUY</span>' if t["action"] == "BUY" else '<span class="badge-sell">SELL</span>'
                st.markdown(f"""
                <div class="order-card">
                  <div class="order-left">
                    <div class="o-ticker">{badge} &nbsp; <b>{t['name']}</b></div>
                    <div class="o-detail">{t['qty']} shares · Target ₹{t['target_price']:,.2f} · Placed {t['placed_time']}</div>
                  </div>
                  <div class="order-right">
                    <div class="o-price">{live_str}</div>
                    <div style="color:#8b90a0;font-size:0.72rem;">live price</div>
                  </div>
                </div>""", unsafe_allow_html=True)
                if st.button("❌ Cancel", key=f"cancel_gtt_{idx}"):
                    st.session_state.pt_targets.remove(t)
                    save_portfolio()
                    st.rerun()
            st.caption("Auto-refresh ON — har 30 second mein price check hoga jab tak market open hai.")

            # ── Auto-refresh: jab tak market open hai aur pending targets hain, ────
            # ── har 30 sec mein page refresh karo taaki target check hota rahe ──────
            if is_market_open():
                time.sleep(30)
                get_index_quote.clear()
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center;padding:50px 20px;color:#8b90a0;">
              <div style="font-size:3rem;">⏱</div>
              <div style="font-size:1.1rem;font-weight:600;color:#e8eaf0;margin-top:12px;">No GTT orders</div>
              <div style="font-size:0.82rem;margin-top:6px;">Good Till Triggered orders yahan dikhenge</div>
            </div>""", unsafe_allow_html=True)

    # ── Baskets tab ───────────────────────────────────────────────────────────
    with basket_tab:
        st.markdown("""
        <div style="text-align:center;padding:50px 20px;color:#8b90a0;">
          <div style="font-size:3rem;">🧺</div>
          <div style="font-size:1.1rem;font-weight:600;color:#e8eaf0;margin-top:12px;">No baskets</div>
          <div style="font-size:0.82rem;margin-top:6px;">Stock baskets yahan dikhenge</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "portfolio":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    DARK_BG   = "#0f1116"
    CARD_BG   = "#1a1d27"
    BORDER    = "#2a2d3a"
    GREEN     = "#27ae60"
    RED       = "#e74c3c"
    BLUE      = "#3b82f6"
    TEXT      = "#e8eaf0"
    MUTED     = "#8b90a0"
    PIE_COLS  = [BLUE,"#a78bfa","#f59e0b","#10b981","#f43f5e",
                 "#06b6d4","#84cc16","#fb923c","#e879f9","#38bdf8"]

    # ── Header with Refresh ───────────────────────────────────────────────────
    pf_h, pf_r = st.columns([5, 1])
    with pf_h:
        st.markdown('<div class="sec-title">MY PORTFOLIO</div>', unsafe_allow_html=True)
    with pf_r:
        if st.button(":material/refresh:", key="portfolio_refresh", help="Prices refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            get_holdings_live_prices.clear()
            st.session_state["_ar_portfolio"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh (portfolio) ─────────────────────────
    _pf_elapsed = time.time() - st.session_state.get("_ar_portfolio", 0)
    if _pf_elapsed >= _AUTO_REFRESH_SECS:
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
            <div class="holdings-grid holdings-header" style="display:grid;grid-template-columns:1.8fr 0.6fr 1.1fr 0.9fr 1fr 1fr 1.1fr 1.1fr;
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
                <div class="holdings-grid" style="display:grid;grid-template-columns:1.8fr 0.6fr 1.1fr 0.9fr 1fr 1fr 1.1fr 1.1fr;
                            gap:8px;padding:12px 14px;
                            background:{bg};
                            border:1px solid {BORDER};border-top:none;
                            border-radius:{border_r};">
                  <div>
                    <div style="font-size:0.88rem;font-weight:700;color:{TEXT};">{r['name']}</div>
                    <div style="font-size:0.68rem;color:{MUTED};margin-top:2px;">Invested ₹{r['inv']:,.0f}</div>
                  </div>
                  <div class="hg-half" data-label="QTY" style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">{r['shares']}</div>
                  </div>
                  <div class="hg-half" data-label="HELD FOR" style="text-align:right;align-self:center;">
                    {held_html}
                  </div>
                  <div class="hg-half" data-label="AVG COST" style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;color:{MUTED};">₹{r['avg']:,.2f}</div>
                  </div>
                  <div class="hg-half" data-label="LTP" style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">₹{r['cur']:,.2f}</div>
                  </div>
                  <div class="hg-half" data-label="CUR. VAL" style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:600;color:{TEXT};">₹{r['cur_v']:,.0f}</div>
                  </div>
                  <div class="hg-full-pnl" data-label="DAY'S P&L" style="text-align:right;align-self:center;">
                    <div style="font-size:0.85rem;font-weight:700;color:{day_c};">
                      {day_ar} ₹{abs(day_p):,.0f}
                    </div>
                    <div style="font-size:0.7rem;color:{day_c};margin-top:1px;">{day_pc:+.2f}%</div>
                  </div>
                  <div class="hg-full-pnl" data-label="TOTAL P&L" style="text-align:right;align-self:center;">
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
                            type="primary", use_container_width=True):
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
                textfont=dict(color=TEXT, size=11),
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
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
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
            st.plotly_chart(pie_fig, use_container_width=True, key="port_pie")

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
    background:{CARD_BG}; border:1px solid {BORDER}; border-radius:10px;
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
    background:{CARD_BG}; border:1px solid {BORDER}; border-radius:10px;
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
            components.html(_animated_block_html, height=360, scrolling=False)

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

            hm_text = [
                f"{r['name']}<br>₹{r['inv']:,.0f} invested<br>{r['pnl_p']:+.2f}% ({'▲' if r['pnl']>=0 else '▼'} ₹{abs(r['pnl']):,.0f})"
                for r in rows
            ]

            heatmap_fig = go.Figure(go.Treemap(
                labels=hm_labels,
                parents=[""] * len(rows),
                values=hm_values,
                text=hm_text,
                texttemplate="<b>%{label}</b><br>%{customdata:+.2f}%",
                customdata=hm_pnl_pct,
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
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                margin=dict(l=4, r=4, t=4, b=4),
                height=420,
            )
            st.plotly_chart(heatmap_fig, use_container_width=True, key="portfolio_heatmap")

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
                    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                    font=dict(color=TEXT, size=11),
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

                st.plotly_chart(pnl_fig, use_container_width=True, key="pnl_graph")

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
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
                        padding:14px 16px;margin-bottom:14px;">
              <div style="font-size:0.65rem;font-weight:800;color:{MUTED};
                          letter-spacing:.1em;margin-bottom:10px;">FILTERS</div>
            </div>""", unsafe_allow_html=True)

            # Quick preset buttons
            preset_cols = st.columns(4)
            with preset_cols[0]:
                if st.button("Last 7 days", key="cal_p7", use_container_width=True):
                    st.session_state.cal_from = (ist_now() - timedelta(days=7)).date()
                    st.session_state.cal_to   = ist_now().date()
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[1]:
                if st.button("Last 30 days", key="cal_p30", use_container_width=True):
                    st.session_state.cal_from = (ist_now() - timedelta(days=30)).date()
                    st.session_state.cal_to   = ist_now().date()
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[2]:
                if st.button("Current FY", key="cal_pfy", use_container_width=True):
                    now_d = ist_now().date()
                    fy_start = date(now_d.year if now_d.month >= 4 else now_d.year - 1, 4, 1)
                    st.session_state.cal_from = fy_start
                    st.session_state.cal_to   = now_d
                    st.session_state.cal_has_applied = True
                    st.rerun()
            with preset_cols[3]:
                if st.button("Prev FY", key="cal_ppfy", use_container_width=True):
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
                if st.button("→ Apply", key="cal_apply", use_container_width=True, type="primary"):
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
                            background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;">
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
                    f'border-radius:10px;padding:16px 18px;">{grid_html}'
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
                              border-radius:10px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">REALISED P&L</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{r_color};">
                      {'+'if total_realised>=0 else ''}₹{abs(total_realised):,.2f}
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:10px;padding:14px;text-align:center;">
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
                              border-radius:10px;padding:14px;text-align:center;">
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
                              border-radius:10px;padding:14px;text-align:center;">
                    <div style="font-size:0.62rem;color:{MUTED};font-weight:700;
                                letter-spacing:.08em;margin-bottom:6px;">NET REALISED P&L</div>
                    <div style="font-size:1.3rem;font-weight:900;color:{net_color};">
                      {'+'if net_realised>=0 else ''}₹{abs(net_realised):,.2f}
                    </div>
                  </div>

                  <div style="background:{CARD_BG};border:1px solid {BORDER};
                              border-radius:10px;padding:14px;text-align:center;">
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
                                  border-radius:10px;padding:14px;display:flex;gap:14px;align-items:center;">
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
                                  border-radius:10px;padding:14px;display:flex;gap:14px;align-items:center;">
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
                stcg_tax = stcg_profit * 0.15
                ltcg_taxable = max(0, ltcg_profit - 125000)   # ₹1.25L exemption
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
                st.markdown(f"""
                <div style="background:{CARD_BG};border:1px solid {BORDER};
                            border-radius:10px;padding:18px 20px;">
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
                            border-radius:10px;padding:24px;text-align:center;color:{MUTED};">
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
            for r in rows:
                tkr_k = r["ticker"].replace(".NS", "")
                sym_unrealised[tkr_k] = r["pnl"]

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
                        up_pct = (up / bv * 100) if bv else 0
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
                gst_on_brok = brokerage * 0.18
            elif trade_type == "Equity Intraday":
                brokerage   = min(order_val * 0.0003, 20.0)   # 0.03% or ₹20 max
                stt         = order_val * 0.00025              # only on sell side
                exch_txn    = order_val * 0.0000345
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00003
                gst_on_brok = brokerage * 0.18
            elif trade_type == "Equity F&O Futures":
                brokerage   = 20.0
                stt         = order_val * 0.0001
                exch_txn    = order_val * 0.000019
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00002
                gst_on_brok = brokerage * 0.18
            else:  # Options
                brokerage   = 20.0
                stt         = order_val * 0.0005   # on sell side (premium)
                exch_txn    = order_val * 0.00053
                sebi        = order_val * 0.000001
                stamp       = order_val * 0.00003
                gst_on_brok = brokerage * 0.18

            dp_charges  = 15.93 if trade_type == "Equity Delivery" else 0.0
            total_buy_charges  = brokerage + exch_txn + sebi + stamp + gst_on_brok
            total_sell_charges = brokerage + stt + exch_txn + sebi + gst_on_brok
            total_charges      = total_buy_charges + total_sell_charges + dp_charges

            breakeven_up   = calc_price + (total_charges / calc_qty)
            breakeven_down = calc_price - (total_charges / calc_qty)
            charges_pct    = (total_charges / order_val) * 100

            # Display
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;padding:16px 20px;margin-top:8px;">
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
                # Normalize: beta 0-3 → score 0-10
                # beta <0.5 = very low risk (score 1-2)
                # beta 0.5-1 = moderate (score 3-5)
                # beta 1-1.5 = high (score 6-7)
                # beta >1.5 = very high (score 8-10)
                raw_score = min(10, max(0, round(port_beta * 100 / 15, 1)))

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
                <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
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
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
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
              <div style="background:{CARD_BG};border:1px solid {wr_color}44;border-radius:10px;
                          padding:14px;text-align:center;border-top:3px solid {wr_color};">
                <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">WIN RATE</div>
                <div style="font-size:2rem;font-weight:900;color:{wr_color};line-height:1.1;">{win_rate}%</div>
                <div style="font-size:0.65rem;color:{wr_color};margin-top:2px;">{wr_label}</div>
              </div>
              <div style="background:{CARD_BG};border:1px solid {pnl_color}44;border-radius:10px;
                          padding:14px;text-align:center;border-top:3px solid {pnl_color};">
                <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">TOTAL P&L</div>
                <div style="font-size:1.4rem;font-weight:900;color:{pnl_color};line-height:1.2;">
                  {'+'if total_pnl>=0 else ''}₹{total_pnl:,.0f}
                </div>
                <div style="font-size:0.65rem;color:{MUTED};margin-top:2px;">{total_closed} trades closed</div>
              </div>
              <div style="background:{CARD_BG};border:1px solid {pf_color}44;border-radius:10px;
                          padding:14px;text-align:center;border-top:3px solid {pf_color};">
                <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">PROFIT FACTOR</div>
                <div style="font-size:2rem;font-weight:900;color:{pf_color};line-height:1.1;">
                  {profit_factor if profit_factor != 999 else "∞"}
                </div>
                <div style="font-size:0.65rem;color:{MUTED};margin-top:2px;">Gross profit / loss</div>
              </div>
              <div style="background:{CARD_BG};border:1px solid #3b82f644;border-radius:10px;
                          padding:14px;text-align:center;border-top:3px solid #3b82f6;">
                <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">AVG HOLD</div>
                <div style="font-size:2rem;font-weight:900;color:#3b82f6;line-height:1.1;">{avg_hold}d</div>
                <div style="font-size:0.65rem;color:{MUTED};margin-top:2px;">Average holding days</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Win/Loss breakdown ────────────────────────────────────────────────
            win_bar  = win_count / total_closed * 100
            loss_bar = loss_count / total_closed * 100
            be_bar   = len(breakevs) / total_closed * 100

            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
                        padding:16px 18px;margin-bottom:10px;">
              <div style="font-size:0.68rem;font-weight:800;color:{MUTED};
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
                {"" if not breakevs else f'<div style="flex:1;min-width:80px;"><div style="font-size:0.65rem;color:{MUTED};margin-bottom:4px;">⚪ Breakeven: {len(breakevs)}</div><div style="background:#13161f;border-radius:4px;height:8px;"><div style="background:{MUTED};width:{be_bar:.1f}%;height:8px;border-radius:4px;"></div></div></div>'}
              </div>
              <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;
                          padding-top:10px;border-top:1px solid {BORDER};">
                <div>
                  <span style="font-size:0.65rem;color:{MUTED};">Avg Profit per Win</span>
                  <span style="font-size:0.82rem;font-weight:700;color:#27ae60;margin-left:8px;">
                    +₹{avg_profit:,.0f}
                  </span>
                </div>
                <div>
                  <span style="font-size:0.65rem;color:{MUTED};">Avg Loss per Loss</span>
                  <span style="font-size:0.82rem;font-weight:700;color:#e74c3c;margin-left:8px;">
                    ₹{avg_loss:,.0f}
                  </span>
                </div>
                <div>
                  <span style="font-size:0.65rem;color:{MUTED};">Avg per Trade</span>
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
                <div style="background:#0d2015;border:1px solid #27ae6055;border-radius:10px;
                            padding:14px 16px;">
                  <div style="font-size:0.65rem;color:#27ae60;font-weight:800;
                              letter-spacing:0.08em;margin-bottom:6px;">🏆 BEST TRADE</div>
                  <div style="font-size:1rem;font-weight:800;color:#e8eaf0;">
                    {best_trade.get('Name', best_trade['Ticker'].replace('.NS',''))}
                  </div>
                  <div style="font-size:1.3rem;font-weight:900;color:#27ae60;">+₹{bp:,.0f}</div>
                  <div style="font-size:0.68rem;color:{MUTED};margin-top:4px;">
                    {best_trade['Shares']} shares @ ₹{best_trade['Price']:,.2f}
                    · {best_trade.get('Time','—')}
                  </div>
                </div>""", unsafe_allow_html=True)
            with bc2:
                wp = worst_trade["P&L"]
                st.markdown(f"""
                <div style="background:#1c0808;border:1px solid #e74c3c55;border-radius:10px;
                            padding:14px 16px;">
                  <div style="font-size:0.65rem;color:#e74c3c;font-weight:800;
                              letter-spacing:0.08em;margin-bottom:6px;">💀 WORST TRADE</div>
                  <div style="font-size:1rem;font-weight:800;color:#e8eaf0;">
                    {worst_trade.get('Name', worst_trade['Ticker'].replace('.NS',''))}
                  </div>
                  <div style="font-size:1.3rem;font-weight:900;color:#e74c3c;">₹{wp:,.0f}</div>
                  <div style="font-size:0.68rem;color:{MUTED};margin-top:4px;">
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
              <div style="font-size:0.78rem;color:{MUTED};padding-top:10px;border-top:1px solid {BORDER};">
                <b style="color:#e8eaf0;">Insight:</b>
                {pf_msg}
                {wr_msg}
              </div>"""

            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
                        padding:14px 18px;margin-top:10px;">
              <div style="font-size:0.68rem;font-weight:800;color:{MUTED};
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
                <div style="background:#1a1d27;border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:{MUTED};">Total BUY Orders</div>
                  <div style="font-size:1.5rem;font-weight:900;color:#3b82f6;">{len(buy_trades)}</div>
                </div>
                <div style="background:#1a1d27;border-radius:8px;padding:10px 14px;text-align:center;flex:1;">
                  <div style="font-size:0.62rem;color:{MUTED};">Closed Trades</div>
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BALANCE
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "balance":
    # ── Header with Refresh button ────────────────────────────────────────────
    bal_h, bal_r = st.columns([5, 1])
    with bal_h:
        st.markdown('<div class="sec-title">MY VIRTUAL BALANCE</div>', unsafe_allow_html=True)
    with bal_r:
        if st.button(":material/refresh:", key="balance_refresh", help="Prices refresh karo"):
            get_index_quote.clear()
            get_batch_quotes.clear()
            st.session_state["_ar_balance"] = time.time()
            st.rerun()

    # ── 60-second background auto-refresh (balance) ───────────────────────────
    _bal_elapsed = time.time() - st.session_state.get("_ar_balance", 0)
    if _bal_elapsed >= _AUTO_REFRESH_SECS:
        get_index_quote.clear()
        get_batch_quotes.clear()
        st.session_state["_ar_balance"] = time.time()
        st.rerun()

    # ── ADD BALANCE SECTION ───────────────────────────────────────────────────
    CARD = "#1a1d27"; BDR = "#2a2d3a"; TXT = "#e8eaf0"; MUT = "#8b90a0"
    G = "#27ae60"; B = "#3b82f6"

    if "show_add_balance" not in st.session_state:
        st.session_state.show_add_balance = False

    add_col, _ = st.columns([2, 3])
    with add_col:
        if st.button("💰 Balance Add Karo", key="toggle_add_bal",
                     use_container_width=True, type="secondary"):
            st.session_state.show_add_balance = not st.session_state.show_add_balance

    if st.session_state.show_add_balance:
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {G};border-radius:10px;
                    padding:16px 18px;margin:10px 0 14px 0;">
          <div style="font-size:0.72rem;color:{MUT};font-weight:600;
                      letter-spacing:.06em;margin-bottom:10px;">💰 VIRTUAL BALANCE ADD KARO</div>
        """, unsafe_allow_html=True)

        # Quick preset amounts
        q1, q2, q3, q4, q5 = st.columns(5)
        presets = [("50K", 50_000), ("1L", 1_00_000), ("5L", 5_00_000),
                   ("10L", 10_00_000), ("1Cr", 1_00_00_000)]
        for col, (label, amt) in zip([q1,q2,q3,q4,q5], presets):
            with col:
                if st.button(f"+₹{label}", key=f"preset_bal_{label}", use_container_width=True):
                    st.session_state.pt_cash += amt
                    save_portfolio()   # ← cash disk pe save karo
                    st.session_state.show_add_balance = False
                    st.success(f"✅ ₹{label} add ho gaya! Available Cash: ₹{st.session_state.pt_cash:,.0f}")
                    st.rerun()

        # Custom amount
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        inp_col, btn_col = st.columns([3, 1])
        with inp_col:
            custom_amt = st.number_input(
                "Ya custom amount likho", min_value=1000, max_value=10_00_00_000,
                value=1_00_000, step=10_000, key="custom_bal_input",
                label_visibility="collapsed",
                format="%d"
            )
        with btn_col:
            if st.button("➕ Add Karo", key="custom_bal_btn",
                          use_container_width=True, type="primary"):
                st.session_state.pt_cash += custom_amt
                save_portfolio()   # ← cash disk pe save karo
                st.session_state.show_add_balance = False
                st.success(f"✅ ₹{custom_amt:,.0f} add ho gaya! Available Cash: ₹{st.session_state.pt_cash:,.0f}")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Calculate totals ──────────────────────────────────────────────────────
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
    pnl_color = "#27ae60" if total_pnl >= 0 else "#e74c3c"
    nw_change = net_worth - 10_000_000
    nw_color  = "#27ae60" if nw_change >= 0 else "#e74c3c"
    nw_sign   = "+" if nw_change >= 0 else ""

    # ── Main Balance Card ─────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d2015,#0d1a2a);
                border:1px solid #27ae60;border-radius:16px;
                padding:28px 32px;margin-bottom:16px;text-align:center;">
        <div style="font-size:0.78rem;color:#8b90a0;letter-spacing:0.1em;margin-bottom:8px;">
            TOTAL NET WORTH
        </div>
        <div style="font-size:2.8rem;font-weight:800;color:#e8eaf0;letter-spacing:-1px;">
            ₹{net_worth:,.0f}
        </div>
        <div style="font-size:1rem;color:{nw_color};margin-top:6px;font-weight:600;">
            {nw_sign}₹{abs(nw_change):,.0f} from ₹1 Crore starting balance
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3 breakdown cards ─────────────────────────────────────────────────────
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(f"""
        <div class="port-card" style="text-align:center;">
            <div class="port-label">💵 AVAILABLE CASH</div>
            <div class="port-val" style="color:#3b82f6;">₹{st.session_state.pt_cash:,.0f}</div>
            <div class="port-sub">Ready to invest</div>
        </div>""", unsafe_allow_html=True)
    with b2:
        st.markdown(f"""
        <div class="port-card" style="text-align:center;">
            <div class="port-label">📦 STOCK VALUE</div>
            <div class="port-val">₹{total_cur_val:,.0f}</div>
            <div class="port-sub">Invested: ₹{total_invested:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with b3:
        pnl_sign = "+" if total_pnl >= 0 else ""
        st.markdown(f"""
        <div class="port-card" style="text-align:center;">
            <div class="port-label">📈 UNREALISED P&L</div>
            <div class="port-val" style="color:{pnl_color};">{pnl_sign}₹{total_pnl:,.0f}</div>
            <div class="port-sub" style="color:{pnl_color};">
                {(total_pnl/total_invested*100) if total_invested else 0:+.2f}% return
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── How to Use Guide ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">HOW TO USE PAPER TRADING</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;padding:20px 24px;">

      <div style="margin-bottom:16px;">
        <div style="color:#3b82f6;font-weight:700;font-size:0.95rem;margin-bottom:6px;">
          📋 Step 1 — Orders Tab mein jaao
        </div>
        <div style="color:#8b90a0;font-size:0.85rem;line-height:1.6;">
          Oopar <b style="color:#e8eaf0;">Orders</b> button pe click karo.
          Wahan koi bhi NSE stock ka ticker daalo (jaise <b style="color:#e8eaf0;">RELIANCE.NS</b>, <b style="color:#e8eaf0;">TCS.NS</b>).
          Kitne shares kharidne hain daalo, phir <b style="color:#27ae60;">BUY</b> karo.
        </div>
      </div>

      <div style="margin-bottom:16px;">
        <div style="color:#3b82f6;font-weight:700;font-size:0.95rem;margin-bottom:6px;">
          💰 Step 2 — Balance check karo
        </div>
        <div style="color:#8b90a0;font-size:0.85rem;line-height:1.6;">
          Yahan <b style="color:#e8eaf0;">Balance</b> tab mein tumhara available cash, invested amount,
          aur P&L dikh raha hai. Shuru mein <b style="color:#27ae60;">₹1,00,00,000 (1 Crore)</b> milte hain.
        </div>
      </div>

      <div style="margin-bottom:16px;">
        <div style="color:#3b82f6;font-weight:700;font-size:0.95rem;margin-bottom:6px;">
          💼 Step 3 — Portfolio check karo
        </div>
        <div style="color:#8b90a0;font-size:0.85rem;line-height:1.6;">
          <b style="color:#e8eaf0;">Portfolio</b> tab mein tumhare saare holdings dikhenge —
          kaunsa stock kitne profit ya loss mein hai live price ke hisaab se.
        </div>
      </div>

      <div style="margin-bottom:16px;">
        <div style="color:#3b82f6;font-weight:700;font-size:0.95rem;margin-bottom:6px;">
          📤 Step 4 — Sell karo jab profit ho
        </div>
        <div style="color:#8b90a0;font-size:0.85rem;line-height:1.6;">
          Orders tab mein wahi ticker daalo, action <b style="color:#e74c3c;">SELL</b> karo.
          Paisa wapas cash balance mein aa jayega. P&L bhi dikhega.
        </div>
      </div>

      <div>
        <div style="color:#3b82f6;font-weight:700;font-size:0.95rem;margin-bottom:6px;">
          🔁 Reset karna ho toh
        </div>
        <div style="color:#8b90a0;font-size:0.85rem;line-height:1.6;">
          Portfolio tab mein neeche <b style="color:#e8eaf0;">Reset Portfolio (₹1 Cr)</b>
          button hai — ek click mein sab reset ho jayega aur phir se ₹1 Crore mil jayenge.
        </div>
      </div>

    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Trade History ─────────────────────────────────────────────────────────
    if st.session_state.pt_history:
        st.markdown('<div class="sec-title">RECENT TRADES</div>', unsafe_allow_html=True)
        for trade in reversed(st.session_state.pt_history[-10:]):
            badge = f'<span class="badge-buy">BUY</span>' if trade["Action"] == "BUY" \
                    else f'<span class="badge-sell">SELL</span>'
            pnl_html = ""
            if trade.get("P&L") is not None:
                pc = "#27ae60" if trade["P&L"] >= 0 else "#e74c3c"
                pnl_html = f'<div style="color:{pc};font-size:0.72rem;font-weight:600;">P&L: ₹{trade["P&L"]:+,.2f}</div>'
            st.markdown(f"""
            <div class="order-card">
              <div class="order-left">
                <div class="o-ticker">{badge} &nbsp; {trade['Ticker'].replace('.NS','')}</div>
                <div class="o-detail">{trade['Shares']} shares · {trade['Time']}</div>
                {pnl_html}
              </div>
              <div class="order-right">
                <div class="o-price">₹{trade['Price']:,.2f}</div>
                <div style="font-size:0.72rem;color:#8b90a0;">Value: ₹{trade['Value']:,.0f}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # P&L REPORT BUTTON + SECTION (Zerodha style)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)

    # P&L Report toggle button
    if "show_pnl_report" not in st.session_state:
        st.session_state.show_pnl_report = False

    if st.button("📊 P&L Report dekho", key="pnl_report_btn", use_container_width=True, type="primary"):
        st.session_state.show_pnl_report = not st.session_state.show_pnl_report

    if st.session_state.show_pnl_report:
        st.markdown('<div class="sec-title" style="margin-top:12px;">P&L REPORT</div>', unsafe_allow_html=True)

        # ── Colour constants (defined here so available in both if/else) ──
        GREEN_PNL = "#27ae60"; RED_PNL = "#e74c3c"; BLUE_PNL = "#3b82f6"
        CARD = "#1a1d27"; BDR = "#2a2d3a"; TXT = "#e8eaf0"; MUT = "#8b90a0"

        if not st.session_state.pt_history:
            st.markdown(f"""
            <div style="text-align:center;padding:40px;color:{MUT};background:{CARD};
                        border:1px solid {BDR};border-radius:10px;">
              <div style="font-size:2.5rem;">📊</div>
              <div style="font-size:1rem;font-weight:600;color:{TXT};margin-top:10px;">
                Koi trade nahi hua abhi tak
              </div>
              <div style="font-size:0.82rem;margin-top:6px;">
                Orders tab se BUY/SELL karo, P&L yahan dikhega
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            import plotly.graph_objects as go

            # ── Parse trades into DataFrame ───────────────────────────────────
            sell_trades = [t for t in st.session_state.pt_history if t["Action"] == "SELL" and t.get("P&L") is not None]
            all_trades  = st.session_state.pt_history

            # Parse dates from trade history (format: "11 Jun 2026 10:30 AM")
            def parse_trade_date(t):
                try:
                    return datetime.strptime(t["Time"], "%d %b %Y %I:%M %p")
                except Exception:
                    return None

            # ── Date Range Filter + View toggle ──────────────────────────────

            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                        padding:14px 18px;margin-bottom:10px;">
              <div style="font-size:0.72rem;color:{MUT};font-weight:600;letter-spacing:.06em;margin-bottom:10px;">
                📅 DATE RANGE FILTER
              </div>""", unsafe_allow_html=True)

            # Find min/max dates from trade history
            all_dates = [parse_trade_date(t) for t in all_trades]
            all_dates = [d for d in all_dates if d is not None]
            if all_dates:
                min_date = min(all_dates).date()
                max_date = max(all_dates).date()
            else:
                min_date = date.today().replace(month=1, day=1)
                max_date = date.today()

            # Quick preset buttons
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

            # Clamp session state values to valid range (avoid out-of-range error)
            clamped_from = max(min_date, min(st.session_state.pnl_date_from, max_date))
            clamped_to   = max(min_date, min(st.session_state.pnl_date_to,   max_date))

            # Manual date pickers
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                date_from = st.date_input(
                    "From Date", value=clamped_from,
                    min_value=min_date, max_value=max_date,
                    key="pnl_from_picker"
                )
                st.session_state.pnl_date_from = date_from
            with dcol2:
                date_to = st.date_input(
                    "To Date", value=clamped_to,
                    min_value=min_date, max_value=max_date,
                    key="pnl_to_picker"
                )
                st.session_state.pnl_date_to = date_to

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Filter trades by selected date range ──────────────────────────
            def in_range(t):
                dt = parse_trade_date(t)
                if dt is None: return False
                return date_from <= dt.date() <= date_to

            filtered_trades = [t for t in all_trades  if in_range(t)]
            filtered_sells  = [t for t in sell_trades if in_range(t)]

            # Show active filter info badge
            total_in_range = len(filtered_trades)
            st.markdown(f"""
            <div style="background:#0d2340;border:1px solid {BLUE_PNL};border-radius:8px;
                        padding:8px 14px;margin-bottom:12px;
                        display:flex;justify-content:space-between;align-items:center;">
              <span style="color:{BLUE_PNL};font-size:0.8rem;font-weight:600;">
                📅 {date_from.strftime('%d %b %Y')} → {date_to.strftime('%d %b %Y')}
              </span>
              <span style="color:{MUT};font-size:0.75rem;">
                {total_in_range} trades is period mein
              </span>
            </div>""", unsafe_allow_html=True)

            # ── View toggle: Month / Year ─────────────────────────────────────
            pnl_view_col, _ = st.columns([2, 3])
            with pnl_view_col:
                pnl_view = st.radio("View by", ["Month-wise", "Year-wise"],
                                    horizontal=True, key="pnl_view_sel",
                                    label_visibility="collapsed")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── OVERALL SUMMARY CARDS (filtered) ─────────────────────────────
            total_realised   = sum(t["P&L"] for t in filtered_sells)
            total_profit_bkd = sum(t["P&L"] for t in filtered_sells if t["P&L"] > 0)
            total_loss_bkd   = sum(t["P&L"] for t in filtered_sells if t["P&L"] < 0)
            # Unrealised P&L (current holdings — always live, not date-filtered)
            unreal_pnl = total_pnl

            # Update sell_trades / all_trades to filtered versions for rest of code
            sell_trades = filtered_sells
            all_trades  = filtered_trades

            rc = GREEN_PNL if total_realised >= 0 else RED_PNL
            uc = GREEN_PNL if unreal_pnl    >= 0 else RED_PNL

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                            padding:14px;text-align:center;">
                  <div style="font-size:0.65rem;color:{MUT};letter-spacing:.06em;">REALISED P&L</div>
                  <div style="font-size:1.25rem;font-weight:800;color:{rc};margin-top:4px;">
                    {'+'if total_realised>=0 else ''}₹{total_realised:,.0f}
                  </div>
                  <div style="font-size:0.72rem;color:{MUT};margin-top:2px;">{len(sell_trades)} closed trades</div>
                </div>""", unsafe_allow_html=True)
            with s2:
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                            padding:14px;text-align:center;">
                  <div style="font-size:0.65rem;color:{MUT};letter-spacing:.06em;">UNREALISED P&L</div>
                  <div style="font-size:1.25rem;font-weight:800;color:{uc};margin-top:4px;">
                    {'+'if unreal_pnl>=0 else ''}₹{unreal_pnl:,.0f}
                  </div>
                  <div style="font-size:0.72rem;color:{MUT};margin-top:2px;">Open holdings</div>
                </div>""", unsafe_allow_html=True)
            with s3:
                st.markdown(f"""
                <div style="background:#0d3320;border:1px solid {GREEN_PNL};border-radius:10px;
                            padding:14px;text-align:center;">
                  <div style="font-size:0.65rem;color:{MUT};letter-spacing:.06em;">PROFIT BOOKED</div>
                  <div style="font-size:1.25rem;font-weight:800;color:{GREEN_PNL};margin-top:4px;">
                    +₹{total_profit_bkd:,.0f}
                  </div>
                  <div style="font-size:0.72rem;color:{MUT};margin-top:2px;">Profitable sells</div>
                </div>""", unsafe_allow_html=True)
            with s4:
                st.markdown(f"""
                <div style="background:#330d0d;border:1px solid {RED_PNL};border-radius:10px;
                            padding:14px;text-align:center;">
                  <div style="font-size:0.65rem;color:{MUT};letter-spacing:.06em;">LOSS BOOKED</div>
                  <div style="font-size:1.25rem;font-weight:800;color:{RED_PNL};margin-top:4px;">
                    ₹{total_loss_bkd:,.0f}
                  </div>
                  <div style="font-size:0.72rem;color:{MUT};margin-top:2px;">Loss-making sells</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── BUILD period-wise P&L data ────────────────────────────────────
            from collections import defaultdict

            period_data = defaultdict(lambda: {"realised": 0.0, "profit": 0.0, "loss": 0.0,
                                                "trades": 0, "buy_val": 0.0, "sell_val": 0.0})

            for t in all_trades:
                dt = parse_trade_date(t)
                if dt is None:
                    continue
                if pnl_view == "Month-wise":
                    key = dt.strftime("%b %Y")   # e.g. "Jun 2026"
                    sort_key = dt.strftime("%Y%m")
                else:
                    key = dt.strftime("%Y")       # e.g. "2026"
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

            # Sort by time
            sorted_periods = sorted(period_data.items(), key=lambda x: x[1].get("_sort", ""))

            if not sorted_periods:
                st.info("Trade history mein dates parse nahi ho payi. Ek baar trade karo.")
            else:
                # ── BAR CHART ────────────────────────────────────────────────
                labels   = [p[0] for p in sorted_periods]
                profits  = [p[1]["profit"]   for p in sorted_periods]
                losses   = [p[1]["loss"]     for p in sorted_periods]
                realiseds= [p[1]["realised"] for p in sorted_periods]

                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(
                    name="Profit Booked", x=labels, y=profits,
                    marker_color=GREEN_PNL,
                    text=[f"₹{v:,.0f}" if v != 0 else "" for v in profits],
                    textposition="inside", textfont=dict(size=10, color="#ffffff"),
                ))
                bar_fig.add_trace(go.Bar(
                    name="Loss Booked", x=labels, y=losses,
                    marker_color=RED_PNL,
                    text=[f"₹{v:,.0f}" if v != 0 else "" for v in losses],
                    textposition="inside", textfont=dict(size=10, color="#ffffff"),
                ))
                bar_fig.add_trace(go.Scatter(
                    name="Net Realised P&L", x=labels, y=realiseds,
                    mode="lines+markers+text",
                    line=dict(color=BLUE_PNL, width=2, dash="dot"),
                    marker=dict(size=8, color=BLUE_PNL),
                    text=[f"₹{v:,.0f}" for v in realiseds],
                    textposition="top center",
                    textfont=dict(size=10, color=BLUE_PNL),
                ))
                bar_fig.update_layout(
                    paper_bgcolor="#0f1116", plot_bgcolor="#0f1116",
                    font=dict(color=TXT, size=11),
                    barmode="relative",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1, font=dict(size=10)),
                    margin=dict(l=60, r=20, t=60, b=60),
                    height=380,
                    xaxis=dict(gridcolor="#1e2130", showgrid=False,
                               tickfont=dict(size=11, color=TXT)),
                    yaxis=dict(gridcolor="#1e2130", showgrid=True,
                               tickprefix="₹", zeroline=True,
                               zerolinecolor="#3a3d4a", zerolinewidth=2,
                               tickfont=dict(size=10, color=TXT),
                               automargin=True),
                    title=dict(text=f"P&L — {pnl_view}", font=dict(size=13, color=MUT), x=0),
                    bargap=0.35,
                )
                st.plotly_chart(bar_fig, use_container_width=True, key="pnl_bar_chart")

                # ── PERIOD TABLE ──────────────────────────────────────────────
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                            overflow:hidden;margin-top:4px;">
                  <!-- Header -->
                  <div style="display:flex;padding:10px 16px;background:#13161f;
                              border-bottom:1px solid {BDR};font-size:0.68rem;
                              color:{MUT};font-weight:600;letter-spacing:.06em;">
                    <div style="flex:2;">PERIOD</div>
                    <div style="flex:2;text-align:right;">REALISED P&L</div>
                    <div style="flex:2;text-align:right;">PROFIT BOOKED</div>
                    <div style="flex:2;text-align:right;">LOSS BOOKED</div>
                    <div style="flex:1.5;text-align:right;">TRADES</div>
                  </div>""", unsafe_allow_html=True)

                for period, d in reversed(sorted_periods):
                    r = d["realised"]; pr = d["profit"]; lo = d["loss"]
                    rc2 = GREEN_PNL if r >= 0 else RED_PNL
                    r_sign = "+" if r >= 0 else ""
                    st.markdown(f"""
                  <div style="display:flex;padding:11px 16px;border-bottom:1px solid {BDR};
                              font-size:0.82rem;align-items:center;">
                    <div style="flex:2;font-weight:700;color:{TXT};">{period}</div>
                    <div style="flex:2;text-align:right;font-weight:700;color:{rc2};">
                      {r_sign}₹{r:,.0f}
                    </div>
                    <div style="flex:2;text-align:right;color:{GREEN_PNL};">
                      {'+'if pr>0 else ''}₹{pr:,.0f}
                    </div>
                    <div style="flex:2;text-align:right;color:{RED_PNL};">
                      ₹{lo:,.0f}
                    </div>
                    <div style="flex:1.5;text-align:right;color:{MUT};">{d['trades']}</div>
                  </div>""", unsafe_allow_html=True)

                # Total row
                tot_r  = sum(d["realised"] for _, d in sorted_periods)
                tot_pr = sum(d["profit"]   for _, d in sorted_periods)
                tot_lo = sum(d["loss"]     for _, d in sorted_periods)
                tot_tr = sum(d["trades"]   for _, d in sorted_periods)
                tot_rc = GREEN_PNL if tot_r >= 0 else RED_PNL
                tot_sign = "+" if tot_r >= 0 else ""
                st.markdown(f"""
                  <div style="display:flex;padding:12px 16px;background:#13161f;
                              font-size:0.85rem;font-weight:700;align-items:center;">
                    <div style="flex:2;color:{TXT};">TOTAL</div>
                    <div style="flex:2;text-align:right;color:{tot_rc};">
                      {tot_sign}₹{tot_r:,.0f}
                    </div>
                    <div style="flex:2;text-align:right;color:{GREEN_PNL};">+₹{tot_pr:,.0f}</div>
                    <div style="flex:2;text-align:right;color:{RED_PNL};">₹{tot_lo:,.0f}</div>
                    <div style="flex:1.5;text-align:right;color:{MUT};">{tot_tr}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

                # ── STOCK-WISE BREAKDOWN ──────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-title">STOCK-WISE P&L BREAKDOWN</div>', unsafe_allow_html=True)

                stock_pnl = defaultdict(lambda: {"profit":0.0,"loss":0.0,"realised":0.0,"sells":0})
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
                    st.markdown(f"""
                    <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;overflow:hidden;">
                      <div style="display:flex;padding:10px 16px;background:#13161f;
                                  border-bottom:1px solid {BDR};font-size:0.68rem;
                                  color:{MUT};font-weight:600;letter-spacing:.06em;">
                        <div style="flex:3;">STOCK</div>
                        <div style="flex:2;text-align:right;">NET P&L</div>
                        <div style="flex:2;text-align:right;">PROFIT</div>
                        <div style="flex:2;text-align:right;">LOSS</div>
                        <div style="flex:1;text-align:right;">SELLS</div>
                      </div>""", unsafe_allow_html=True)

                    for tkr2, sd in sorted(stock_pnl.items(),
                                           key=lambda x: x[1]["realised"], reverse=True):
                        sc = GREEN_PNL if sd["realised"] >= 0 else RED_PNL
                        s_sign = "+" if sd["realised"] >= 0 else ""
                        # Unrealised for this stock
                        h2  = st.session_state.pt_holdings.get(tkr2)
                        if h2:
                            q2    = get_index_quote(tkr2)
                            cp    = q2[0] if q2 else h2["avg_price"]
                            unr2  = (cp - h2["avg_price"]) * h2["shares"]
                            unr_c = GREEN_PNL if unr2 >= 0 else RED_PNL
                            unr_badge = f'<span style="background:#0d2340;color:{BLUE_PNL};border-radius:4px;padding:1px 6px;font-size:0.65rem;margin-left:6px;">Unrealised {unr2:+,.0f}</span>'
                        else:
                            unr_badge = ""
                        st.markdown(f"""
                      <div style="display:flex;padding:11px 16px;border-bottom:1px solid {BDR};
                                  font-size:0.82rem;align-items:center;">
                        <div style="flex:3;">
                          <span style="font-weight:700;color:{TXT};">{sd['name']}</span>
                          {unr_badge}
                        </div>
                        <div style="flex:2;text-align:right;font-weight:700;color:{sc};">
                          {s_sign}₹{sd['realised']:,.0f}
                        </div>
                        <div style="flex:2;text-align:right;color:{GREEN_PNL};">
                          +₹{sd['profit']:,.0f}
                        </div>
                        <div style="flex:2;text-align:right;color:{RED_PNL};">
                          ₹{sd['loss']:,.0f}
                        </div>
                        <div style="flex:1;text-align:right;color:{MUT};">{sd['sells']}</div>
                      </div>""", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="text-align:center;padding:24px;color:{MUT};background:{CARD};
                                border:1px solid {BDR};border-radius:10px;">
                      Koi SELL trade nahi hua abhi. Stock-wise P&L tab dikhega jab sell karo.
                    </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — NEWS
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "news":

    G = "#27ae60"; R = "#e74c3c"; B = "#3b82f6"; Y = "#f59e0b"
    CARD = "#1a1d27"; BDR = "#2a2d3a"; TXT = "#e8eaf0"; MUT = "#8b90a0"

    # ── Header + Refresh ──────────────────────────────────────────────────────
    nh1, nh2 = st.columns([5, 1])
    with nh1:
        st.markdown(f'<div class="sec-title">📰 NEWS & SENTIMENT</div>', unsafe_allow_html=True)
    with nh2:
        if st.button(":material/refresh: Refresh", key="news_refresh", use_container_width=True):
            fetch_mc_market_news.clear()
            fetch_stock_news.clear()
            st.rerun()

    # ── 4 TABS: Market Summary | Stock News | All News | Defence Orders ─────────
    tab_summary, tab_stock, tab_all, tab_defence = st.tabs([
        "🌐 Market Summary", "📌 Stock-wise News", "📋 All News", "🪖 Defence Orders"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB A — MARKET SUMMARY (Aaj kya hua + sentiment overview)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_summary:
        with st.spinner("Market news aa rahi hai..."):
            all_news = fetch_mc_market_news(max_items=30)

        if all_news:
            # Sentiment count karo
            sentiments = [analyse_sentiment(n["title"]) for n in all_news]
            pos_count  = sum(1 for s in sentiments if s[0] == "Positive")
            neg_count  = sum(1 for s in sentiments if s[0] == "Negative")
            neu_count  = sum(1 for s in sentiments if s[0] == "Neutral")
            total      = len(sentiments)
            pos_pct    = int(pos_count / total * 100)
            neg_pct    = int(neg_count / total * 100)

            # Overall sentiment
            if pos_count > neg_count * 1.5:
                overall_label = "Bullish 🟢"
                overall_color = G
                overall_bg    = "#0d2015"
                overall_msg   = "Market aaj positive mood mein hai"
            elif neg_count > pos_count * 1.5:
                overall_label = "Bearish 🔴"
                overall_color = R
                overall_bg    = "#200d0d"
                overall_msg   = "Market mein aaj negativity zyada hai"
            else:
                overall_label = "Neutral ⚪"
                overall_color = MUT
                overall_bg    = CARD
                overall_msg   = "Market mixed signals de raha hai"

            # Overall card
            st.markdown(f"""
            <div style="background:{overall_bg};border:2px solid {overall_color};
                        border-radius:10px;padding:18px 22px;margin-bottom:16px;text-align:center;">
              <div style="font-size:0.72rem;color:{MUT};font-weight:700;letter-spacing:.08em;">
                AAJ KA MARKET SENTIMENT
              </div>
              <div style="font-size:2rem;font-weight:900;color:{overall_color};margin:8px 0;">
                {overall_label}
              </div>
              <div style="font-size:0.85rem;color:{TXT};">{overall_msg}</div>
              <div style="font-size:0.72rem;color:{MUT};margin-top:6px;">
                {total} headlines analyse ki gayi
              </div>
            </div>""", unsafe_allow_html=True)

            # Sentiment bar
            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                        padding:14px 18px;margin-bottom:16px;">
              <div style="font-size:0.72rem;color:{MUT};font-weight:700;margin-bottom:10px;">
                SENTIMENT BREAKDOWN
              </div>
              <div style="display:flex;gap:6px;margin-bottom:8px;">
                <div style="flex:{pos_count};background:{G};height:8px;border-radius:4px 0 0 4px;
                            min-width:4px;"></div>
                <div style="flex:{neu_count};background:{MUT};height:8px;min-width:4px;"></div>
                <div style="flex:{neg_count};background:{R};height:8px;border-radius:0 4px 4px 0;
                            min-width:4px;"></div>
              </div>
              <div style="display:flex;justify-content:space-between;font-size:0.72rem;">
                <span style="color:{G};">🟢 Positive: {pos_count} ({pos_pct}%)</span>
                <span style="color:{MUT};">⚪ Neutral: {neu_count}</span>
                <span style="color:{R};">🔴 Negative: {neg_count} ({neg_pct}%)</span>
              </div>
            </div>""", unsafe_allow_html=True)

            # Top 5 positive + top 5 negative headlines
            pos_news = [(n, s) for n, s in zip(all_news, sentiments) if s[0] == "Positive"][:5]
            neg_news = [(n, s) for n, s in zip(all_news, sentiments) if s[0] == "Negative"][:5]

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""<div style="background:#0d2015;border:1px solid {G}44;
                    border-radius:10px;padding:10px 14px;margin-bottom:8px;
                    font-size:0.72rem;font-weight:700;color:{G};">
                    🟢 Positive Headlines</div>""", unsafe_allow_html=True)
                for n, s in pos_news:
                    st.markdown(f"""
                    <div style="background:{CARD};border:1px solid {BDR};border-radius:8px;
                                padding:10px 12px;margin-bottom:6px;
                                border-left:3px solid {G};">
                      <div style="font-size:0.8rem;color:{TXT};line-height:1.4;">
                        {n['title'][:90]}{'…' if len(n['title'])>90 else ''}
                      </div>
                      <div style="font-size:0.65rem;color:{MUT};margin-top:4px;">
                        🕐 {n['time']} &nbsp;·&nbsp;
                        <a href="{n['link']}" target="_blank"
                           style="color:{B};text-decoration:none;">Padho →</a>
                      </div>
                    </div>""", unsafe_allow_html=True)

            with c2:
                st.markdown(f"""<div style="background:#200d0d;border:1px solid {R}44;
                    border-radius:10px;padding:10px 14px;margin-bottom:8px;
                    font-size:0.72rem;font-weight:700;color:{R};">
                    🔴 Negative Headlines</div>""", unsafe_allow_html=True)
                for n, s in neg_news:
                    st.markdown(f"""
                    <div style="background:{CARD};border:1px solid {BDR};border-radius:8px;
                                padding:10px 12px;margin-bottom:6px;
                                border-left:3px solid {R};">
                      <div style="font-size:0.8rem;color:{TXT};line-height:1.4;">
                        {n['title'][:90]}{'…' if len(n['title'])>90 else ''}
                      </div>
                      <div style="font-size:0.65rem;color:{MUT};margin-top:4px;">
                        🕐 {n['time']} &nbsp;·&nbsp;
                        <a href="{n['link']}" target="_blank"
                           style="color:{B};text-decoration:none;">Padho →</a>
                      </div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.warning("News load nahi hui. Refresh karo.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB B — STOCK-WISE NEWS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_stock:
        wl_names   = [name for _, name in st.session_state.custom_watchlist]
        wl_tickers = [tkr  for tkr, _ in st.session_state.custom_watchlist]

        sel_name   = st.selectbox("Stock chuno", wl_names, key="news_stock_sel")
        sel_ticker = wl_tickers[wl_names.index(sel_name)]

        with st.spinner(f"{sel_name} ki news aa rahi hai..."):
            stock_news = fetch_stock_news(sel_name, max_items=8)

        if stock_news:
            # Stock sentiment
            stock_sentiments = [analyse_sentiment(n["title"]) for n in stock_news]
            sp = sum(1 for s in stock_sentiments if s[0] == "Positive")
            sn = sum(1 for s in stock_sentiments if s[0] == "Negative")
            if sp > sn:   s_lbl, s_clr = f"Positive ({sp}/{len(stock_news)})", G
            elif sn > sp: s_lbl, s_clr = f"Negative ({sn}/{len(stock_news)})", R
            else:         s_lbl, s_clr = "Neutral",                             MUT

            st.markdown(f"""
            <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                        padding:12px 16px;margin-bottom:12px;
                        display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:0.72rem;color:{MUT};">NEWS SENTIMENT</div>
                <div style="font-size:1.1rem;font-weight:800;color:{s_clr};">{s_lbl}</div>
              </div>
              <div style="font-size:0.75rem;color:{MUT};">{len(stock_news)} headlines</div>
            </div>""", unsafe_allow_html=True)

            for n, sent in zip(stock_news, stock_sentiments):
                lbl, clr, _ = sent
                dot = "🟢" if lbl=="Positive" else ("🔴" if lbl=="Negative" else "⚪")
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                            padding:12px 16px;margin-bottom:8px;
                            border-left:3px solid {clr};">
                  <div style="display:flex;align-items:flex-start;gap:8px;">
                    <span style="font-size:0.85rem;margin-top:1px;">{dot}</span>
                    <div style="flex:1;">
                      <div style="font-size:0.88rem;font-weight:600;color:{TXT};
                                  line-height:1.5;">{n['title']}</div>
                      <div style="display:flex;justify-content:space-between;
                                  margin-top:6px;align-items:center;">
                        <div style="display:flex;gap:8px;align-items:center;">
                          <span style="background:#1a1f30;color:{MUT};border-radius:4px;
                                       padding:1px 7px;font-size:0.65rem;">{n['source']}</span>
                          <span style="background:{'#0d2015' if lbl=='Positive' else ('#200d0d' if lbl=='Negative' else '#1a1d27')};
                                       color:{clr};border-radius:4px;
                                       padding:1px 7px;font-size:0.65rem;font-weight:700;">{lbl}</span>
                        </div>
                        <div style="display:flex;gap:10px;align-items:center;">
                          <span style="font-size:0.65rem;color:{MUT};">🕐 {n['time']}</span>
                          <a href="{n['link']}" target="_blank"
                             style="color:{B};font-size:0.72rem;text-decoration:none;
                                    font-weight:600;">Padho →</a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info(f"{sel_name} ke liye news nahi mili. Baad mein try karo.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB C — ALL NEWS (original news feed)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_all:
        with st.spinner("Moneycontrol se news aa rahi hai..."):
            news_items = fetch_mc_market_news(max_items=25)

        if news_items:
            st.markdown(f'<div style="font-size:0.72rem;color:{MUT};margin-bottom:10px;">✅ {len(news_items)} khabrein</div>', unsafe_allow_html=True)
            for n in news_items:
                lbl, clr, _ = analyse_sentiment(n["title"])
                dot = "🟢" if lbl=="Positive" else ("🔴" if lbl=="Negative" else "⚪")
                st.markdown(f"""
                <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                            padding:12px 16px;margin-bottom:7px;
                            border-left:3px solid {clr};">
                  <div style="font-size:0.88rem;font-weight:600;color:{TXT};
                              line-height:1.5;margin-bottom:7px;">
                    {dot} {n['title']}
                  </div>
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="display:flex;gap:8px;">
                      <span style="background:#1a1f30;color:{MUT};border-radius:4px;
                                   padding:1px 7px;font-size:0.65rem;">{n['source']}</span>
                      <span style="color:{clr};font-size:0.65rem;font-weight:700;">{lbl}</span>
                    </div>
                    <div style="display:flex;gap:10px;align-items:center;">
                      <span style="font-size:0.65rem;color:{MUT};">🕐 {n['time']}</span>
                      <a href="{n['link']}" target="_blank"
                         style="color:{B};font-size:0.72rem;text-decoration:none;
                                font-weight:600;">Padho →</a>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="text-align:center;padding:60px 20px;color:{MUT};">
              <div style="font-size:3rem;">📡</div>
              <div style="font-size:1rem;font-weight:700;color:{TXT};margin-top:12px;">
                News load nahi hui</div>
              <div style="font-size:0.82rem;margin-top:6px;">
                Internet check karo ya 🔄 Refresh dabao</div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB D — DEFENCE ORDERS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_defence:
        OLIVE   = "#7c9a3a"
        STEEL   = "#4a7fa5"
        SAFFRON = "#f97316"

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f1f0a,#0a1520);
                    border:1px solid {OLIVE}55;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="font-size:2rem;">🪖</div>
            <div>
              <div style="font-size:1rem;font-weight:900;color:#f0f3ff;">Defence Order Tracker</div>
              <div style="font-size:0.78rem;color:{MUT};margin-top:3px;">
                HAL · MAZDOCK · GRSE · COCHINSHIP · PARAS · ZENTEC — government contracts, ministry orders, navy/army deals
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        _, def_r2 = st.columns([4, 1])
        with def_r2:
            if st.button(":material/refresh: Refresh", key="def_refresh", use_container_width=True):
                fetch_defence_orders.clear()
                st.rerun()

        st.markdown(f"""
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">
          <span style="background:{SAFFRON}22;color:{SAFFRON};border:1px solid {SAFFRON}44;border-radius:20px;padding:3px 11px;font-size:0.68rem;font-weight:700;">💰 Big Order (₹ mentioned)</span>
          <span style="background:{OLIVE}22;color:{OLIVE};border:1px solid {OLIVE}44;border-radius:20px;padding:3px 11px;font-size:0.68rem;font-weight:700;">📋 Contract / Deal</span>
          <span style="background:{STEEL}22;color:{STEEL};border:1px solid {STEEL}44;border-radius:20px;padding:3px 11px;font-size:0.68rem;font-weight:700;">🚢 Navy / Army / IAF</span>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("🪖 Defence orders fetch ho rahe hain..."):
            def_news = fetch_defence_orders(max_items=30)

        if def_news:
            big_orders   = [n for n in def_news if n["is_big"]]
            other_orders = [n for n in def_news if not n["is_big"]]

            if big_orders:
                st.markdown(f'''<div style="font-size:0.7rem;font-weight:800;color:{SAFFRON};letter-spacing:0.1em;margin-bottom:8px;">🔥 BADE ORDERS — ₹ Value Mentioned ({len(big_orders)})</div>''', unsafe_allow_html=True)
                for n in big_orders:
                    stocks_html = "".join([f'<span style="background:#27ae6022;color:#27ae60;border-radius:4px;padding:1px 7px;font-size:0.65rem;font-weight:700;margin-right:4px;">{s}</span>' for s in n["stocks"]])
                    val_badge = f'<span style="background:{SAFFRON}33;color:{SAFFRON};border:1px solid {SAFFRON}66;border-radius:6px;padding:2px 9px;font-size:0.72rem;font-weight:800;">💰 {n["order_val"]}</span>' if n["order_val"] else ""
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#1a1200,#1a1d27);border:1px solid {SAFFRON}55;border-radius:10px;padding:14px 16px;margin-bottom:8px;border-left:4px solid {SAFFRON};">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
                        <div style="font-size:0.9rem;font-weight:700;color:{TXT};line-height:1.5;flex:1;">{n['title']}</div>
                        {val_badge}
                      </div>
                      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                          {stocks_html}
                          <span style="background:#1a1f30;color:{MUT};border-radius:4px;padding:1px 7px;font-size:0.63rem;">{n['source']}</span>
                        </div>
                        <div style="display:flex;gap:10px;align-items:center;">
                          <span style="font-size:0.65rem;color:{MUT};">🕐 {n['time']}</span>
                          <a href="{n['link']}" target="_blank" style="color:{SAFFRON};font-size:0.72rem;font-weight:700;text-decoration:none;">Padho →</a>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

            if other_orders:
                st.markdown(f'''<div style="font-size:0.7rem;font-weight:800;color:{OLIVE};letter-spacing:0.1em;margin:14px 0 8px;">📋 OTHER DEFENCE NEWS ({len(other_orders)})</div>''', unsafe_allow_html=True)
                for n in other_orders:
                    stocks_html = "".join([f'<span style="background:{OLIVE}22;color:{OLIVE};border-radius:4px;padding:1px 7px;font-size:0.65rem;font-weight:700;margin-right:4px;">{s}</span>' for s in n["stocks"]])
                    st.markdown(f"""
                    <div style="background:{CARD};border:1px solid {OLIVE}33;border-radius:10px;padding:13px 16px;margin-bottom:7px;border-left:4px solid {OLIVE};">
                      <div style="font-size:0.88rem;font-weight:600;color:{TXT};line-height:1.5;margin-bottom:8px;">{n['title']}</div>
                      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                          {stocks_html if stocks_html else f'<span style="color:{MUT};font-size:0.65rem;">Defence Sector</span>'}
                          <span style="background:#1a1f30;color:{MUT};border-radius:4px;padding:1px 7px;font-size:0.63rem;">{n['source']}</span>
                        </div>
                        <div style="display:flex;gap:10px;align-items:center;">
                          <span style="font-size:0.65rem;color:{MUT};">🕐 {n['time']}</span>
                          <a href="{n['link']}" target="_blank" style="color:{B};font-size:0.72rem;font-weight:600;text-decoration:none;">Padho →</a>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

            st.markdown(f'''<div style="text-align:center;margin-top:12px;font-size:0.68rem;color:{MUT};">🔄 Auto-refresh: 30 min · Sources: ET, Mint, BS, NDTV Profit, Moneycontrol</div>''', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:center;padding:60px 20px;color:{MUT};">
              <div style="font-size:3rem;">🪖</div>
              <div style="font-size:1rem;font-weight:700;color:{TXT};margin-top:12px;">Abhi koi defence order news nahi mili</div>
              <div style="font-size:0.82rem;margin-top:6px;">🔄 Refresh karo ya thodi der mein check karo</div>
            </div>""", unsafe_allow_html=True)

# TAB 6 — MARKET
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "market":
    col_h, col_r = st.columns([5,1])
    with col_h:
        st.markdown('<div class="sec-title">MAJOR INDICES</div>', unsafe_allow_html=True)
    with col_r:
        if st.button(":material/refresh:", key="mkt_refresh"):
            get_batch_quotes.clear()
            get_index_quote.clear()
            get_nse_top_movers.clear()
            get_market_breadth.clear()
            st.rerun()

    idx_cols = st.columns(3)
    ALL_INDICES = [
        {"name": "NIFTY 50",        "ticker": "^NSEI"},
        {"name": "BANK NIFTY",      "ticker": "^NSEBANK"},
        {"name": "SENSEX",          "ticker": "^BSESN"},
        {"name": "NIFTY IT",        "ticker": "^CNXIT"},
        {"name": "NIFTY MIDCAP 50", "ticker": "^NSEMDCP50"},
        {"name": "INDIA VIX",       "ticker": "^INDIAVIX"},
    ]
    for i, idx in enumerate(ALL_INDICES):
        q = get_index_quote(idx["ticker"])
        with idx_cols[i % 3]:
            if q:
                cur, _, chg, pct = q
                chg_c = "#27ae60" if chg >= 0 else "#e74c3c"
                arrow = "▲" if chg >= 0 else "▼"
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;
                            padding:14px;margin-bottom:8px;text-align:center;">
                  <div style="font-size:0.72rem;color:#8b90a0;">{idx['name']}</div>
                  <div style="font-size:1.2rem;font-weight:700;color:#e8eaf0;">{cur:,.2f}</div>
                  <div style="font-size:0.8rem;color:{chg_c};font-weight:600;">
                    {arrow} {abs(chg):,.2f} ({pct:+.2f}%)
                  </div>
                </div>""", unsafe_allow_html=True)

    # ── Gainers & Losers ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-title" style="margin-top:12px;">TODAY\'S TOP MOVERS</div>',
                unsafe_allow_html=True)

    with st.spinner("Fetching movers…"):
        gainers, losers = get_nse_top_movers()

    g_col, l_col = st.columns(2)
    with g_col:
        st.markdown("""<div style="background:#0d2015;border:1px solid #27ae60;border-radius:10px;
                        padding:8px 14px;margin-bottom:6px;font-weight:700;color:#27ae60;font-size:0.85rem;">
                        🟢 Top Gainers</div>""", unsafe_allow_html=True)
        gainer_html = ""
        for s in gainers:
            gainer_html += f"""<div class="mover-row">
              <div>
                <div class="mover-name">{s['name']}</div>
                <div class="wl-ticker">{s['ticker']}</div>
              </div>
              <div style="text-align:right">
                <div class="mover-price">₹{s['price']:,.2f}</div>
                <div class="mover-pct-g">▲ {s['chg_pct']:+.2f}%</div>
              </div>
            </div>"""
        st.markdown(f'<div style="background:#1a1d27;border-radius:10px;border:1px solid #2a2d3a;">{gainer_html}</div>',
                    unsafe_allow_html=True)

    with l_col:
        st.markdown("""<div style="background:#200d0d;border:1px solid #e74c3c;border-radius:10px;
                        padding:8px 14px;margin-bottom:6px;font-weight:700;color:#e74c3c;font-size:0.85rem;">
                        🔴 Top Losers</div>""", unsafe_allow_html=True)
        loser_html = ""
        for s in losers:
            loser_html += f"""<div class="mover-row">
              <div>
                <div class="mover-name">{s['name']}</div>
                <div class="wl-ticker">{s['ticker']}</div>
              </div>
              <div style="text-align:right">
                <div class="mover-price">₹{s['price']:,.2f}</div>
                <div class="mover-pct-r">▼ {abs(s['chg_pct']):.2f}%</div>
              </div>
            </div>"""
        st.markdown(f'<div style="background:#1a1d27;border-radius:10px;border:1px solid #2a2d3a;">{loser_html}</div>',
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB — MARKET BREADTH (Advance/Decline + Gap Movers — pro-trader signals)
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "breadth":
    col_h, col_r = st.columns([5, 1])
    with col_h:
        st.markdown('<div class="sec-title">📊 MARKET BREADTH</div>', unsafe_allow_html=True)
    with col_r:
        if st.button(":material/refresh:", key="breadth_refresh"):
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
        if st.button(":material/refresh:", key="screener_refresh", help="Data refresh karo"):
            get_screener_data.clear()
            st.rerun()

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("50 stocks ka data fetch ho raha hai... (1-2 min lag sakta hai)"):
        _holding_tickers = tuple(sorted(st.session_state.get("pt_holdings", {}).keys()))
        raw_data = get_screener_data(holding_tickers=_holding_tickers)

    if not raw_data:
        st.error("Data fetch nahi hua. Refresh karo ya thodi der baad try karo.")
        st.stop()

    # ── FILTER PANEL ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                padding:16px 18px;margin-bottom:14px;">
      <div style="font-size:0.72rem;color:{MUT};font-weight:600;
                  letter-spacing:.06em;margin-bottom:12px;">🔍 FILTERS</div>""",
    unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    f4, f5, f6 = st.columns(3)

    with f1:
        all_sectors = sorted(set(s["sector"] for s in raw_data if s["sector"] != "—"))
        sector_sel = st.multiselect("Sector", ["All"] + all_sectors,
                                     default=["All"], key="scr_sector")
    with f2:
        pe_range = st.slider("P/E Ratio", min_value=0.0, max_value=200.0,
                              value=(0.0, 100.0), step=1.0, key="scr_pe")
    with f3:
        change_range = st.slider("Today's Change %",
                                  min_value=-15.0, max_value=15.0,
                                  value=(-15.0, 15.0), step=0.5, key="scr_chg")
    with f4:
        vol_filter = st.selectbox("Volume",
                                   ["Any", "High (>2x avg)", "Very High (>3x avg)", "Low (<0.5x avg)"],
                                   key="scr_vol")
    with f5:
        w52_filter = st.selectbox("52W Position",
                                   ["Any", "Near 52W High (within 5%)",
                                    "Near 52W Low (within 5%)",
                                    "More than 20% below 52W High"],
                                   key="scr_52w")
    with f6:
        sort_by = st.selectbox("Sort By",
                                ["Change % (High→Low)", "Change % (Low→High)",
                                 "P/E (Low→High)", "P/E (High→Low)",
                                 "Volume Ratio (High→Low)",
                                 "Price (High→Low)", "Price (Low→High)",
                                 "% from 52W Low (High→Low)"],
                                key="scr_sort")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── APPLY FILTERS ─────────────────────────────────────────────────────────
    filtered = raw_data[:]

    # Sector
    if sector_sel and "All" not in sector_sel:
        filtered = [s for s in filtered if s["sector"] in sector_sel]

    # P/E
    filtered = [s for s in filtered
                if s["pe"] is None or (pe_range[0] <= s["pe"] <= pe_range[1])]

    # Change %
    filtered = [s for s in filtered
                if change_range[0] <= s["chg_pct"] <= change_range[1]]

    # Volume
    if vol_filter == "High (>2x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] >= 2]
    elif vol_filter == "Very High (>3x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] >= 3]
    elif vol_filter == "Low (<0.5x avg)":
        filtered = [s for s in filtered if s["vol_ratio"] <= 0.5]

    # 52W
    if w52_filter == "Near 52W High (within 5%)":
        filtered = [s for s in filtered if s["from_52h"] >= -5]
    elif w52_filter == "Near 52W Low (within 5%)":
        filtered = [s for s in filtered if s["from_52l"] <= 5]
    elif w52_filter == "More than 20% below 52W High":
        filtered = [s for s in filtered if s["from_52h"] <= -20]

    # Sort
    sort_map = {
        "Change % (High→Low)":        ("chg_pct",    True),
        "Change % (Low→High)":        ("chg_pct",    False),
        "P/E (Low→High)":             ("pe",         False),
        "P/E (High→Low)":             ("pe",         True),
        "Volume Ratio (High→Low)":    ("vol_ratio",  True),
        "Price (High→Low)":           ("price",      True),
        "Price (Low→High)":           ("price",      False),
        "% from 52W Low (High→Low)":  ("from_52l",   True),
    }
    sk, rev = sort_map.get(sort_by, ("chg_pct", True))
    # Put None values last
    filtered.sort(key=lambda x: (x[sk] is None, x[sk] if x[sk] is not None else 0), reverse=rev)

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

    # ── RESULTS TABLE ─────────────────────────────────────────────────────────
    if not filtered:
        st.markdown(f"""<div style="text-align:center;padding:40px;background:{CARD};
            border:1px solid {BDR};border-radius:10px;color:{MUT};">
          <div style="font-size:2rem;">🔍</div>
          <div style="font-size:1rem;color:{TXT};margin-top:10px;font-weight:600;">
            Koi stock match nahi hua
          </div>
          <div style="font-size:0.82rem;margin-top:6px;">
            Filters thoda loosen karo
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        # Table header
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;overflow:hidden;">
          <div style="display:flex;padding:10px 16px;background:#13161f;
                      border-bottom:1px solid {BDR};font-size:0.67rem;
                      color:{MUT};font-weight:600;letter-spacing:.06em;align-items:center;">
            <div style="flex:2.5;">STOCK</div>
            <div style="flex:1.5;text-align:right;">PRICE</div>
            <div style="flex:1.2;text-align:right;">CHG%</div>
            <div style="flex:1;text-align:right;">P/E</div>
            <div style="flex:1;text-align:right;">P/B</div>
            <div style="flex:1.8;text-align:right;">52W HIGH</div>
            <div style="flex:1.8;text-align:right;">52W LOW</div>
            <div style="flex:1.5;text-align:right;">VOL RATIO</div>
            <div style="flex:1.5;text-align:right;">SECTOR</div>
          </div>""", unsafe_allow_html=True)

        for s in filtered:
            chg_c = G if s["chg_pct"] >= 0 else R
            chg_arrow = "▲" if s["chg_pct"] >= 0 else "▼"

            # 52W bar visual
            w52_range = s["w52h"] - s["w52l"]
            w52_pos   = ((s["price"] - s["w52l"]) / w52_range * 100) if w52_range > 0 else 50
            w52_pos   = max(0, min(100, w52_pos))
            w52_bar   = f"""<div style="width:60px;display:inline-block;vertical-align:middle;margin-left:4px;">
              <div style="height:4px;background:#2a2d3a;border-radius:2px;position:relative;">
                <div style="position:absolute;left:{w52_pos:.0f}%;top:-3px;width:2px;height:10px;
                            background:{B};border-radius:1px;transform:translateX(-50%);"></div>
              </div>
            </div>"""

            # Volume badge
            vr = s["vol_ratio"]
            if vr >= 3:   vol_badge = f'<span style="background:#2d0d2d;color:#e879f9;border-radius:4px;padding:1px 6px;font-size:0.62rem;">🔥 {vr:.1f}x</span>'
            elif vr >= 2: vol_badge = f'<span style="background:#0d2340;color:{B};border-radius:4px;padding:1px 6px;font-size:0.62rem;">↑ {vr:.1f}x</span>'
            elif vr < 0.5:vol_badge = f'<span style="background:#2d2000;color:#f59e0b;border-radius:4px;padding:1px 6px;font-size:0.62rem;">↓ {vr:.1f}x</span>'
            else:          vol_badge = f'<span style="color:{MUT};font-size:0.75rem;">{vr:.1f}x</span>'

            pe_disp  = f"{s['pe']:.1f}" if s['pe'] else "—"
            pb_disp  = f"{s['pb']:.2f}" if s['pb'] else "—"
            h_pct    = f'<span style="color:{R};font-size:0.7rem;">({s["from_52h"]:.1f}%)</span>'
            l_pct    = f'<span style="color:{G};font-size:0.7rem;">(+{s["from_52l"]:.1f}%)</span>'

            sector_short = (s["sector"][:12] + "…") if len(s["sector"]) > 13 else s["sector"]

            st.markdown(f"""
          <div style="display:flex;padding:11px 16px;border-bottom:1px solid {BDR};
                      font-size:0.8rem;align-items:center;">
            <div style="flex:2.5;">
              <div style="font-weight:700;color:{TXT};">{s['name']}</div>
              <div style="font-size:0.68rem;color:{MUT};">{s['ticker'].replace('.NS','')}</div>
            </div>
            <div style="flex:1.5;text-align:right;font-weight:700;color:{TXT};">
              ₹{s['price']:,.2f}
            </div>
            <div style="flex:1.2;text-align:right;font-weight:700;color:{chg_c};">
              {chg_arrow} {abs(s['chg_pct']):.2f}%
            </div>
            <div style="flex:1;text-align:right;color:{TXT};">{pe_disp}</div>
            <div style="flex:1;text-align:right;color:{TXT};">{pb_disp}</div>
            <div style="flex:1.8;text-align:right;">
              <span style="color:{TXT};">₹{s['w52h']:,.0f}</span> {h_pct}
            </div>
            <div style="flex:1.8;text-align:right;">
              <span style="color:{TXT};">₹{s['w52l']:,.0f}</span> {l_pct}
            </div>
            <div style="flex:1.5;text-align:right;">{vol_badge}</div>
            <div style="flex:1.5;text-align:right;font-size:0.72rem;color:{MUT};">
              {sector_short}
            </div>
          </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

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

    CARD_BG = "#1a1d27"; BORDER = "#2a2d3a"; TEXT = "#e8eaf0"
    MUTED   = "#8b90a0"; BLUE   = "#3b82f6"; GREEN = "#27ae60"
    RED     = "#e74c3c"; AMBER  = "#f59e0b"; PURPLE = "#a78bfa"

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
                            border-radius:10px;padding:14px;text-align:center;
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
                        border-radius:10px;padding:13px 16px;margin-bottom:7px;
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
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
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

    if not ipos:
        st.markdown(f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
                    padding:16px;text-align:center;color:{MUTED};font-size:0.8rem;">
          Is filter mein abhi koi IPO nahi hai.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB — AI ANALYSIS (Claude API powered)
# ══════════════════════════════════════════════════════════════════════════════
elif tab == "ai_analysis":
    import requests as _req, json as _json

    G = "#27ae60"; R = "#e74c3c"; B = "#3b82f6"; Y = "#f59e0b"
    CARD = "#1a1d27"; BDR = "#2a2d3a"; TXT = "#e8eaf0"; MUT = "#8b90a0"

    if "ai_result"         not in st.session_state: st.session_state.ai_result         = None
    if "ai_ticker_shown"   not in st.session_state: st.session_state.ai_ticker_shown   = ""
    if "ai_stock_data"     not in st.session_state: st.session_state.ai_stock_data     = {}
    if "ai_market_result"  not in st.session_state: st.session_state.ai_market_result  = None

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117 0%,#1a1d27 100%);
                border:1px solid {BDR};border-radius:10px;padding:20px 22px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="font-size:2rem;">🤖</div>
        <div>
          <div style="font-size:1.15rem;font-weight:800;color:{TXT};">AI Stock Analysis</div>
          <div style="font-size:0.8rem;color:{MUT};margin-top:3px;">
            Claude AI powered — Bullish/Bearish signal with full reasoning
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Claude API call (robust) ──────────────────────────────────────────────
    def call_claude_stock_ai(prompt_text):
        try:
            # API key — pehle secrets se lo, nahi toh env variable se
            api_key = ""
            try:
                api_key = st.secrets["ANTHROPIC_API_KEY"]
            except Exception:
                import os
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")

            if not api_key:
                return (
                    "⚠️ API Key nahi mili!\n\n"
                    "Setup karo:\n"
                    "1. Project folder mein `.streamlit/secrets.toml` file banao\n"
                    "2. Usme likho:\n"
                    "   ANTHROPIC_API_KEY = \"sk-ant-xxxxx\"\n"
                    "3. App restart karo\n\n"
                    "API key yahan se lo: https://console.anthropic.com"
                )

            resp = _req.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt_text}]
                },
                timeout=45
            )
            data = resp.json()
            if resp.status_code != 200:
                err = data.get("error", {})
                return f"⚠️ API Error ({resp.status_code}): {err.get('message', str(data))}"
            content = data.get("content", [])
            if not content:
                return f"⚠️ Empty response. Full: {_json.dumps(data)[:300]}"
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block["text"]
            return f"⚠️ No text block. Response: {_json.dumps(data)[:300]}"
        except _req.exceptions.Timeout:
            return "⚠️ Timeout — 45 seconds mein response nahi aaya. Dobara try karo."
        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    # ── Fetch stock data for AI ───────────────────────────────────────────────
    def fetch_ai_stock_data(ticker, name):
        try:
            import yfinance as yf
            t    = yf.Ticker(ticker)
            fi   = t.fast_info
            info = t.info
            hist = t.history(period="30d", interval="1d").dropna(subset=["Close"])
            price    = fi.last_price or 0
            prev     = info.get("previousClose") or price
            chg_pct  = ((price - prev) / prev * 100) if prev else 0
            w52h     = fi.year_high or 0
            w52l     = fi.year_low  or 0
            pe       = info.get("trailingPE")
            pb       = info.get("priceToBook")
            mktcap   = info.get("marketCap", 0)
            sector   = info.get("sector", "—")
            volume   = fi.last_volume or 0
            avg_vol  = info.get("averageVolume") or fi.three_month_average_volume or volume or 1
            vol_ratio= round(volume / avg_vol, 2) if avg_vol else 1
            closes   = list(hist["Close"].round(2).astype(float))[-20:]
            sma5     = round(sum(closes[-5:])  / 5,  2) if len(closes) >= 5  else price
            sma20    = round(sum(closes[-20:]) / 20, 2) if len(closes) >= 20 else price
            gains    = [max(closes[i]-closes[i-1], 0) for i in range(1, len(closes))]
            losses   = [max(closes[i-1]-closes[i], 0) for i in range(1, len(closes))]
            avg_g    = sum(gains[-14:])  / 14 if len(gains)  >= 14 else 0
            avg_l    = sum(losses[-14:]) / 14 if len(losses) >= 14 else 1
            rsi      = round(100 - (100 / (1 + avg_g / avg_l)), 1) if avg_l else 50
            return {
                "name": name, "ticker": ticker.replace(".NS",""),
                "price": round(price,2), "chg_pct": round(chg_pct,2),
                "w52h": round(w52h,2),   "w52l": round(w52l,2),
                "pe": round(pe,1) if pe else None,
                "pb": round(pb,2) if pb else None,
                "mktcap_cr": round(mktcap/1e7, 0) if mktcap else None,
                "sector": sector, "volume": volume,
                "vol_ratio": vol_ratio, "sma5": sma5, "sma20": sma20,
                "rsi": rsi, "closes_20d": closes,
            }
        except Exception as e:
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — STOCK ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="sec-title">STOCK ANALYSIS</div>', unsafe_allow_html=True)

    ANALYSIS_STOCKS = [
        # ── Defence Stocks Only ──
        ("MAZDOCK.NS","Mazagon Dock"),("HAL.NS","HAL"),
        ("GRSE.NS","GRSE"),("COCHINSHIP.NS","Cochin Shipyard"),
        ("DATAPATTNS.NS","Data Patterns"),("ZENTEC.NS","Zen Technologies"),
        ("PARAS.NS","Paras Defence"),("UNIMECH.NS","Unimech Aerospace"),
        ("IDEAFORGE.NS","Ideaforge Tech"),("KRISHNADEF.NS","Krishna Defence"),
        ("BEL.NS","BEL"),("BEML.NS","BEML"),
        ("MIDHANI.NS","Midhani"),("MTAR.NS","MTAR Technologies"),
        ("KPITTECH.NS","KPIT Tech"),("BSE.NS","BSE Ltd"),
        ("ANGELONE.NS","Angel One"),
    ]
    # Watchlist se bhi defence stocks add karo (jo upar nahi hain)
    defence_set = {t for t, _ in ANALYSIS_STOCKS}
    wl_extra = [(t, n) for t, n in st.session_state.custom_watchlist
                if t not in defence_set]
    ALL_AI_STOCKS = ANALYSIS_STOCKS + wl_extra

    sel_col, btn_col = st.columns([3, 1])
    with sel_col:
        stock_choice = st.selectbox(
            "Stock", [f"{n}  ({t.replace('.NS','')})" for t, n in ALL_AI_STOCKS],
            key="ai_stock_sel", label_visibility="collapsed"
        )
    with btn_col:
        analyse_btn = st.button("🤖 Analyse Karo", key="ai_analyse",
                                 use_container_width=True, type="primary")

    chosen_idx             = [f"{n}  ({t.replace('.NS','')})" for t, n in ALL_AI_STOCKS].index(stock_choice)
    chosen_ticker, chosen_name = ALL_AI_STOCKS[chosen_idx]

    if analyse_btn:
        with st.spinner(f"📊 {chosen_name} ka data fetch ho raha hai..."):
            sd = fetch_ai_stock_data(chosen_ticker, chosen_name)
        if not sd:
            st.error("⚠️ Data fetch nahi hua. Thodi der baad dobara try karo.")
        else:
            h52_pct = ((sd['price']-sd['w52h'])/sd['w52h']*100) if sd['w52h'] else 0
            l52_pct = ((sd['price']-sd['w52l'])/sd['w52l']*100) if sd['w52l'] else 0
            prompt = f"""You are an expert Indian stock market analyst. Analyze this NSE stock and give a clear verdict.
Respond in Hinglish (mix of Hindi and English) — friendly and clear, like explaining to a retail investor.

Stock: {sd['name']} ({sd['ticker']})  |  Sector: {sd['sector']}

LIVE DATA:
- Price: ₹{sd['price']} | Today: {sd['chg_pct']:+.2f}%
- 52W High: ₹{sd['w52h']} ({h52_pct:.1f}% from high)
- 52W Low:  ₹{sd['w52l']} (+{l52_pct:.1f}% from low)

TECHNICAL:
- SMA5: ₹{sd['sma5']} | SMA20: ₹{sd['sma20']} | RSI: {sd['rsi']}
- Volume vs Avg: {sd['vol_ratio']}x
- Last 20 closes: {sd['closes_20d']}

FUNDAMENTAL:
- P/E: {sd['pe'] or 'N/A'} | P/B: {sd['pb'] or 'N/A'}
- Market Cap: ₹{f"{sd['mktcap_cr']:,.0f} Cr" if sd['mktcap_cr'] else 'N/A'}

Respond in EXACTLY this format:

VERDICT: [BULLISH 🟢 / BEARISH 🔴 / NEUTRAL 🟡]
CONFIDENCE: [High / Medium / Low]

SUMMARY:
(2-3 lines — kya ho raha hai is stock ke saath, simple language mein)

BULLISH FACTORS:
• point 1
• point 2
• point 3 (if any)

BEARISH FACTORS:
• point 1
• point 2

TECHNICAL VIEW:
(RSI, SMA, volume ke baare mein 2 lines)

WHAT TO WATCH:
(Ek actionable point — next few days mein kya dekhna chahiye)

⚠️ Disclaimer: Sirf educational analysis hai. Investment advice nahi. Apne advisor se zaroor puchho."""

            with st.spinner("🤖 Claude AI analysis kar raha hai..."):
                ai_resp = call_claude_stock_ai(prompt)
            st.session_state.ai_result       = ai_resp
            st.session_state.ai_ticker_shown = chosen_name
            st.session_state.ai_stock_data   = sd

    # ── Show result ───────────────────────────────────────────────────────────
    if st.session_state.ai_result:
        sd   = st.session_state.ai_stock_data
        resp = st.session_state.ai_result

        verdict_c  = B;      verdict_bg = "#0d2340"
        if "BULLISH" in resp.upper():  verdict_c = G; verdict_bg = "#0d2a1a"
        elif "BEARISH" in resp.upper():verdict_c = R; verdict_bg = "#2a0d0d"

        if sd:
            chg_c = G if sd["chg_pct"] >= 0 else R
            chg_a = "▲" if sd["chg_pct"] >= 0 else "▼"
            st.markdown(f"""
            <div style="background:{verdict_bg};border:1px solid {verdict_c};
                        border-radius:10px;padding:14px 18px;margin:12px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="font-size:1.1rem;font-weight:800;color:{TXT};">
                    {st.session_state.ai_ticker_shown}
                  </div>
                  <div style="font-size:0.75rem;color:{MUT};margin-top:2px;">
                    NSE · {sd.get('sector','—')}
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:1.3rem;font-weight:800;color:{TXT};">₹{sd['price']:,.2f}</div>
                  <div style="font-size:0.82rem;font-weight:600;color:{chg_c};">{chg_a} {abs(sd['chg_pct']):.2f}%</div>
                </div>
              </div>
              <div style="display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;">
                <span style="font-size:0.72rem;color:{MUT};">52W H: <b style="color:{TXT};">₹{sd['w52h']:,.0f}</b></span>
                <span style="font-size:0.72rem;color:{MUT};">52W L: <b style="color:{TXT};">₹{sd['w52l']:,.0f}</b></span>
                <span style="font-size:0.72rem;color:{MUT};">P/E: <b style="color:{TXT};">{sd['pe'] or '—'}</b></span>
                <span style="font-size:0.72rem;color:{MUT};">RSI: <b style="color:{TXT};">{sd['rsi']}</b></span>
                <span style="font-size:0.72rem;color:{MUT};">Vol: <b style="color:{TXT};">{sd['vol_ratio']}x</b></span>
                <span style="font-size:0.72rem;color:{MUT};">SMA5: <b style="color:{TXT};">₹{sd['sma5']:,.0f}</b></span>
                <span style="font-size:0.72rem;color:{MUT};">SMA20: <b style="color:{TXT};">₹{sd['sma20']:,.0f}</b></span>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                    padding:20px 22px;line-height:1.75;font-size:0.88rem;
                    color:{TXT};white-space:pre-wrap;">{resp}</div>""",
        unsafe_allow_html=True)

        if st.button("🗑️ Clear", key="ai_clear"):
            st.session_state.ai_result = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — MARKET MOOD
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="sec-title">📊 MARKET MOOD ANALYSIS</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                padding:12px 16px;margin-bottom:12px;font-size:0.82rem;color:{MUT};">
      🇮🇳 Aaj Indian market kaisa dikh raha hai? Nifty, Bank Nifty, sectors —
      sab ka ek saath AI analysis.
    </div>""", unsafe_allow_html=True)

    if st.button("📊 Market Mood Analyse Karo", key="ai_market_btn",
                  type="primary", use_container_width=True):
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
                            "WIPRO.NS","BAJFINANCE.NS","SBIN.NS","ZOMATO.NS","IRCTC.NS"]
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

                with st.spinner("🤖 Market analysis ho rahi hai..."):
                    mkt_resp = call_claude_stock_ai(mkt_prompt)

                st.session_state.ai_market_result = {"response": mkt_resp, "data": mkt_data}
            except Exception as e:
                st.error(f"Market data error: {e}")

    if st.session_state.ai_market_result:
        mres  = st.session_state.ai_market_result
        mresp = mres["response"]
        mdata = mres["data"]

        mood_c = B; mood_bg = "#0d2340"
        if "BULLISH"  in mresp.upper(): mood_c = G; mood_bg = "#0d2a1a"
        elif "BEARISH" in mresp.upper(): mood_c = R; mood_bg = "#2a0d0d"
        elif "VOLATILE"in mresp.upper(): mood_c = Y; mood_bg = "#2a1a00"

        chips = ""
        for iname, d in mdata.items():
            ic = G if d["chg"] >= 0 else R
            ia = "▲" if d["chg"] >= 0 else "▼"
            chips += f"""<div style="background:{CARD};border:1px solid {BDR};border-radius:8px;
              padding:8px 12px;text-align:center;min-width:90px;">
              <div style="font-size:0.62rem;color:{MUT};">{iname}</div>
              <div style="font-size:0.8rem;font-weight:700;color:{TXT};">₹{d['price']:,.0f}</div>
              <div style="font-size:0.7rem;color:{ic};">{ia} {abs(d['chg']):.2f}%</div>
            </div>"""

        st.markdown(f"""
        <div style="background:{mood_bg};border:1px solid {mood_c};border-radius:10px;
                    padding:14px 18px;margin:12px 0;">
          <div style="font-size:0.72rem;color:{MUT};font-weight:600;margin-bottom:8px;">LIVE INDICES</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">{chips}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BDR};border-radius:10px;
                    padding:20px 22px;line-height:1.75;font-size:0.88rem;
                    color:{TXT};white-space:pre-wrap;">{mresp}</div>""",
        unsafe_allow_html=True)

        if st.button("🗑️ Clear Market Analysis", key="ai_mkt_clear"):
            st.session_state.ai_market_result = None
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB — DEFENCE BUDGET & ORDER TRACKER
# ══════════════════════════════════════════════════════════════════════════════
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
            if st.button(_slabel, key=f"sector_pill_{_skey}", use_container_width=True,
                         type="primary" if tab == _skey else "secondary"):
                st.session_state.active_tab = _skey
                st.session_state.last_sector_tab = _skey
                st.rerun()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

if tab == "defence":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    OLIVE  = "#7c9a3a"; STEEL = "#4a7fa5"; SAFFRON = "#f97316"
    CARD_BG = "#1a1d27"; BORDER = "#2a2d3a"; TEXT = "#e8eaf0"; MUTED = "#8b90a0"
    GREEN = "#27ae60"; RED = "#e74c3c"; BLUE = "#3b82f6"; PURPLE = "#a78bfa"

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
          <div style="background:{CARD_BG};border:1px solid {OLIVE}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {OLIVE};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">FY26 TOTAL BUDGET</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">₹6.81L Cr</div>
            <div style="font-size:0.65rem;color:{OLIVE};margin-top:2px;">+{growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {STEEL}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {STEEL};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">FY26 CAPITAL OUTLAY</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">₹2.27L Cr</div>
            <div style="font-size:0.65rem;color:{STEEL};margin-top:2px;">+{cap_growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SAFFRON}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {SAFFRON};">
            <div style="font-size:0.6rem;color:{MUTED};font-weight:700;letter-spacing:0.08em;">% OF GDP</div>
            <div style="font-size:1.1rem;font-weight:900;color:#f0f3ff;">1.9%</div>
            <div style="font-size:0.65rem;color:{SAFFRON};margin-top:2px;">Target: 3% by 2030</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:10px;
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
            paper_bgcolor="#0f1116", plot_bgcolor="#0f1116",
            font=dict(color=TEXT, size=11),
            margin=dict(l=10, r=10, t=30, b=10),
            height=320,
            legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
            xaxis=dict(gridcolor="#1e2130"),
            yaxis=dict(gridcolor="#1e2130", title="₹ Crore"),
            title=dict(text="India Defence Budget FY22–FY26", font=dict(size=13, color=TEXT), x=0.5),
        )
        st.plotly_chart(fig1, use_container_width=True, key="budget_chart")

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
                paper_bgcolor="#0f1116", plot_bgcolor="#0f1116",
                font=dict(color=TEXT, size=11),
                margin=dict(l=10, r=10, t=30, b=10), height=300,
                legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
                xaxis=dict(gridcolor="#1e2130"),
                yaxis=dict(gridcolor="#1e2130", title="Order Book (₹ Cr)"),
                title=dict(text="Company-wise Order Book Trend", font=dict(size=13, color=TEXT), x=0.5),
            )
            st.plotly_chart(fig2, use_container_width=True, key="orders_chart")

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
                paper_bgcolor="#0f1116",
                font=dict(color=TEXT, size=11),
                margin=dict(l=10, r=10, t=30, b=10), height=280,
                title=dict(text="FY26 Order Book Share", font=dict(size=12, color=TEXT), x=0.5),
                showlegend=False,
            )
            st.plotly_chart(fig3, use_container_width=True, key="pie_chart")

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
                            border-radius:10px;padding:14px 16px;margin-bottom:8px;
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
                        border-radius:10px;padding:13px 16px;margin-bottom:8px;
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
                    border:1px solid {OLIVE}55;border-radius:10px;
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
                    border:1px solid #dc262655;border-radius:10px;
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
            if st.button(":material/refresh: Refresh", key="ri_refresh", use_container_width=True):
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
    CARD_BG= "#1a1d27"; BORDER="#2a2d3a"; TEXT="#e8eaf0"; MUTED="#8b90a0"
    GREEN  = "#27ae60"; RED="#e74c3c"; BLUE="#3b82f6"; PURPLE="#a78bfa"

    _bh, _br = st.columns([5,1])
    with _bh:
        st.markdown('<div class="sec-title">BROKING & FINTECH</div>', unsafe_allow_html=True)
    with _br:
        if st.button(":material/refresh:", key="broking_refresh", help="Refresh karo"):
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
          <div style="background:{CARD_BG};border:1px solid {GOLD}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {GOLD};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 TOTAL REVENUE</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['total']//100:,}K Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{growth}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {BLUE}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {BLUE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">RETAIL BROKING</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['retail']//100:,}K Cr</div>
            <div style="font-size:0.72rem;color:{MUTED};">67% of total</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {TEAL}44;border-radius:10px;
                      padding:14px;text-align:center;border-top:3px solid {TEAL};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">DEMAT ACCOUNTS</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['demat_cr']}Cr+</div>
            <div style="font-size:0.72rem;color:{GREEN};">India ka financialization</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:10px;
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
        fig.update_layout(barmode="stack", paper_bgcolor="#0f1116", plot_bgcolor="#0f1116",
                          font=dict(color=TEXT,size=11), height=380,
                          margin=dict(l=60,r=20,t=40,b=40), bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Broking & Fintech Revenue FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor="#1e2130"), yaxis=dict(gridcolor="#1e2130",tickprefix="₹"))
        st.plotly_chart(fig, use_container_width=True)

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
            fig2.update_layout(paper_bgcolor="#0f1116",plot_bgcolor="#0f1116",font=dict(color=TEXT,size=11),
                               height=350,margin=dict(l=60,r=20,t=40,b=40),
                               title=dict(text="Company Revenue FY22–FY26 (₹ Cr)",font=dict(size=13,color=MUTED),x=0),
                               xaxis=dict(gridcolor="#1e2130"),yaxis=dict(gridcolor="#1e2130",tickprefix="₹"))
            st.plotly_chart(fig2, use_container_width=True)

        for co, d in company_data.items():
            vals = [d[y] for y in years]
            gr = round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:10px;
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
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:10px;
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
    CARD_BG= "#1a1d27"; BORDER="#2a2d3a"; TEXT="#e8eaf0"; MUTED="#8b90a0"
    GREEN  = "#27ae60"; RED="#e74c3c"; BLUE="#3b82f6"; PURPLE="#a78bfa"

    _rh, _rr = st.columns([5,1])
    with _rh:
        st.markdown('<div class="sec-title">RENEWABLE ENERGY</div>', unsafe_allow_html=True)
    with _rr:
        if st.button(":material/refresh:", key="renewable_refresh", help="Refresh karo"):
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
            <span style="font-size:0.65rem;color:#8b90a0;margin-left:4px;">Jain Resource Recycling</span>
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
          <div style="background:{CARD_BG};border:1px solid {SOLAR}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {SOLAR};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 TOTAL CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['total_gw']} GW</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['total_gw']-fy22['total_gw'])/fy22['total_gw']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SOLAR}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {SOLAR};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">SOLAR CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['solar_gw']} GW</div>
            <div style="font-size:0.72rem;color:{MUTED};">Target: 500 GW by 2030</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {WIND}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {WIND};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">WIND CAPACITY</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['wind_gw']} GW</div>
            <div style="font-size:0.72rem;color:{MUTED};">Offshore wind starting</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {HYDRO}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {HYDRO};">
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
        fig.update_layout(barmode="stack",paper_bgcolor="#0f1116",plot_bgcolor="#0f1116",
                          font=dict(color=TEXT,size=11),height=380,margin=dict(l=60,r=20,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Renewable Energy Capacity FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor="#1e2130"),yaxis=dict(gridcolor="#1e2130",ticksuffix=" GW"))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        for co, d in company_data.items():
            vals=[d[y] for y in years]; gr=round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:10px;
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
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:10px;
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
    CARD_BG= "#1a1d27"; BORDER="#2a2d3a"; TEXT="#e8eaf0"; MUTED="#8b90a0"
    GREEN  = "#27ae60"; RED="#e74c3c"; BLUE="#3b82f6"; PURPLE="#a78bfa"

    _eh, _er = st.columns([5,1])
    with _eh:
        st.markdown('<div class="sec-title">EV & AUTO TECH</div>', unsafe_allow_html=True)
    with _er:
        if st.button(":material/refresh:", key="ev_refresh", help="Refresh karo"):
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
        "TATAMOTORS":{"FY22":68000,"FY23":84000,"FY24":105000,"FY25":125000,"FY26":145000,
                      "color":AUTO,"sector":"EV OEM","ticker":"TATAMOTORS.NS",
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
          <div style="background:{CARD_BG};border:1px solid {ELEC}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {ELEC};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 EV SALES</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['ev_sales_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['ev_sales_lakh']-fy22['ev_sales_lakh'])/fy22['ev_sales_lakh']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {AUTO}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {AUTO};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">2-WHEELER EV</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['2w_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{MUTED};">Ola, TVS, Bajaj</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {SOFT}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {SOFT};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">4-WHEELER EV</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['4w_lakh']}L units</div>
            <div style="font-size:0.72rem;color:{MUTED};">Tata, MG, Hyundai</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {PURPLE}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {PURPLE};">
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
        fig.update_layout(barmode="stack",paper_bgcolor="#0f1116",plot_bgcolor="#0f1116",
                          font=dict(color=TEXT,size=11),height=380,margin=dict(l=60,r=20,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India EV Sales FY22–FY26 (Lakh Units)",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor="#1e2130"),yaxis=dict(gridcolor="#1e2130"))
        st.plotly_chart(fig, use_container_width=True, key="ev_sector_trend_chart")

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
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:10px;
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
            {"stock":"TATAMOTORS", "event":"Nexon EV 1L deliveries","1d":"+6.2%","1w":"+11.4%","1m":"+22.8%","trigger":"Tata Nexon EV ne 1 lakh deliveries complete ki. Market share 65%.","color":AUTO},
            {"stock":"MINDA",      "event":"EV Component PLI","1d":"+9.8%","1w":"+18.2%","1m":"+38.4%","trigger":"PLI scheme auto components. Minda EV switch + sensor orders 3x.","color":PURPLE},
            {"stock":"EXIDEIND",   "event":"Li-ion Plant Commencement","1d":"+12.1%","1w":"+22.4%","1m":"+48.6%","trigger":"Exide Li-ion battery plant Bangalore. India first indigenous cell mfg.","color":"#fb923c"},
            {"stock":"MOTHERSON",  "event":"EV Wiring Contracts","1d":"+5.1%","1w":"+9.8%","1m":"+18.9%","trigger":"BMW, Stellantis EV wiring harness orders. ₹8,000 Cr contract.","color":SOFT},
        ]
        st.markdown(f'<div style="font-size:0.7rem;font-weight:800;color:{MUTED};letter-spacing:.1em;margin-bottom:12px;">📊 EV POLICY & NEWS PE STOCK REACTION</div>', unsafe_allow_html=True)
        for r in reactions:
            d1c=GREEN if "+" in r["1d"] else RED; d7c=GREEN if "+" in r["1w"] else RED; d30c=GREEN if "+" in r["1m"] else RED
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:10px;
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
    CARD_BG="#1a1d27"; BORDER="#2a2d3a"; TEXT="#e8eaf0"; MUTED="#8b90a0"
    GREEN="#27ae60"; RED="#e74c3c"; BLUE="#3b82f6"; PURPLE="#a78bfa"

    _bnkh, _bnkr = st.columns([5,1])
    with _bnkh:
        st.markdown('<div class="sec-title">BANKING & NBFC</div>', unsafe_allow_html=True)
    with _bnkr:
        if st.button(":material/refresh:", key="banking_refresh", help="Refresh karo"):
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
          <div style="background:{CARD_BG};border:1px solid {BANKBLUE}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {BANKBLUE};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">FY26 CREDIT OUTSTANDING</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">₹{fy26['credit_lakh_cr']}L Cr</div>
            <div style="font-size:0.72rem;color:{GREEN};">+{round((fy26['credit_lakh_cr']-fy22['credit_lakh_cr'])/fy22['credit_lakh_cr']*100,1)}% since FY22</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {NPA}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {NPA};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">GROSS NPA</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['npa_pct']}%</div>
            <div style="font-size:0.72rem;color:{GREEN};">From {fy22['npa_pct']}% in FY22 ↓</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {GREEN}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {GREEN};">
            <div style="font-size:0.62rem;color:{MUTED};font-weight:700;letter-spacing:.08em;">SECTOR ROE</div>
            <div style="font-size:1.5rem;font-weight:900;color:{TEXT};margin:6px 0;">{fy26['roe_pct']}%</div>
            <div style="font-size:0.72rem;color:{GREEN};">Best in a decade</div>
          </div>
          <div style="background:{CARD_BG};border:1px solid {NBFC}44;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {NBFC};">
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
        fig.update_layout(paper_bgcolor="#0f1116",plot_bgcolor="#0f1116",
                          font=dict(color=TEXT,size=11),height=380,margin=dict(l=60,r=60,t=40,b=40),bargap=0.3,
                          legend=dict(orientation="h",y=-0.15),
                          title=dict(text="India Banking Credit Growth & NPA FY22–FY26",font=dict(size=13,color=MUTED),x=0),
                          xaxis=dict(gridcolor="#1e2130"),
                          yaxis=dict(gridcolor="#1e2130",tickprefix="₹",title="Credit (₹L Cr)"),
                          yaxis2=dict(overlaying="y",side="right",title="NPA %",ticksuffix="%",showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        for co, d in company_data.items():
            vals=[d[y] for y in years]; gr=round((vals[-1]-vals[0])/vals[0]*100,1) if vals[0] else 0
            st.markdown(f"""
            <div style="background:{CARD_BG};border:1px solid {d['color']}44;border-radius:10px;
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
            <div style="background:{CARD_BG};border:1px solid {r['color']}44;border-radius:10px;
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

