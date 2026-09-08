"""General-purpose helpers shared across modules."""

import logging
import os
import re
import time
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_DEFAULT_UA = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _DEFAULT_UA, "Accept": "application/json"})


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def retry_get(
    url: str,
    params: Optional[dict] = None,
    retries: int = 3,
    backoff: float = 1.5,
    timeout: int = 15,
    headers: Optional[dict] = None,
) -> Optional[requests.Response]:
    """GET with exponential backoff. Returns None on permanent failure."""
    for attempt in range(retries):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout,
                                headers=headers or {})
            if resp.status_code == 200:
                return resp
            if resp.status_code == 404:
                logger.debug("404 for %s — skipping", url)
                return None
            if resp.status_code == 429:
                wait = backoff * (2 ** attempt)
                logger.warning("Rate-limited on %s — sleeping %.1fs", url, wait)
                time.sleep(wait)
                continue
            logger.warning("HTTP %s for %s", resp.status_code, url)
        except requests.exceptions.Timeout:
            logger.warning("Timeout on %s (attempt %d)", url, attempt + 1)
        except requests.exceptions.RequestException as exc:
            logger.warning("Request error on %s: %s", url, exc)

        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))

    logger.error("All %d attempts failed for %s", retries, url)
    return None


def retry_post(
    url: str,
    json_body: Any = None,
    retries: int = 3,
    backoff: float = 1.5,
    timeout: int = 15,
    headers: Optional[dict] = None,
) -> Optional[requests.Response]:
    for attempt in range(retries):
        try:
            resp = _SESSION.post(url, json=json_body, timeout=timeout,
                                 headers=headers or {})
            if resp.status_code == 200:
                return resp
            if resp.status_code == 404:
                return None
            logger.warning("HTTP %s on POST %s", resp.status_code, url)
        except requests.exceptions.RequestException as exc:
            logger.warning("POST error %s: %s", url, exc)

        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    return None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def clean_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def truncate(text: str, max_chars: int = 300) -> str:
    if not text or len(text) <= max_chars:
        return text or ""
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
