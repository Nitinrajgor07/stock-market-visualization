"""
Stock Symbol Resolver & Validator for Indian Equities (NSE/BSE).
Supports raw tickers, .NS / .BO suffixes, BSE scrip codes, company name search,
corporate action / ticker renames, and market-closed resilience.
"""

import io
import re
import sys
import time
import contextlib
from typing import Dict, Any, List, Optional, Tuple
import yfinance as yf

# Known corporate actions, mergers, and ticker renamings
CORPORATE_ACTION_MAP = {
    "LTIM": "LTM.NS",
    "LTIM.NS": "LTM.NS",
    "LTI": "LTM.NS",
    "MINDTREE": "LTM.NS",
    "ZOMATO": "ETERNAL.NS",
    "ZOMATO.NS": "ETERNAL.NS",
    "TATAMOTORS": "TMPV.NS",
    "TATAMOTORS.NS": "TMPV.NS",
    "CADILAHC": "ZYDUSLIFE.NS",
    "CADILAHC.NS": "ZYDUSLIFE.NS",
    "IDFC": "IDFCFIRSTB.NS",
    "IDFC.NS": "IDFCFIRSTB.NS",
    "MOTHERSUMI": "MOTHERSON.NS",
    "MOTHERSUMI.NS": "MOTHERSON.NS",
    # Prominent BSE Scrip Codes to Yahoo symbols
    "500325": "RELIANCE.BO",
    "500325.BO": "RELIANCE.BO",
    "532540": "TCS.BO",
    "532540.BO": "TCS.BO",
    "500209": "INFY.BO",
    "500209.BO": "INFY.BO",
    "500180": "HDFCBANK.BO",
    "500180.BO": "HDFCBANK.BO",
    "500112": "SBIN.BO",
    "500112.BO": "SBIN.BO",
    "532174": "ICICIBANK.BO",
    "532174.BO": "ICICIBANK.BO",
    "500696": "HINDUNILVR.BO",
    "500696.BO": "HINDUNILVR.BO",
    "500510": "LT.BO",
    "500510.BO": "LT.BO",
    "500520": "M&M.BO",
    "500520.BO": "M&M.BO",
    "540005": "540005.BO",
    "540005.BO": "540005.BO",
}

# Positive resolution cache with TTL to avoid redundant lookups while ensuring
# failed lookups are never permanently cached.
_RESOLVE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECS = 600  # 10 minutes


def _clean_company_name(raw_name: Optional[str], ticker: str) -> str:
    """Format and clean company name retrieved from market metadata."""
    if not raw_name:
        clean_tkr = ticker.split(".")[0]
        return clean_tkr.title() if not clean_tkr.isdigit() else f"BSE {clean_tkr}"

    # Clean typical Yahoo suffixes like "LIMITED", "LTD", "INC"
    name = re.sub(r"\b(LIMITED|LTD\.?|LTD|CORP\.?|CORPORATION)\b", "", raw_name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else raw_name.title()


def _validate_ticker_candidate(ticker: str) -> Optional[Tuple[float, str]]:
    """
    Validate if a ticker exists and has usable market data.
    Works whether market is open or closed (uses metadata & previous close).
    Silences stdout/stderr to avoid yfinance delisted/404 tracebacks.
    Returns (price, company_name) on success, or None on failure.
    """
    try:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            t = yf.Ticker(ticker)

            # 1. Fast metadata check (works outside market hours)
            meta = None
            try:
                meta = t.get_history_metadata()
            except Exception:
                meta = None

            short_name = ""
            price = None

            if meta and isinstance(meta, dict):
                short_name = meta.get("shortName") or meta.get("longName") or ""
                price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")

            # 2. If price still not found, try fast_info
            if price is None or price <= 0:
                try:
                    fi = t.fast_info
                    price = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
                except Exception:
                    pass

            # 3. If price still not found, check short historical window
            if price is None or price <= 0:
                try:
                    hist = t.history(period="5d")
                    if hist is not None and not hist.empty:
                        closes = hist["Close"].dropna()
                        if not closes.empty:
                            price = float(closes.iloc[-1])
                except Exception:
                    pass

            if price is not None and price > 0:
                # Try getting short_name if not available yet
                if not short_name:
                    try:
                        short_name = t.info.get("shortName") or t.info.get("longName") or ""
                    except Exception:
                        pass
                return (float(price), short_name)

            return None
    except Exception:
        return None


def _search_company_symbol(query: str) -> List[str]:
    """
    Use Yahoo Finance Search to find Indian tickers (.NS, .BO) for a company query.
    """
    candidates: List[str] = []
    try:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            search = yf.Search(query, max_results=8)
            quotes = getattr(search, "quotes", []) or []
            for q in quotes:
                sym = q.get("symbol", "").upper()
                if sym.endswith(".NS") or sym.endswith(".BO"):
                    candidates.append(sym)
    except Exception:
        pass
    return candidates


def resolve_and_validate_stock(raw_input: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entrypoint to resolve and validate a stock for Add Stock.

    Args:
        raw_input: Symbol or company name entered by the user.
        custom_name: Optional custom display name provided by user.

    Returns:
        dict with keys:
            - 'success': bool
            - 'ticker': str (e.g. 'RELIANCE.NS', '540005.BO')
            - 'name': str (display name)
            - 'price': float (latest/closing price)
            - 'error': str or None (user-friendly error message)
    """
    if not raw_input or not raw_input.strip():
        return {
            "success": False,
            "ticker": None,
            "name": None,
            "price": None,
            "error": "Please enter a stock symbol or company name."
        }

    query = raw_input.strip()
    cache_key = query.upper()

    # Check short-lived cache
    now = time.time()
    if cache_key in _RESOLVE_CACHE:
        cached_time, cached_res = _RESOLVE_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL_SECS:
            res = dict(cached_res)
            if custom_name and custom_name.strip():
                res["name"] = custom_name.strip()
            return res

    # 1. Normalize and check corporate action mappings
    clean_query = query.upper()
    candidates: List[str] = []

    base_sym = clean_query.split(".")[0] if "." in clean_query else clean_query
    if clean_query in CORPORATE_ACTION_MAP:
        candidates.append(CORPORATE_ACTION_MAP[clean_query])
    elif base_sym in CORPORATE_ACTION_MAP:
        candidates.append(CORPORATE_ACTION_MAP[base_sym])

    # 2. Generate intelligent candidate list
    if clean_query.endswith(".NS"):
        candidates.append(clean_query)
        candidates.append(clean_query.replace(".NS", ".BO"))
    elif clean_query.endswith(".BO"):
        candidates.append(clean_query)
        candidates.append(clean_query.replace(".BO", ".NS"))
    elif clean_query.isdigit() and len(clean_query) in (5, 6):
        # BSE 5 or 6 digit scrip code
        candidates.append(f"{clean_query}.BO")
    else:
        # Standard ticker without suffix: try NSE first, then BSE
        # Replace spaces with hyphens for tickers like BAJAJ AUTO -> BAJAJ-AUTO
        normalized_ticker = re.sub(r"\s+", "-", clean_query)
        candidates.append(f"{normalized_ticker}.NS")
        candidates.append(f"{normalized_ticker}.BO")

    # 3. Test the generated direct candidates
    tested_candidates = set()
    for cand in candidates:
        if cand in tested_candidates:
            continue
        tested_candidates.add(cand)

        res = _validate_ticker_candidate(cand)
        if res:
            price, raw_name = res
            display_name = custom_name.strip() if custom_name and custom_name.strip() else _clean_company_name(raw_name, cand)
            result = {
                "success": True,
                "ticker": cand,
                "name": display_name,
                "price": price,
                "error": None
            }
            _RESOLVE_CACHE[cache_key] = (now, result)
            return result

    # 4. If direct candidates failed, try company name search
    search_candidates = _search_company_symbol(query)
    for cand in search_candidates:
        if cand in tested_candidates:
            continue
        tested_candidates.add(cand)

        res = _validate_ticker_candidate(cand)
        if res:
            price, raw_name = res
            display_name = custom_name.strip() if custom_name and custom_name.strip() else _clean_company_name(raw_name, cand)
            result = {
                "success": True,
                "ticker": cand,
                "name": display_name,
                "price": price,
                "error": None
            }
            _RESOLVE_CACHE[cache_key] = (now, result)
            return result

    # 5. Friendly error handling
    # Check if this was a known ticker that may be inactive or delisted
    if any(cand.startswith("LTIM.") for cand in candidates):
        err_msg = "This symbol appears inactive or changed. Try LTM or its BSE code 540005."
    elif clean_query.isalpha() and len(clean_query) <= 12:
        err_msg = f"Stock '{query}' not found. Please check the symbol or try with exchange suffix (e.g. .NS or .BO)."
    else:
        err_msg = "Stock not found. Please check the symbol/company name."

    return {
        "success": False,
        "ticker": None,
        "name": None,
        "price": None,
        "error": err_msg
    }
