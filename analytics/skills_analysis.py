"""
Skill frequency, co-occurrence, salary correlation, and study roadmap analytics.
All computations are purely data-driven — no LLM inference.
"""

import logging
from collections import Counter, defaultdict
from itertools import combinations
from typing import Optional

import pandas as pd

from database.db import get_all_jobs, get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jobs_to_df(filters: Optional[dict] = None) -> pd.DataFrame:
    """Load jobs from DB into a DataFrame with skills as a list column."""
    rows = get_all_jobs(filters)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["skills_list"] = df["skills"].apply(
        lambda s: [x.strip() for x in s.split("|") if x.strip()] if s else []
    )
    df["skill_cats_list"] = df["skill_categories"].apply(
        lambda s: [x.strip() for x in s.split("|") if x.strip()] if s else []
    )
    return df


# ---------------------------------------------------------------------------
# Public analytics functions
# ---------------------------------------------------------------------------


def skill_frequency(
    filters: Optional[dict] = None,
    top_n: int = 30,
) -> pd.DataFrame:
    """
    Return a DataFrame of skill name, category, and job_count
    sorted descending by frequency.
    """
    df = _jobs_to_df(filters)
    if df.empty:
        return pd.DataFrame(columns=["skill", "category", "job_count", "pct"])

    counter: Counter = Counter()
    skill_to_cat: dict[str, str] = {}

    for _, row in df.iterrows():
        for skill, cat in zip(row["skills_list"], row["skill_cats_list"]):
            counter[skill] += 1
            skill_to_cat[skill] = cat

    total_jobs = len(df)
    records = [
        {"skill": skill, "category": skill_to_cat.get(skill, "Other"),
         "job_count": cnt, "pct": round(cnt / total_jobs * 100, 1)}
        for skill, cnt in counter.most_common(top_n)
    ]
    return pd.DataFrame(records)


def skill_frequency_by_category(filters: Optional[dict] = None) -> pd.DataFrame:
    """Return skill frequency grouped by category."""
    df = skill_frequency(filters, top_n=200)
    if df.empty:
        return df
    return (
        df.groupby("category")
        .apply(lambda g: g.nlargest(10, "job_count"))
        .reset_index(drop=True)
    )


def top_paying_skills(
    filters: Optional[dict] = None,
    top_n: int = 20,
    min_jobs: int = 2,
) -> pd.DataFrame:
    """
    For each skill, compute the median salary of jobs that list it.
    Returns skills sorted by median salary descending.
    """
    df = _jobs_to_df(filters)
    if df.empty:
        return pd.DataFrame(columns=["skill", "category", "median_salary", "job_count"])

    df = df.dropna(subset=["salary_min"])
    df["mid_salary"] = df.apply(
        lambda r: (r["salary_min"] + (r["salary_max"] or r["salary_min"])) / 2,
        axis=1,
    )

    skill_salaries: dict[str, list] = defaultdict(list)
    skill_to_cat: dict[str, str] = {}

    for _, row in df.iterrows():
        for skill, cat in zip(row["skills_list"], row["skill_cats_list"]):
            skill_salaries[skill].append(row["mid_salary"])
            skill_to_cat[skill] = cat

    records = []
    for skill, salaries in skill_salaries.items():
        if len(salaries) < min_jobs:
            continue
        records.append({
            "skill": skill,
            "category": skill_to_cat.get(skill, "Other"),
            "median_salary": int(sorted(salaries)[len(salaries) // 2]),
            "job_count": len(salaries),
        })

    result = pd.DataFrame(records)
    if result.empty:
        return result
    return result.nlargest(top_n, "median_salary").reset_index(drop=True)


def skill_combinations(
    filters: Optional[dict] = None,
    top_n: int = 20,
    min_count: int = 2,
) -> pd.DataFrame:
    """
    Find the most common skill pairs that appear together in job postings.
    """
    df = _jobs_to_df(filters)
    if df.empty:
        return pd.DataFrame(columns=["skill_a", "skill_b", "co_count"])

    pair_counter: Counter = Counter()
    for skill_list in df["skills_list"]:
        unique_skills = sorted(set(skill_list))
        for a, b in combinations(unique_skills, 2):
            pair_counter[(a, b)] += 1

    records = [
        {"skill_a": a, "skill_b": b, "co_count": cnt}
        for (a, b), cnt in pair_counter.most_common(top_n)
        if cnt >= min_count
    ]
    return pd.DataFrame(records)


def study_roadmap(
    role_category: Optional[str] = None,
    top_n_skills: int = 40,
) -> dict[str, list[str]]:
    """
    Generate a grouped study roadmap from real job data.
    Groups skills by category, sorted by frequency within each category.
    Returns {category: [skill, ...]} — no LLM, purely from DB counts.
    """
    filters = {"role_categories": [role_category]} if role_category else None
    freq_df = skill_frequency(filters, top_n=top_n_skills)
    if freq_df.empty:
        return {}

    roadmap: dict[str, list[str]] = defaultdict(list)
    for _, row in freq_df.iterrows():
        roadmap[row["category"]].append(row["skill"])

    # Preferred category order for display
    order = [
        "LLM Stack", "ML/DL", "Healthcare", "MLOps",
        "Data Engineering", "Infrastructure", "Cloud",
        "Programming", "Governance",
    ]
    sorted_roadmap = {}
    for cat in order:
        if cat in roadmap:
            sorted_roadmap[cat] = roadmap[cat]
    for cat in roadmap:
        if cat not in sorted_roadmap:
            sorted_roadmap[cat] = roadmap[cat]

    return sorted_roadmap


def skills_summary_stats(filters: Optional[dict] = None) -> dict:
    """Return high-level summary metrics for display in the app."""
    from database.db import get_all_jobs
    jobs = get_all_jobs(filters)
    if not jobs:
        return {"total_jobs": 0, "unique_skills": 0, "avg_salary": 0, "companies": 0}

    all_skills: set = set()
    salaries = []
    companies: set = set()
    for j in jobs:
        if j.get("skills"):
            all_skills.update(s.strip() for s in j["skills"].split("|") if s.strip())
        if j.get("salary_min"):
            salaries.append(j["salary_min"])
        companies.add(j["company_name"])

    return {
        "total_jobs": len(jobs),
        "unique_skills": len(all_skills),
        "avg_salary": int(sum(salaries) / len(salaries)) if salaries else 0,
        "companies": len(companies),
    }
