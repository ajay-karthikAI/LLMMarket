"""SQLite persistence layer — schema, connection management, and CRUD helpers."""

import logging
import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "healthai_jobs.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_DEFAULT_DB)))

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    slug        TEXT,
    ats_type    TEXT,
    career_url  TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id         TEXT    NOT NULL,
    source              TEXT    NOT NULL,
    company_id          INTEGER REFERENCES companies(id),
    company_name        TEXT    NOT NULL,
    title               TEXT    NOT NULL,
    location            TEXT,
    location_normalized TEXT,
    salary_min          INTEGER,
    salary_max          INTEGER,
    salary_raw          TEXT,
    is_remote           INTEGER DEFAULT 0,
    url                 TEXT    NOT NULL,
    description         TEXT,
    role_category       TEXT,
    seniority           TEXT,
    posted_at           TIMESTAMP,
    fetched_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active           INTEGER DEFAULT 1,
    UNIQUE(external_id, source)
);

CREATE TABLE IF NOT EXISTS skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,
    subcategory     TEXT
);

CREATE TABLE IF NOT EXISTS job_skills (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id   INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills(id),
    UNIQUE(job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date DATE    NOT NULL,
    skill_id      INTEGER REFERENCES skills(id),
    job_count     INTEGER DEFAULT 0,
    UNIQUE(snapshot_date, skill_id)
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id   INTEGER REFERENCES jobs(id) ON DELETE CASCADE UNIQUE,
    notes    TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_salary   ON jobs(salary_min);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location_normalized);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_active   ON jobs(is_active);
"""

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(_SCHEMA)
    logger.info("Database initialised at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


def upsert_company(name: str, slug: str, ats_type: str, career_url: str = "") -> int:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO companies (name, slug, ats_type, career_url)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 slug       = excluded.slug,
                 ats_type   = excluded.ats_type,
                 career_url = COALESCE(NULLIF(excluded.career_url,''), career_url)""",
            (name, slug, ats_type, career_url),
        )
        row = conn.execute(
            "SELECT id FROM companies WHERE name = ?", (name,)
        ).fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def insert_job(job_data: dict) -> Optional[int]:
    """Upsert a job record. Returns the row ID, or None on error."""
    sql = """
        INSERT INTO jobs (
            external_id, source, company_id, company_name, title,
            location, location_normalized, salary_min, salary_max,
            salary_raw, is_remote, url, description,
            role_category, seniority, posted_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(external_id, source) DO UPDATE SET
            title               = excluded.title,
            url                 = excluded.url,
            salary_min          = excluded.salary_min,
            salary_max          = excluded.salary_max,
            salary_raw          = excluded.salary_raw,
            description         = excluded.description,
            role_category       = excluded.role_category,
            seniority           = excluded.seniority,
            is_active           = 1,
            fetched_at          = CURRENT_TIMESTAMP
    """
    try:
        with get_connection() as conn:
            conn.execute(
                sql,
                (
                    job_data["external_id"],
                    job_data["source"],
                    job_data.get("company_id"),
                    job_data["company_name"],
                    job_data["title"],
                    job_data.get("location"),
                    job_data.get("location_normalized"),
                    job_data.get("salary_min"),
                    job_data.get("salary_max"),
                    job_data.get("salary_raw"),
                    int(job_data.get("is_remote", False)),
                    job_data["url"],
                    job_data.get("description"),
                    job_data.get("role_category"),
                    job_data.get("seniority"),
                    job_data.get("posted_at"),
                ),
            )
            row = conn.execute(
                "SELECT id FROM jobs WHERE external_id=? AND source=?",
                (job_data["external_id"], job_data["source"]),
            ).fetchone()
            return row[0] if row else None
    except Exception:
        logger.exception("Error inserting job external_id=%s", job_data.get("external_id"))
        return None


def get_all_jobs(filters: Optional[dict] = None) -> list[dict]:
    base = """
        SELECT j.*,
               GROUP_CONCAT(s.canonical_name, '|') AS skills,
               GROUP_CONCAT(s.category,       '|') AS skill_categories
        FROM jobs j
        LEFT JOIN job_skills js ON j.id = js.job_id
        LEFT JOIN skills     s  ON js.skill_id = s.id
        WHERE j.is_active = 1
    """
    params: list = []
    f = filters or {}

    if f.get("min_salary"):
        base += " AND (j.salary_min >= ? OR j.salary_max >= ?)"
        params += [f["min_salary"], f["min_salary"]]
    if f.get("locations"):
        placeholders = ",".join("?" * len(f["locations"]))
        base += f" AND j.location_normalized IN ({placeholders})"
        params += f["locations"]
    if f.get("companies"):
        placeholders = ",".join("?" * len(f["companies"]))
        base += f" AND j.company_name IN ({placeholders})"
        params += f["companies"]
    if f.get("role_categories"):
        placeholders = ",".join("?" * len(f["role_categories"]))
        base += f" AND j.role_category IN ({placeholders})"
        params += f["role_categories"]
    if f.get("skill"):
        base += " AND j.id IN (SELECT job_id FROM job_skills js2 JOIN skills s2 ON js2.skill_id=s2.id WHERE LOWER(s2.canonical_name) LIKE ?)"
        params.append(f"%{f['skill'].lower()}%")

    base += " GROUP BY j.id ORDER BY j.fetched_at DESC"

    with get_connection() as conn:
        return [dict(r) for r in conn.execute(base, params).fetchall()]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def upsert_skill(canonical_name: str, category: str, subcategory: str = "") -> int:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO skills (canonical_name, category, subcategory)
               VALUES (?, ?, ?)
               ON CONFLICT(canonical_name) DO NOTHING""",
            (canonical_name, category, subcategory),
        )
        row = conn.execute(
            "SELECT id FROM skills WHERE canonical_name = ?", (canonical_name,)
        ).fetchone()
        return row[0]


def link_job_skill(job_id: int, skill_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)",
            (job_id, skill_id),
        )


# ---------------------------------------------------------------------------
# Saved Jobs
# ---------------------------------------------------------------------------


def save_job(job_id: int, notes: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO saved_jobs (job_id, notes) VALUES (?, ?)",
            (job_id, notes),
        )


def get_saved_jobs() -> list[dict]:
    sql = """
        SELECT j.*, sj.notes, sj.saved_at,
               GROUP_CONCAT(s.canonical_name, '|') AS skills
        FROM saved_jobs sj
        JOIN jobs   j  ON sj.job_id   = j.id
        LEFT JOIN job_skills js ON j.id = js.job_id
        LEFT JOIN skills     s  ON js.skill_id = s.id
        GROUP BY j.id
        ORDER BY sj.saved_at DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql).fetchall()]


# ---------------------------------------------------------------------------
# Skill Snapshots (for trend tracking)
# ---------------------------------------------------------------------------


def take_skill_snapshot() -> None:
    today = date.today().isoformat()
    sql = """
        INSERT OR REPLACE INTO skill_snapshots (snapshot_date, skill_id, job_count)
        SELECT ?, skill_id, COUNT(DISTINCT job_id)
        FROM job_skills
        GROUP BY skill_id
    """
    with get_connection() as conn:
        conn.execute(sql, (today,))
    logger.info("Skill snapshot taken for %s", today)


def get_skill_trend(days: int = 30) -> list[dict]:
    sql = """
        SELECT ss.snapshot_date, s.canonical_name, s.category, ss.job_count
        FROM skill_snapshots ss
        JOIN skills s ON ss.skill_id = s.id
        WHERE ss.snapshot_date >= date('now', ?)
        ORDER BY ss.snapshot_date, ss.job_count DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, (f"-{days} days",)).fetchall()]
