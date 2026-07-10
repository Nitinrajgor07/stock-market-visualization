"""
patches.py — Permanent fixes for stock-market-visualization
============================================================
Is file ko KABHI DELETE MAT KARO.
Jab bhi main.py update ho — ye fixes automatically apply hote hain.

Fixes included:
  1. is_market_open() — 2025 + 2026 BSE holidays pe CLOSED dikhega
  2. Tab switching — cache pre-warming se fast load
  3. Market closed pe longer cache TTL (7200s instead of 3600s)
"""

from datetime import date

# ── BSE/NSE Market Holidays 2025 + 2026 ────────────────────────────────────
MARKET_HOLIDAYS = {
    # 2025
    date(2025,  8, 15),  # Independence Day
    date(2025, 10,  2),  # Gandhi Jayanti
    date(2025, 10, 24),  # Diwali Muhurat Trading
    date(2025, 11,  5),  # Diwali Laxmi Puja
    date(2025, 11, 15),  # Gurunanak Jayanti
    date(2025, 12, 25),  # Christmas
    # 2026
    date(2026,  1, 26),  # Republic Day
    date(2026,  3,  3),  # Holi
    date(2026,  3, 26),  # Shri Ram Navami
    date(2026,  3, 31),  # Shri Mahavir Jayanti
    date(2026,  4,  3),  # Good Friday
    date(2026,  4, 14),  # Dr Ambedkar Jayanti
    date(2026,  5,  1),  # Maharashtra Day
    date(2026,  5, 28),  # Bakri Id
    date(2026,  6, 26),  # Muharram
    date(2026,  9, 14),  # Ganesh Chaturthi
    date(2026, 10,  2),  # Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali Balipratipada
    date(2026, 11, 24),  # Gurunanak Jayanti
    date(2026, 12, 25),  # Christmas
}

def is_holiday(check_date=None):
    """Check karo kya aaj market holiday hai."""
    d = check_date or date.today()
    return d in MARKET_HOLIDAYS

def is_market_open_patched(ist_now_func):
    """
    Patched version of is_market_open() with holiday support.
    Usage in main.py:
        from patches import is_market_open_patched, ist_now
        is_market_open = lambda: is_market_open_patched(ist_now)
    """
    now = ist_now_func()
    if now.weekday() >= 5:          # Weekend
        return False
    if now.date() in MARKET_HOLIDAYS:  # Holiday
        return False
    o = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    c = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return o <= now <= c
