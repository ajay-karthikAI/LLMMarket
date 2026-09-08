"""
Lever public Postings API client.
Docs: https://help.lever.co/hc/en-us/articles/206460965
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from utils.helpers import retry_get, clean_html

logger = logging.getLogger(__name__)

_BASE = "https://api.lever.co/v0/postings/{slug}"


def _ms_to_date(ms: Optional[int]) -> Optional[str]:
    if not ms:
        return None
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return None


def fetch_lever(company_name: str, slug: str) -> list[dict]:
    """
    Fetch all job postings for a Lever company slug.
    Returns raw job dicts for downstream processing.
    """
    url = _BASE.format(slug=slug)
    resp = retry_get(url, params={"mode": "json", "limit": 500})
    if not resp:
        logger.info("Lever: no response for %s (%s)", company_name, slug)
        return []

    try:
        data = resp.json()
    except Exception:
        logger.warning("Lever: bad JSON for %s", slug)
        return []

    if not isinstance(data, list):
        logger.warning("Lever: unexpected payload shape for %s", slug)
        return []

    logger.info("Lever %s (%s): %d postings fetched", company_name, slug, len(data))

    results = []
    for job in data:
        jid = str(job.get("id", ""))
        title = job.get("text", "")
        categories = job.get("categories", {})
        location_raw = categories.get("location", "")
        apply_url = job.get("applyUrl", "") or job.get("hostedUrl", "")
        created_ms = job.get("createdAt")
        posted_at = _ms_to_date(created_ms)

        # Lever description is HTML — concatenate all sections
        desc_parts = []
        for field in ("description", "additional", "descriptionPlain"):
            part = job.get(field) or ""
            if part:
                desc_parts.append(clean_html(part) if "<" in part else part)
        # Also parse lists[] blocks
        for lst in job.get("lists", []):
            content = lst.get("content", "")
            if content:
                desc_parts.append(clean_html(content))
        description = " ".join(desc_parts)

        results.append({
            "external_id": jid,
            "source": "lever",
            "company_name": company_name,
            "title": title,
            "location": location_raw,
            "url": apply_url,
            "description": description,
            "posted_at": posted_at,
            "salary_raw_meta": None,
        })

    return results
