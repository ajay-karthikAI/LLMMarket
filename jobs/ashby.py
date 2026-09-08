"""
Ashby HQ public job board GraphQL API client.
No auth required for public boards.

Some Ashby boards return a richer type (with isRemote, descriptionHtml, etc.) while
others return a stripped-down type (JobPostingBriefsWithIdsAndTeamId) that only has
id, title, locationName, compensationTierSummary, and employmentType.  We try the full
query first and fall back to the minimal one on GRAPHQL_VALIDATION_FAILED.

For minimal-schema boards we fetch descriptions individually (in parallel, title-filtered)
using the ApiJobPosting detail endpoint so skill extraction still works.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.helpers import retry_post, clean_html

logger = logging.getLogger(__name__)

_BOARD_URL  = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
_DETAIL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
_HEADERS    = {"Content-Type": "application/json"}

_QUERY_FULL = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    jobPostings {
      id title isRemote isListed employmentType locationName
      publishedDate externalLink descriptionHtml compensationTierSummary
      team { name }
    }
  }
}
"""

_QUERY_MINIMAL = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    jobPostings {
      id title locationName compensationTierSummary employmentType
    }
  }
}
"""

_QUERY_DETAIL = """
query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
    jobPostingId: $jobPostingId
  ) {
    id title descriptionHtml locationName publishedDate compensationTierSummary
  }
}
"""

# Quick title-based AI signal — same idea as is_ai_role() but lightweight,
# used only to decide whether to spend a detail request on this posting.
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
    r"clinician|clinical success|physician|office manager)\b",
    re.I,
)


def _title_looks_ai(title: str) -> bool:
    return not _EXCLUDE_TITLE.search(title) and bool(_AI_TITLE.search(title))


def _board_post(slug: str, query: str) -> list[dict] | None:
    payload = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": slug},
        "query": query,
    }
    resp = retry_post(_BOARD_URL, json_body=payload, headers=_HEADERS)
    if not resp:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if data.get("errors"):
        codes = [e.get("extensions", {}).get("code", "") for e in data["errors"]]
        if any(c == "GRAPHQL_VALIDATION_FAILED" for c in codes):
            return None     # signal caller to retry with minimal query
        return []
    return (data.get("data") or {}).get("jobBoard", {}).get("jobPostings") or []


def _fetch_detail(slug: str, job_id: str) -> dict:
    """Fetch full description for a single job posting."""
    payload = {
        "operationName": "ApiJobPosting",
        "variables": {"organizationHostedJobsPageName": slug, "jobPostingId": job_id},
        "query": _QUERY_DETAIL,
    }
    resp = retry_post(_DETAIL_URL, json_body=payload, headers=_HEADERS)
    if not resp:
        return {}
    try:
        data = resp.json()
    except Exception:
        return {}
    return (data.get("data") or {}).get("jobPosting") or {}


def fetch_ashby(company_name: str, slug: str) -> list[dict]:
    postings = _board_post(slug, _QUERY_FULL)
    minimal = False
    if postings is None:
        logger.info("Ashby %s: full schema unavailable, fetching descriptions individually", slug)
        postings = _board_post(slug, _QUERY_MINIMAL) or []
        minimal = True

    logger.info("Ashby %s (%s): %d postings", company_name, slug, len(postings))

    # For minimal-schema boards, fetch descriptions in parallel for AI-candidate titles
    detail_cache: dict[str, dict] = {}
    if minimal:
        ai_ids = [str(j.get("id", "")) for j in postings if _title_looks_ai(j.get("title", ""))]
        logger.info("Ashby %s: fetching %d job details", slug, len(ai_ids))
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_detail, slug, jid): jid for jid in ai_ids}
            for fut in as_completed(futures):
                jid = futures[fut]
                try:
                    detail_cache[jid] = fut.result()
                except Exception:
                    detail_cache[jid] = {}

    results = []
    for job in postings:
        if not minimal and not job.get("isListed", True):
            continue

        jid          = str(job.get("id", ""))
        title        = job.get("title", "")
        location_raw = job.get("locationName", "") or ""

        if not minimal:
            is_remote = job.get("isRemote", False)
            if is_remote and not location_raw:
                location_raw = "Remote"
            description  = clean_html(job.get("descriptionHtml", "") or "")
            external_link = job.get("externalLink") or f"https://jobs.ashbyhq.com/{slug}/{jid}"
            posted_at    = job.get("publishedDate")
            comp_summary = job.get("compensationTierSummary") or ""
        else:
            detail       = detail_cache.get(jid, {})
            description  = clean_html(detail.get("descriptionHtml", "") or "")
            external_link = f"https://jobs.ashbyhq.com/{slug}/{jid}"
            posted_at    = detail.get("publishedDate")
            comp_summary = job.get("compensationTierSummary") or detail.get("compensationTierSummary") or ""

        results.append({
            "external_id":    jid,
            "source":         "ashby",
            "company_name":   company_name,
            "title":          title,
            "location":       location_raw,
            "url":            external_link,
            "description":    description,
            "posted_at":      posted_at,
            "salary_raw_meta": comp_summary or None,
        })

    return results
