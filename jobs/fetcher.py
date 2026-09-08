"""
Job fetch orchestrator.
Pulls from Greenhouse, Lever, and Ashby, applies filters, and persists to SQLite.
"""

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from database.db import (
    init_db, upsert_company, insert_job, upsert_skill,
    link_job_skill, take_skill_snapshot,
)
from extraction.skills import extract_skills
from extraction.salary import parse_salary, meets_salary_threshold
from extraction.location import normalize_location
from jobs.greenhouse import fetch_greenhouse
from jobs.lever import fetch_lever
from jobs.ashby import fetch_ashby

logger = logging.getLogger(__name__)

MIN_SALARY = int(os.getenv("MIN_SALARY", "150000"))
FETCH_WORKERS = int(os.getenv("FETCH_WORKERS", "4"))

# ---------------------------------------------------------------------------
# Company Registry
# Each entry: (display_name, ats_type, slug, career_url)
# ---------------------------------------------------------------------------

COMPANY_REGISTRY: list[dict] = [
    # -----------------------------------------------------------------------
    # GREENHOUSE — slugs verified live
    # -----------------------------------------------------------------------

    # Clinical AI & Imaging
    {"name": "PathAI",              "ats": "greenhouse", "slug": "pathai",                  "url": "https://job-boards.greenhouse.io/pathai"},
    {"name": "Butterfly Network",   "ats": "greenhouse", "slug": "butterflynetwork",        "url": "https://job-boards.greenhouse.io/butterflynetwork"},
    {"name": "Qventus",             "ats": "greenhouse", "slug": "qventus",                 "url": "https://job-boards.greenhouse.io/qventus"},
    {"name": "Suki",                "ats": "greenhouse", "slug": "suki",                    "url": "https://job-boards.greenhouse.io/suki"},

    # Genomics & Biotech
    {"name": "Recursion",           "ats": "greenhouse", "slug": "recursionpharmaceuticals","url": "https://job-boards.greenhouse.io/recursionpharmaceuticals"},
    {"name": "Natera",              "ats": "greenhouse", "slug": "natera",                  "url": "https://job-boards.greenhouse.io/natera"},
    {"name": "Freenome",            "ats": "greenhouse", "slug": "freenome",                "url": "https://job-boards.greenhouse.io/freenome"},
    {"name": "10x Genomics",        "ats": "greenhouse", "slug": "10xgenomics",             "url": "https://job-boards.greenhouse.io/10xgenomics"},
    {"name": "Twist Bioscience",    "ats": "greenhouse", "slug": "twistbioscience",         "url": "https://job-boards.greenhouse.io/twistbioscience"},
    {"name": "Veracyte",            "ats": "greenhouse", "slug": "veracyte",                "url": "https://job-boards.greenhouse.io/veracyte"},
    {"name": "Blueprint Medicines", "ats": "greenhouse", "slug": "blueprintmedicines",      "url": "https://job-boards.greenhouse.io/blueprintmedicines"},
    {"name": "Relay Therapeutics",  "ats": "greenhouse", "slug": "relaytherapeutics",       "url": "https://job-boards.greenhouse.io/relaytherapeutics"},
    {"name": "Akoya Biosciences",   "ats": "greenhouse", "slug": "akoya",                   "url": "https://job-boards.greenhouse.io/akoya"},

    # Health Data & Analytics
    {"name": "Flatiron Health",     "ats": "greenhouse", "slug": "flatironhealth",          "url": "https://job-boards.greenhouse.io/flatironhealth"},
    {"name": "Komodo Health",       "ats": "greenhouse", "slug": "komodohealth",            "url": "https://job-boards.greenhouse.io/komodohealth"},
    {"name": "Cohere Health",       "ats": "greenhouse", "slug": "coherehealth",            "url": "https://job-boards.greenhouse.io/coherehealth"},
    {"name": "Inovalon",            "ats": "greenhouse", "slug": "inovalon",                "url": "https://job-boards.greenhouse.io/inovalon"},
    {"name": "Definitive Healthcare","ats": "greenhouse","slug": "definitivehc",            "url": "https://job-boards.greenhouse.io/definitivehc"},
    {"name": "Doximity",            "ats": "greenhouse", "slug": "doximity",                "url": "https://job-boards.greenhouse.io/doximity"},
    {"name": "Garner Health",       "ats": "greenhouse", "slug": "garnerhealth",            "url": "https://job-boards.greenhouse.io/garnerhealth"},
    {"name": "Collective Health",   "ats": "greenhouse", "slug": "collectivehealth",        "url": "https://job-boards.greenhouse.io/collectivehealth"},

    # Payer / Insurance AI
    {"name": "Oscar Health",        "ats": "greenhouse", "slug": "oscar",                   "url": "https://job-boards.greenhouse.io/oscar"},
    {"name": "Clover Health",       "ats": "greenhouse", "slug": "cloverhealth",            "url": "https://job-boards.greenhouse.io/cloverhealth"},

    # Mental Health & Digital Health
    {"name": "Cerebral",            "ats": "greenhouse", "slug": "cerebral",                "url": "https://job-boards.greenhouse.io/cerebral"},
    {"name": "Modern Health",       "ats": "greenhouse", "slug": "modernhealth",            "url": "https://job-boards.greenhouse.io/modernhealth"},
    {"name": "Omada Health",        "ats": "greenhouse", "slug": "omadahealth",             "url": "https://job-boards.greenhouse.io/omadahealth"},
    {"name": "Talkspace",           "ats": "greenhouse", "slug": "talkspace",               "url": "https://job-boards.greenhouse.io/talkspace"},
    {"name": "Alma",                "ats": "greenhouse", "slug": "alma",                    "url": "https://job-boards.greenhouse.io/alma"},
    {"name": "Transcarent",         "ats": "greenhouse", "slug": "transcarent",             "url": "https://job-boards.greenhouse.io/transcarent"},
    {"name": "Workit Health",       "ats": "greenhouse", "slug": "workithealth",            "url": "https://job-boards.greenhouse.io/workithealth"},

    # -----------------------------------------------------------------------
    # LEVER — slugs verified live
    # -----------------------------------------------------------------------
    {"name": "Veeva Systems",       "ats": "lever",      "slug": "veeva",                   "url": "https://jobs.lever.co/veeva"},
    {"name": "Arcadia",             "ats": "lever",      "slug": "arcadia",                 "url": "https://jobs.lever.co/arcadia"},
    {"name": "Artera AI",           "ats": "lever",      "slug": "artera",                  "url": "https://jobs.lever.co/artera"},
    {"name": "Included Health",     "ats": "lever",      "slug": "includedhealth",          "url": "https://jobs.lever.co/includedhealth"},
    {"name": "Ro",                  "ats": "lever",      "slug": "ro",                      "url": "https://jobs.lever.co/ro"},
    {"name": "Clarify Health",      "ats": "lever",      "slug": "clarifyhealth",           "url": "https://jobs.lever.co/clarifyhealth"},
    {"name": "BenchSci",            "ats": "lever",      "slug": "benchsci",                "url": "https://jobs.lever.co/benchsci"},
    {"name": "Veda Data",           "ats": "lever",      "slug": "vedadata",                "url": "https://jobs.lever.co/vedadata"},

    # -----------------------------------------------------------------------
    # ASHBY — slugs verified live
    # -----------------------------------------------------------------------
    {"name": "OpenEvidence",        "ats": "ashby",      "slug": "openevidence",            "url": "https://jobs.ashbyhq.com/openevidence"},
    {"name": "Anterior",            "ats": "ashby",      "slug": "anterior",                "url": "https://jobs.ashbyhq.com/anterior"},
    {"name": "Thoughtful AI",       "ats": "ashby",      "slug": "thoughtful",              "url": "https://jobs.ashbyhq.com/thoughtful"},
    {"name": "Regard",              "ats": "ashby",      "slug": "regard",                  "url": "https://jobs.ashbyhq.com/regard"},
    {"name": "Datavant",            "ats": "ashby",      "slug": "datavant",                "url": "https://jobs.ashbyhq.com/datavant"},
    {"name": "Apixio",              "ats": "ashby",      "slug": "apixio",                  "url": "https://jobs.ashbyhq.com/apixio"},
    {"name": "Abridge",             "ats": "ashby",      "slug": "abridge",                 "url": "https://jobs.ashbyhq.com/abridge"},
    {"name": "Cohere (AI)",         "ats": "ashby",      "slug": "cohere",                  "url": "https://jobs.ashbyhq.com/cohere"},
    {"name": "Ambience Healthcare", "ats": "ashby",      "slug": "ambiencehealthcare",      "url": "https://jobs.ashbyhq.com/ambiencehealthcare"},
    {"name": "Nabla",               "ats": "ashby",      "slug": "nabla",                   "url": "https://jobs.ashbyhq.com/nabla"},
    {"name": "Notable Health",      "ats": "ashby",      "slug": "notable",                 "url": "https://jobs.ashbyhq.com/notable"},
    {"name": "Insitro",             "ats": "ashby",      "slug": "insitro",                 "url": "https://jobs.ashbyhq.com/insitro"},
    {"name": "Freed",               "ats": "ashby",      "slug": "freed",                   "url": "https://jobs.ashbyhq.com/freed"},
    {"name": "Owkin",               "ats": "ashby",      "slug": "owkin",                   "url": "https://jobs.ashbyhq.com/owkin"},
    # New Ashby — verified live
    {"name": "Canvas Medical",      "ats": "ashby",      "slug": "canvas-medical",          "url": "https://jobs.ashbyhq.com/canvas-medical"},
    {"name": "Health Gorilla",      "ats": "ashby",      "slug": "healthgorilla",           "url": "https://jobs.ashbyhq.com/healthgorilla"},
    {"name": "Modal",               "ats": "ashby",      "slug": "modal",                   "url": "https://jobs.ashbyhq.com/modal"},
    {"name": "Unlearn.AI",          "ats": "ashby",      "slug": "unlearn",                 "url": "https://jobs.ashbyhq.com/unlearn"},

    # -----------------------------------------------------------------------
]

# ---------------------------------------------------------------------------
# Additional companies added via Greenhouse sweep (verified live)
# ---------------------------------------------------------------------------
COMPANY_REGISTRY += [
    # Genomics / Drug Discovery
    {"name": "Isomorphic Labs",     "ats": "greenhouse", "slug": "isomorphiclabs",          "url": "https://job-boards.greenhouse.io/isomorphiclabs"},
    # Digital Health / Value-Based Care
    {"name": "Maven Clinic",        "ats": "greenhouse", "slug": "mavenclinic",             "url": "https://job-boards.greenhouse.io/mavenclinic"},
    {"name": "Waymark",             "ats": "greenhouse", "slug": "waymark",                 "url": "https://job-boards.greenhouse.io/waymark"},
    {"name": "Wellthy",             "ats": "greenhouse", "slug": "wellthy",                 "url": "https://job-boards.greenhouse.io/wellthy"},
    # Remote Patient Monitoring
    {"name": "Biofourmis",          "ats": "greenhouse", "slug": "biofourmis",              "url": "https://job-boards.greenhouse.io/biofourmis"},
]

_ATS_FETCHERS: dict[str, Callable] = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
}

# ---------------------------------------------------------------------------
# Role Classification
# Covers ALL seniority levels — junior through VP/C-suite.
# Salary threshold ($150k+) is the gating criterion, not title.
# ---------------------------------------------------------------------------

_ROLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("LLM / Generative AI",    re.compile(r"\b(llm|large language model|generative ai|genai|gen ai|gpt|foundation model|prompt engineer)\b", re.I)),
    ("Clinical AI",            re.compile(r"\b(clinical ai|medical ai|healthcare ai|clinical ml|medical ml|ambient|ambient scribe|ambient ai|clinical nlp|medical nlp)\b", re.I)),
    ("ML Engineer",            re.compile(r"\b(machine learning engineer|ml engineer|mle|applied ml|ml platform|mlops|ml infrastructure|ml ops)\b", re.I)),
    ("Applied Scientist",      re.compile(r"\b(applied scientist|research scientist|research engineer|applied research)\b", re.I)),
    ("Data Scientist",         re.compile(r"\b(data scientist|healthcare data scientist|clinical data scientist|biostatistician|health data scientist)\b", re.I)),
    ("AI Platform / Infra",    re.compile(r"\b(ai platform|ai infrastructure|ai infra|model serving|inference|mlflow|kubeflow|model platform)\b", re.I)),
    ("Computer Vision",        re.compile(r"\b(computer vision|image recognition|medical imaging|radiology ai|pathology ai|dicom)\b", re.I)),
    ("NLP Engineer",           re.compile(r"\b(nlp engineer|natural language|text mining|information extraction|ner|named entity)\b", re.I)),
    ("Data Engineer",          re.compile(r"\b(data engineer|data pipeline|etl|elt|data platform|data infrastructure|spark|airflow|fhir engineer)\b", re.I)),
    ("AI / ML",                re.compile(r"\b(ai engineer|artificial intelligence|deep learning|neural network|ml scientist)\b", re.I)),
]

_SENIORITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("VP / Director", re.compile(r"\b(vp|vice president|director|head of)\b", re.I)),
    ("Principal / Staff", re.compile(r"\b(principal|staff engineer|distinguished|fellow)\b", re.I)),
    ("Lead / Architect", re.compile(r"\b(lead|tech lead|architect|senior staff)\b", re.I)),
    ("Senior", re.compile(r"\b(senior|sr\.?)\b", re.I)),
    ("Mid-level", re.compile(r"\b(ii|2|mid.level|mid level)\b", re.I)),
    ("Junior / Associate", re.compile(r"\b(junior|jr\.?|associate|entry.level|new grad|ng)\b", re.I)),
]

_EXCLUDE_TITLES = re.compile(
    r"\b(intern|internship|co.op|coop|sales|account executive|marketing|"
    r"recruiter|recruiting|finance|legal|administrative|office manager|"
    r"customer success|account manager|business development|hr |human resources)\b",
    re.I,
)

_AI_TITLE_PAT = re.compile(
    r"\b(ai|ml|machine learning|deep learning|data science|nlp|llm|"
    r"generative|clinical ai|medical ai|healthcare ai|mlops|"
    r"research engineer|applied scientist|data engineer|platform engineer|"
    r"inference|model|neural|computer vision|bioinformatics|genomics|"
    r"imaging|radiology|ambient|scribe|fhir|ehr)\b",
    re.I,
)


def classify_role(title: str, description: str) -> str:
    combined = f"{title} {description[:2000]}"
    for category, pat in _ROLE_PATTERNS:
        if pat.search(combined):
            return category
    return "AI / ML"


def classify_seniority(title: str) -> str:
    for level, pat in _SENIORITY_PATTERNS:
        if pat.search(title):
            return level
    return "Mid-level"


def is_ai_role(title: str, description: str) -> bool:
    if _EXCLUDE_TITLES.search(title):
        return False
    if _AI_TITLE_PAT.search(title):
        return True
    # Fallback: check description for strong AI signal
    desc_snippet = description[:1500] if description else ""
    ai_mentions = len(re.findall(
        r"\b(machine learning|deep learning|neural network|llm|transformer|"
        r"pytorch|tensorflow|scikit|xgboost|nlp|computer vision|mlops|"
        r"clinical ai|medical ai|generative ai)\b", desc_snippet, re.I))
    return ai_mentions >= 3


# ---------------------------------------------------------------------------
# Per-company fetch + filter + persist
# ---------------------------------------------------------------------------


def _process_raw_job(raw: dict, company_id: int) -> dict | None:
    """
    Apply all filters and enrichment to a single raw job dict.
    Returns an enriched dict ready for DB insert, or None if filtered out.
    """
    title = raw.get("title", "")
    description = raw.get("description", "") or ""
    location_raw = raw.get("location", "") or ""

    # --- Filter: must be an AI role ---
    if not is_ai_role(title, description):
        return None

    # --- Filter: must be US location ---
    location_norm = normalize_location(location_raw)
    if not location_norm:
        # Some jobs list location in description ("Remote - US")
        location_norm = normalize_location(description[:300])
    if not location_norm:
        return None

    # --- Salary extraction ---
    # Priority: metadata hint -> description text
    salary_text = raw.get("salary_raw_meta") or ""
    salary_dict = parse_salary(salary_text) if salary_text else {}
    if not salary_dict:
        salary_dict = parse_salary(description)

    # Salary stored as-is (may be None). UI slider handles threshold filtering.
    # We never fabricate salary — NULL means the posting didn't disclose it.
    role_category = classify_role(title, description)
    seniority = classify_seniority(title)
    is_remote = location_norm == "Remote"

    return {
        "external_id": raw["external_id"],
        "source": raw["source"],
        "company_id": company_id,
        "company_name": raw["company_name"],
        "title": title,
        "location": location_raw,
        "location_normalized": location_norm,
        "salary_min": salary_dict.get("salary_min"),
        "salary_max": salary_dict.get("salary_max"),
        "salary_raw": salary_dict.get("salary_raw"),
        "is_remote": is_remote,
        "url": raw.get("url", ""),
        "description": description,
        "role_category": role_category,
        "seniority": seniority,
        "posted_at": raw.get("posted_at"),
    }


def _fetch_and_store_company(entry: dict) -> tuple[str, int, int]:
    """Fetch, filter, extract, and persist one company's jobs."""
    name = entry["name"]
    ats = entry["ats"]
    slug = entry["slug"]
    url = entry.get("url", "")

    fetcher = _ATS_FETCHERS.get(ats)
    if not fetcher:
        logger.warning("Unknown ATS type: %s for %s", ats, name)
        return name, 0, 0

    company_id = upsert_company(name, slug, ats, url)

    raw_jobs = fetcher(name, slug)

    stored = 0
    skipped = 0
    for raw in raw_jobs:
        enriched = _process_raw_job(raw, company_id)
        if enriched is None:
            skipped += 1
            continue

        job_id = insert_job(enriched)
        if job_id is None:
            skipped += 1
            continue

        # Skill extraction and linking
        skills = extract_skills(enriched["description"])
        for skill in skills:
            skill_id = upsert_skill(skill.canonical, skill.category, skill.subcategory)
            link_job_skill(job_id, skill_id)

        stored += 1

    logger.info("%s: %d stored, %d skipped", name, stored, skipped)
    return name, stored, skipped


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_all_fetchers(
    companies: list[dict] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict:
    """
    Fetch jobs from all companies in parallel.
    Returns summary {total_stored, total_skipped, companies}.
    """
    init_db()
    targets = companies or COMPANY_REGISTRY
    total_stored = 0
    total_skipped = 0
    results = []

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch_and_store_company, e): e for e in targets}
        for future in as_completed(futures):
            try:
                name, stored, skipped = future.result()
                total_stored += stored
                total_skipped += skipped
                results.append({"company": name, "stored": stored, "skipped": skipped})
                if progress_callback:
                    progress_callback(name, stored, skipped)
            except Exception:
                entry = futures[future]
                logger.exception("Unhandled error fetching %s", entry["name"])

    # Take a daily skill snapshot for trend tracking
    try:
        take_skill_snapshot()
    except Exception:
        logger.exception("Skill snapshot failed")

    logger.info("Fetch complete: %d stored, %d skipped across %d companies",
                total_stored, total_skipped, len(targets))
    return {
        "total_stored": total_stored,
        "total_skipped": total_skipped,
        "companies": results,
    }
