"""
Deterministic salary extraction via regex.
No LLM inference — parse only explicit dollar figures in job text.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MIN_PLAUSIBLE = 50_000    # sanity floor — ignore "$80 / hour" mis-parses
MAX_PLAUSIBLE = 2_000_000  # sanity ceiling

# ---------------------------------------------------------------------------
# Regex patterns  (ordered: most specific first)
# ---------------------------------------------------------------------------

_CURRENCY_PAT = r"(?:USD\s*)?\$"

_PATTERNS: list[re.Pattern] = [
    # $150,000 – $200,000  /  $150k – $200k  /  150,000-200,000
    re.compile(
        rf"{_CURRENCY_PAT}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*k?\s*"
        r"(?:[-–—]|to)\s*"
        rf"{_CURRENCY_PAT}?\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*k?",
        re.IGNORECASE,
    ),
    # base salary of $180,000
    re.compile(
        r"(?:base\s+salary|base\s+pay|annual\s+salary|base\s+compensation)"
        rf"\s+(?:of\s+)?{_CURRENCY_PAT}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*k?",
        re.IGNORECASE,
    ),
    # total compensation of $250,000  /  OTE $250k  /  TC $250,000
    re.compile(
        r"(?:total\s+compensation|total\s+comp|compensation|ote|tc)"
        rf"\s+(?:of\s+)?{_CURRENCY_PAT}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*k?",
        re.IGNORECASE,
    ),
    # $200,000 per year / annually / /year
    re.compile(
        rf"{_CURRENCY_PAT}\s*(\d{{1,3}}(?:,\d{{3}})*|\d+)\s*k?"
        r"\s*(?:per\s+year|annually|\/\s*year|\/\s*yr|per\s+annum)",
        re.IGNORECASE,
    ),
    # salary range: 150000 to 200000
    re.compile(
        r"salary\s+(?:range\s+)?(?:of\s+)?"
        r"(\d{1,3}(?:,\d{3})*|\d{5,7})"
        r"\s*(?:[-–—]|to)\s*"
        r"(\d{1,3}(?:,\d{3})*|\d{5,7})",
        re.IGNORECASE,
    ),
]

# Hourly-rate pattern — detect and convert (assume 2080 hours/year)
_HOURLY_PAT = re.compile(
    r"\$\s*(\d{2,4})\s*(?:[-–]?\s*\$\s*(\d{2,4}))?\s*"
    r"(?:per\s+hour|/\s*hour|/\s*hr|hourly)",
    re.IGNORECASE,
)


def _clean_num(raw: str) -> Optional[int]:
    """Convert '150,000' or '150k' or '150' to integer annual salary."""
    if not raw:
        return None
    raw = raw.replace(",", "").strip()
    try:
        val = int(float(raw))
    except ValueError:
        return None
    # Bare two/three-digit number treated as thousands (e.g. "150" → 150_000)
    if val < 1_000:
        val *= 1_000
    if not (MIN_PLAUSIBLE <= val <= MAX_PLAUSIBLE):
        return None
    return val


def _clean_hourly(raw: str) -> Optional[int]:
    """Parse a raw hourly rate string — no k-multiplier applied."""
    if not raw:
        return None
    try:
        val = int(float(raw.replace(",", "").strip()))
    except ValueError:
        return None
    if not (10 <= val <= 500):  # sanity bounds for $/hr
        return None
    return val


def parse_salary(text: str) -> dict:
    """
    Return {salary_min, salary_max, salary_raw} parsed from job text.
    All values are annualised integers in USD.
    Returns empty dict if no salary found.
    """
    if not text:
        return {}

    # Try hourly first (uses _clean_hourly — no k-multiplier)
    m = _HOURLY_PAT.search(text)
    if m:
        lo = _clean_hourly(m.group(1))
        hi = _clean_hourly(m.group(2)) if m.group(2) else None
        if lo:
            lo_annual = lo * 2080
            hi_annual = hi * 2080 if hi else None
            if lo_annual >= MIN_PLAUSIBLE:
                return {
                    "salary_min": lo_annual,
                    "salary_max": hi_annual or lo_annual,
                    "salary_raw": m.group(0).strip(),
                }

    for pat in _PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        groups = [g for g in m.groups() if g is not None]
        if len(groups) >= 2:
            lo = _clean_num(groups[0])
            hi = _clean_num(groups[1])
            if lo and hi and lo <= hi:
                return {"salary_min": lo, "salary_max": hi, "salary_raw": m.group(0).strip()}
        elif len(groups) == 1:
            val = _clean_num(groups[0])
            if val:
                return {"salary_min": val, "salary_max": val, "salary_raw": m.group(0).strip()}

    return {}


def meets_salary_threshold(salary_dict: dict, threshold: int = 150_000) -> bool:
    """
    True if at least one of salary_min / salary_max is at or above threshold.
    Returns False when no salary data is present.
    """
    lo = salary_dict.get("salary_min") or 0
    hi = salary_dict.get("salary_max") or 0
    return max(lo, hi) >= threshold


def format_salary(salary_min: Optional[int], salary_max: Optional[int]) -> str:
    """Human-readable salary string for display."""
    if not salary_min and not salary_max:
        return "Not listed"
    if salary_min == salary_max or not salary_max:
        return f"${salary_min:,.0f}"
    return f"${salary_min:,.0f} – ${salary_max:,.0f}"
