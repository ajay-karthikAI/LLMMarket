"""
Workday CXS REST API client (read-only, no auth required for public boards).

Usage pattern:
  fetch_workday(company_name, tenant, board)
  e.g. fetch_workday("Tempus AI", "tempus", "Tempus_Careers")

The CXS list endpoint returns title, externalPath, locationsText, postedOn.
We then fetch full job descriptions in parallel for AI-candidate titles only,
using the per-job CXS detail endpoint.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.helpers import retry_post, retry_get, clean_html

logger = logging.getLogger(__name__)

_LIST_URL  = "https://{tenant}.wd{shard}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs"
_DETAIL_URL = "https://{tenant}.wd{shard}.myworkdayjobs.com/wday/cxs/{tenant}/{board}{path}"
_JOB_URL    = "https://{tenant}.wd{shard}.myworkdayjobs.com/{board}{path}"

_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

_AI_TITLE = re.compile(
    r"\b(ai|ml|machine learning|data scientist|data engineer|nlp|llm|"
    r"generative|deep learning|research scientist|applied scientist|"
    r"computer vision|platform engineer|inference|model|neural|"
    r"analytics|bioinformatics|genomics|clinical ai|ambient|fhir|"
    r"software engineer|backend|infrastructure|devops|mlops)\b",
    re.I,
)
_EXCLUDE_TITLE = re.compile(
    r"\b(intern|sales|account executive|marketing|recruiter|legal|"
    r"counsel|finance|hr |human resources|customer success|nursing|"
    r"clinician|clinical success|physician|office manager|associate i\b)\b",
    re.I,
)


def _title_looks_ai(title: str) -> bool:
    return not _EXCLUDE_TITLE.search(title) and bool(_AI_TITLE.search(title))


def _fetch_all_postings(tenant: str, board: str, shard: int = 5) -> list[dict]:
    url = _LIST_URL.format(tenant=tenant, board=board, shard=shard)
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    resp = retry_post(url, json_body=payload, headers=_HEADERS)
    if not resp:
        return []
    try:
        data = resp.json()
    except Exception:
        return []

    total = data.get("total") or 0
    if not total:
        return []

    jobs = list(data.get("jobPostings") or [])

    # Fetch remaining pages
    offset = 20
    while offset < total:
        payload["offset"] = offset
        resp = retry_post(url, json_body=payload, headers=_HEADERS)
        if not resp:
            break
        try:
            page = resp.json().get("jobPostings") or []
        except Exception:
            break
        if not page:
            break
        jobs.extend(page)
        offset += 20

    return jobs


def _fetch_detail(tenant: str, board: str, path: str, shard: int = 5) -> dict:
    url = _DETAIL_URL.format(tenant=tenant, board=board, path=path, shard=shard)
    resp = retry_get(url, headers=_HEADERS)
    if not resp:
        return {}
    try:
        data = resp.json()
    except Exception:
        return {}
    return (data.get("jobPostingInfo") or {})


def fetch_workday(company_name: str, tenant: str, board: str, shard: int = 5) -> list[dict]:
    postings = _fetch_all_postings(tenant, board, shard)
    logger.info("Workday %s (%s/%s): %d postings", company_name, tenant, board, len(postings))

    # Pre-filter to AI-candidate titles before spending detail requests
    ai_postings = [p for p in postings if _title_looks_ai(p.get("title", ""))]
    logger.info("Workday %s: fetching details for %d AI-candidate jobs", company_name, len(ai_postings))

    detail_cache: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_fetch_detail, tenant, board, p["externalPath"], shard): p["externalPath"]
            for p in ai_postings
            if p.get("externalPath")
        }
        for fut in as_completed(futures):
            path = futures[fut]
            try:
                detail_cache[path] = fut.result()
            except Exception:
                detail_cache[path] = {}

    results = []
    for job in postings:
        path = job.get("externalPath", "")
        detail = detail_cache.get(path, {})

        title = job.get("title", "")
        location_raw = job.get("locationsText", "") or ""
        posted_at = detail.get("postedOn") or job.get("postedOn")
        description = clean_html(detail.get("jobDescription", "") or "")
        job_url = _JOB_URL.format(tenant=tenant, board=board, shard=shard, path=path) if path else ""

        results.append({
            "external_id": detail.get("jobPostingId") or detail.get("jobReqId") or path,
            "source": "workday",
            "company_name": company_name,
            "title": title,
            "location": location_raw,
            "url": job_url,
            "description": description,
            "posted_at": posted_at,
            "salary_raw_meta": None,
        })

    return results
