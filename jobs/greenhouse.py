"""
Greenhouse public Jobs Board API client.
Docs: https://developers.greenhouse.io/job-board.html
"""

import logging
from datetime import datetime
from typing import Optional

from utils.helpers import retry_get, clean_html

logger = logging.getLogger(__name__)

_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def _parse_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt[:len(fmt)]).\
                strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _extract_salary_from_metadata(metadata: list) -> dict:
    """Some Greenhouse boards expose salary in the custom metadata array."""
    result: dict = {}
    for field in metadata or []:
        name = (field.get("name") or "").lower()
        val = field.get("value") or ""
        if any(k in name for k in ("salary", "compensation", "pay", "comp")):
            result["salary_raw"] = str(val)
    return result


def fetch_greenhouse(company_name: str, slug: str) -> list[dict]:
    """
    Fetch all job postings for a Greenhouse board slug.
    Returns a list of raw job dicts ready for downstream processing.
    """
    url = _BASE.format(slug=slug)
    resp = retry_get(url, params={"content": "true"})
    if not resp:
        logger.info("Greenhouse: no response for %s (%s)", company_name, slug)
        return []

    try:
        data = resp.json()
    except Exception:
        logger.warning("Greenhouse: bad JSON for %s", slug)
        return []

    jobs_raw = data.get("jobs", [])
    logger.info("Greenhouse %s (%s): %d postings fetched", company_name, slug, len(jobs_raw))

    results = []
    for job in jobs_raw:
        jid = str(job.get("id", ""))
        title = job.get("title", "")
        location_raw = (job.get("location") or {}).get("name", "")
        url_link = job.get("absolute_url", "")
        updated_at = _parse_date(job.get("updated_at"))

        # Description may be HTML
        desc_html = job.get("content", "") or ""
        desc_text = clean_html(desc_html)

        # Salary sometimes in metadata
        meta_salary = _extract_salary_from_metadata(job.get("metadata", []))

        results.append({
            "external_id": jid,
            "source": "greenhouse",
            "company_name": company_name,
            "title": title,
            "location": location_raw,
            "url": url_link,
            "description": desc_text,
            "posted_at": updated_at,
            "salary_raw_meta": meta_salary.get("salary_raw"),
        })

    return results
