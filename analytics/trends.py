"""
Trend analytics — weekly/monthly skill growth using the snapshot table.
"""

import logging
from typing import Optional

import pandas as pd

from database.db import get_skill_trend, get_connection

logger = logging.getLogger(__name__)


def skill_trend_df(days: int = 60) -> pd.DataFrame:
    """
    Return a long-format DataFrame of skill job counts over time.
    Columns: snapshot_date, canonical_name, category, job_count
    """
    rows = get_skill_trend(days)
    if not rows:
        return pd.DataFrame(columns=["snapshot_date", "canonical_name", "category", "job_count"])
    df = pd.DataFrame(rows)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


def fastest_growing_skills(days: int = 30, top_n: int = 15) -> pd.DataFrame:
    """
    Identify skills with the largest absolute increase in job_count
    from the earliest snapshot in the window to the most recent.
    Returns DataFrame: skill, category, count_start, count_end, growth.
    """
    df = skill_trend_df(days)
    if df.empty or df["snapshot_date"].nunique() < 2:
        return pd.DataFrame(columns=["skill", "category", "count_start", "count_end", "growth"])

    earliest = df["snapshot_date"].min()
    latest = df["snapshot_date"].max()

    start = df[df["snapshot_date"] == earliest].set_index("canonical_name")[["job_count", "category"]]
    end = df[df["snapshot_date"] == latest].set_index("canonical_name")[["job_count", "category"]]

    merged = start.join(end, lsuffix="_start", rsuffix="_end", how="inner")
    merged = merged.rename(columns={
        "job_count_start": "count_start",
        "job_count_end": "count_end",
        "category_start": "category",
    })
    merged["growth"] = merged["count_end"] - merged["count_start"]
    merged = merged[merged["growth"] > 0].sort_values("growth", ascending=False)
    merged = merged.head(top_n).reset_index().rename(columns={"canonical_name": "skill"})
    return merged[["skill", "category", "count_start", "count_end", "growth"]]


def weekly_snapshot_summary() -> pd.DataFrame:
    """
    Aggregate snapshots by ISO week, summing job counts per skill.
    Returns: week, canonical_name, category, weekly_jobs
    """
    df = skill_trend_df(90)
    if df.empty:
        return df
    df["week"] = df["snapshot_date"].dt.to_period("W").astype(str)
    weekly = (
        df.groupby(["week", "canonical_name", "category"])["job_count"]
        .sum()
        .reset_index()
        .rename(columns={"job_count": "weekly_jobs"})
    )
    return weekly


def category_trend(days: int = 60) -> pd.DataFrame:
    """
    Aggregate skill counts by category over time.
    Returns: snapshot_date, category, total_jobs
    """
    df = skill_trend_df(days)
    if df.empty:
        return df
    return (
        df.groupby(["snapshot_date", "category"])["job_count"]
        .sum()
        .reset_index()
        .rename(columns={"job_count": "total_jobs"})
    )
