"""
Stock Symbol Resolver & Validator for Indian Equities (NSE/BSE).
Supports raw tickers, .NS / .BO suffixes, BSE scrip codes, company name search,
corporate action / ticker renames, and market-closed resilience.
"""

import io
import re
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, Any, List, Optional, Tuple
import yfinance as yf

# Silence yfinance logging thread-safely
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

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
    "540005": "LTM.BO",
    "540005.BO": "LTM.BO",
    "LTIMINDTREE": "LTM.NS",
    "LTIMINDTREE.NS": "LTM.NS",
    "532215": "AXISBANK.BO",
    "532215.BO": "AXISBANK.BO",
    "500820": "ASIANPAINT.BO",
    "500820.BO": "ASIANPAINT.BO",
    "532454": "BHARTIARTL.BO",
    "532454.BO": "BHARTIARTL.BO",
    "500247": "KOTAKBANK.BO",
    "500247.BO": "KOTAKBANK.BO",
    "532500": "MARUTI.BO",
    "532500.BO": "MARUTI.BO",
    "500570": "TMPV.BO",
    "500570.BO": "TMPV.BO",
    "500182": "HEROMOTOCO.BO",
    "500182.BO": "HEROMOTOCO.BO",
    "500470": "TATASTEEL.BO",
    "500470.BO": "TATASTEEL.BO",
    "532755": "TECHM.BO",
    "532755.BO": "TECHM.BO",
    "507685": "WIPRO.BO",
    "507685.BO": "WIPRO.BO",
    "532538": "ULTRACEMCO.BO",
    "532538.BO": "ULTRACEMCO.BO",
    "500312": "ONGC.BO",
    "500312.BO": "ONGC.BO",
    "500875": "ITC.BO",
    "500875.BO": "ITC.BO",
    "532555": "NTPC.BO",
    "532555.BO": "NTPC.BO",
    "500034": "BAJFINANCE.BO",
    "500034.BO": "BAJFINANCE.BO",
    "500114": "TITAN.BO",
    "500114.BO": "TITAN.BO",
}

# Positive resolution cache with TTL to avoid redundant lookups while ensuring
# failed lookups are never permanently cached.
_RESOLVE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECS = 600  # 10 minutes


def _clean_company_name(raw_name: Optional[str], ticker: str) -> str:
    """Format and clean company name retrieved from market metadata."""
    if not raw_name:
        clean_tkr = ticker.split(".")[0]
        if clean_tkr == "LTM":
            return "LTIMindtree"
        return clean_tkr.title() if not clean_tkr.isdigit() else f"BSE {clean_tkr}"

    # Clean typical Yahoo suffixes like "LIMITED", "LTD", "INC"
    name = re.sub(r"\b(LIMITED|LTD|CORP|CORPORATION|INC)\b\.?", "", raw_name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s+", " ", name).strip(" .-")
    if ticker.startswith("LTM.") or name.upper() == "LTM":
        return "LTIMindtree"
    return name.title() if name else raw_name.title()


def _validate_ticker_candidate(ticker: str) -> Optional[Tuple[float, str]]:
    """
    Validate if a ticker exists and has usable market data.
    Works whether market is open or closed (uses metadata & previous close).
    Uses fast, single-call validation without slow quoteSummary/t.info calls.
    Returns (price, company_name) on success, or None on failure.
    """
    try:
        t = yf.Ticker(ticker)
        short_name = ""
        price = None

        # 1. Fast metadata check (works outside market hours)
        try:
            meta = t.get_history_metadata()
            if meta and isinstance(meta, dict):
                short_name = meta.get("shortName") or meta.get("longName") or ""
                price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
        except Exception:
            meta = None

        # 2. If price still not found, try fast_info
        if price is None or price <= 0:
            try:
                fi = t.fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
            except Exception:
                pass

        # 3. Fall back to 5d history only if price is still missing
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
        search = yf.Search(query, max_results=8)
        quotes = getattr(search, "quotes", []) or []
        for q in quotes:
            sym = q.get("symbol", "").upper()
            if sym.endswith(".NS") or sym.endswith(".BO"):
                candidates.append(sym)
            elif q.get("exchange") in ("NSI", "NSE") and not sym.endswith(".NS"):
                candidates.append(f"{sym}.NS")
            elif q.get("exchange") == "BSE" and not sym.endswith(".BO"):
                candidates.append(f"{sym}.BO")
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
    now = time.time()
    deadline = now + 20.0

    # Check short-lived cache
    if cache_key in _RESOLVE_CACHE:
        cached_time, cached_res = _RESOLVE_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL_SECS:
            res = dict(cached_res)
            if custom_name and custom_name.strip():
                res["name"] = custom_name.strip()
            return res

    # 1. Normalize and check corporate action mappings
    clean_query = query.upper()
    compact_query = clean_query.replace(" ", "").replace("-", "")
    candidates: List[str] = []

    target_sym = None
    base_sym = clean_query.split(".")[0] if "." in clean_query else clean_query
    if clean_query in CORPORATE_ACTION_MAP:
        target_sym = CORPORATE_ACTION_MAP[clean_query]
    elif compact_query in CORPORATE_ACTION_MAP:
        target_sym = CORPORATE_ACTION_MAP[compact_query]
    elif base_sym in CORPORATE_ACTION_MAP:
        target_sym = CORPORATE_ACTION_MAP[base_sym]

    if target_sym:
        candidates.append(target_sym)
        if target_sym.endswith(".BO"):
            candidates.append(target_sym.replace(".BO", ".NS"))
        elif target_sym.endswith(".NS"):
            candidates.append(target_sym.replace(".NS", ".BO"))

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
        normalized_ticker = re.sub(r"\s+", "-", clean_query)
        candidates.append(f"{normalized_ticker}.NS")
        candidates.append(f"{normalized_ticker}.BO")

    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    should_search = not (clean_query.isdigit() or clean_query.endswith(".NS") or clean_query.endswith(".BO"))

    winner = None

    # Parallel Execution Pool (~4 workers)
    with ThreadPoolExecutor(max_workers=4) as executor:
        search_future: Optional[Future] = None
        if should_search:
            search_future = executor.submit(_search_company_symbol, query)

        # 3. Test direct candidates in parallel
        cand_futures = {executor.submit(_validate_ticker_candidate, c): c for c in unique_candidates}
        valid_results: Dict[str, Tuple[float, str]] = {}

        for future in as_completed(cand_futures, timeout=max(0.1, deadline - time.time())):
            c = cand_futures[future]
            try:
                res = future.result()
                if res:
                    valid_results[c] = res
                    # If this is .NS and primary candidate, immediate win
                    if c.endswith(".NS") and unique_candidates.index(c) == 0:
                        winner = (c, res)
                        break
            except Exception:
                pass

        if not winner and valid_results:
            # Prefer .NS if both .NS and .BO are valid
            for c in unique_candidates:
                if c in valid_results and c.endswith(".NS"):
                    winner = (c, valid_results[c])
                    break
            if not winner:
                for c in unique_candidates:
                    if c in valid_results:
                        winner = (c, valid_results[c])
                        break

        # 4. If direct candidates failed, process search results
        if not winner and search_future is not None:
            rem_time = max(0.1, deadline - time.time())
            try:
                search_results = search_future.result(timeout=rem_time) or []
            except Exception:
                search_results = []

            top_search = []
            for sc in search_results:
                if sc not in seen:
                    seen.add(sc)
                    top_search.append(sc)
                if len(top_search) >= 4:
                    break

            if top_search:
                s_futures = {executor.submit(_validate_ticker_candidate, sc): sc for sc in top_search}
                s_valid: Dict[str, Tuple[float, str]] = {}
                for future in as_completed(s_futures, timeout=max(0.1, deadline - time.time())):
                    sc = s_futures[future]
                    try:
                        res = future.result()
                        if res:
                            s_valid[sc] = res
                            if sc.endswith(".NS"):
                                winner = (sc, res)
                                break
                    except Exception:
                        pass

                if not winner and s_valid:
                    for sc in top_search:
                        if sc in s_valid and sc.endswith(".NS"):
                            winner = (sc, s_valid[sc])
                            break
                    if not winner:
                        for sc in top_search:
                            if sc in s_valid:
                                winner = (sc, s_valid[sc])
                                break

    if time.time() >= deadline:
        return {
            "success": False,
            "ticker": None,
            "name": None,
            "price": None,
            "error": "Yahoo Finance is taking too long to respond. Please try again."
        }

    if winner:
        cand, (price, raw_name) = winner
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
    if any(c.startswith("LTIM.") for c in unique_candidates):
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
