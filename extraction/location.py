"""
Location normalisation and US/remote filtering.
Deterministic string matching — no geocoding API required.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical US locations we care about
# ---------------------------------------------------------------------------

US_LOCATIONS: dict[str, list[str]] = {
    "San Francisco": [
        "san francisco", "sf", "bay area", "sf bay area", "south bay",
        "silicon valley", "palo alto", "mountain view", "sunnyvale",
        "menlo park", "san jose", "santa clara", "redwood city",
        "foster city", "burlingame", "san mateo", "oakland", "emeryville",
    ],
    "New York City": [
        "new york", "nyc", "new york city", "manhattan", "brooklyn",
        "queens", "new york, ny", "ny, ny",
        "ny office", "nyc office", "new york office",
    ],
    "Seattle": [
        "seattle", "bellevue", "redmond", "kirkland", "bothell",
        "seattle, wa", "puget sound", "seattle office",
    ],
    "Boston": [
        "boston", "cambridge, ma", "cambridge ma", "somerville",
        "waltham", "lexington, ma", "boston, ma", "boston office",
        "durham, nc", "durham office", "research triangle",
    ],
    "Los Angeles": [
        "los angeles", "santa monica", "culver city", "west hollywood",
        "los angeles, ca", "southern california", "socal", "pasadena",
        "los angeles office", "la office",
    ],
    "Austin": [
        "austin", "austin, tx", "round rock", "cedar park", "austin office",
    ],
    "Chicago": [
        "chicago", "chicago, il", "evanston", "naperville", "schaumburg",
        "chicago office",
    ],
    "Washington DC": [
        "washington dc", "washington, dc", "d.c.", "arlington, va",
        "arlington va", "bethesda", "mclean", "tysons", "northern virginia",
        "nova", "reston", "herndon", "dc office",
    ],
    "Miami": [
        "miami", "miami, fl", "miami beach", "brickell", "coral gables",
        "fort lauderdale", "boca raton",
    ],
    "San Diego": [
        "san diego", "san diego, ca", "la jolla", "del mar", "san diego office",
    ],
    "Phoenix": [
        "phoenix", "phoenix, az", "scottsdale", "tempe", "mesa, az",
        "chandler, az",
    ],
    "Remote": [
        "remote", "remote us", "remote usa", "work from home", "wfh",
        "fully remote", "100% remote", "us remote", "united states remote",
        "distributed", "remote - united states", "remote (us)",
        "remote, us", "remote, usa", "remote - us", "remote – us",
        "remote - usa", "remote (united states)", "us only", "usa only",
        "anywhere in the us", "anywhere in us",
        # Generic US-wide location strings common in Greenhouse/Lever
        "united states", "nationwide", "national",
        # Ashby tiered remote (company-internal pay bands, still US remote)
        "remote - tier 1", "remote - tier 2", "remote - tier 3",
        "remote – tier 1", "remote – tier 2", "remote – tier 3",
    ],
}

# Flat reverse lookup: normalised alias -> canonical location
_ALIAS_MAP: dict[str, str] = {}
for canonical, aliases in US_LOCATIONS.items():
    for alias in aliases:
        _ALIAS_MAP[alias.lower()] = canonical

# Non-US markers — if these appear alongside ambiguous terms we exclude
_NON_US_MARKERS = re.compile(
    r"\b(united kingdom|uk|london|england|scotland|canada|toronto|vancouver|"
    r"australia|sydney|melbourne|germany|berlin|france|paris|india|bangalore|"
    r"remote\s*-\s*(?!us|usa|united states)|eu remote|europe)\b",
    re.IGNORECASE,
)


def normalize_location(raw: str) -> Optional[str]:
    """
    Map a raw location string to one of our canonical US locations.
    Returns None if not a recognised US target.
    """
    if not raw:
        return None
    text = raw.strip().lower()

    # Reject non-US locations
    if _NON_US_MARKERS.search(text):
        return None

    for alias, canonical in _ALIAS_MAP.items():
        if alias in text:
            return canonical

    return None


def is_us_location(raw: str) -> bool:
    return normalize_location(raw) is not None


def get_canonical_locations() -> list[str]:
    return list(US_LOCATIONS.keys())
