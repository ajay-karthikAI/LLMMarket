# HealthAI Skill Radar

Personal career intelligence dashboard for tracking **real technical skills** required in high-paying US healthcare AI jobs.

## Portfolio project plans

- [SunoPulse Real Data: Music Trend, Social, and Creator Intelligence Platform](docs/suno_real_data_project_plan.md) — the recommended real-data version using ListenBrainz, MusicBrainz, Last.fm, and YouTube public data.
- [SunoPulse: Real-Time Content, Social, and Creator Intelligence Platform](docs/suno_content_social_ds_project_plan.md) — a Suno-tailored data science project roadmap covering real-time events, APIs, database design, content trends, creator analytics, experimentation, and dashboarding.

---

## What it does

- Pulls **live job postings** from Greenhouse, Lever, and Ashby APIs (35+ companies)
- Filters to **US locations** and **$150k+ salary** only
- Extracts skills using **pure regex + dictionary matching** — no LLM inference
- Surfaces the most in-demand skills across 200+ canonical healthcare AI terms
- Tracks skill frequency trends over time (weekly snapshots)
- 4-tab Streamlit dashboard: Live Jobs · Skill Frequency · Interview Prep · Trend Tracking

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install spaCy language model (required for NLP preprocessing)

```bash
python -m spacy download en_core_web_sm
```

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to adjust MIN_SALARY, DB_PATH, etc.
```

### 4. Run the app

```bash
streamlit run app.py
```

---

## First use

1. Open the app in your browser (default: http://localhost:8501)
2. Click **"🔄 Fetch Live Jobs"** in the sidebar
3. The fetcher pulls from all 35+ companies concurrently — takes 30–90 seconds
4. Jobs are filtered to US-only, AI-relevant roles, $150k+ salary
5. Skills are extracted from descriptions and linked to jobs in SQLite

---

## Folder structure

```
LLMarket/
├── app.py                  # Streamlit frontend (4 tabs)
├── requirements.txt
├── README.md
├── .env.example
├── data/                   # SQLite database (auto-created)
│   └── healthai_jobs.db
├── database/
│   └── db.py               # Schema, CRUD, snapshots
├── extraction/
│   ├── skills.py           # 200+ skill canonical dict + regex extractor
│   ├── salary.py           # Salary parsing (ranges, k-notation, hourly)
│   └── location.py         # US location normalisation (12 cities + Remote)
├── jobs/
│   ├── greenhouse.py       # Greenhouse Jobs Board API
│   ├── lever.py            # Lever Postings API
│   ├── ashby.py            # Ashby GraphQL API
│   └── fetcher.py          # Orchestrator: filter, classify, persist
├── analytics/
│   ├── skills_analysis.py  # Frequency, top-paying, co-occurrence, roadmap
│   └── trends.py           # Growth rates, category trends, weekly summaries
├── utils/
│   ├── logging_config.py
│   └── helpers.py          # HTTP retry, HTML cleaner
└── tests/
    ├── test_extraction.py  # 25+ skill extraction unit tests
    └── test_salary.py      # 20+ salary parsing unit tests
```

---

## Supported companies & ATS

| Company | ATS |
|---|---|
| Abridge | Greenhouse |
| Tempus | Greenhouse |
| Flatiron Health | Greenhouse |
| Freenome | Greenhouse |
| Viz.ai | Greenhouse |
| Aidoc | Greenhouse |
| PathAI | Greenhouse |
| Butterfly Network | Greenhouse |
| Recursion | Greenhouse |
| Veeva Systems | Greenhouse |
| Komodo Health | Greenhouse |
| Clarify Health | Greenhouse |
| Innovaccer | Greenhouse |
| Notable Health | Greenhouse |
| Cohere Health | Greenhouse |
| Nuna | Greenhouse |
| Spring Health | Greenhouse |
| Hippocratic AI | Lever |
| Rad AI | Lever |
| Suki AI | Lever |
| Ambience Healthcare | Lever |
| Hyro | Lever |
| Corti | Lever |
| Nabla | Lever |
| OpenEvidence | Ashby |
| Anterior | Ashby |
| Thoughtful AI | Ashby |
| Regard | Ashby |
| Datavant | Ashby |
| + more | |

---

## Skill categories

| Category | Examples |
|---|---|
| LLM Stack | LangChain, LangGraph, RAG, DSPy, MCP, Fine-tuning |
| ML/DL | PyTorch, TensorFlow, JAX, Transformers, Multimodal AI |
| Healthcare | FHIR, HL7, Epic, Clinical NLP, HIPAA, ICD-10, Ambient AI |
| MLOps | Kubernetes, Docker, Airflow, MLflow, CI/CD, LLMOps |
| Data Engineering | SQL, Spark, Databricks, Snowflake, BigQuery, Kafka |
| Cloud | AWS, Azure, GCP |
| Infrastructure | Pinecone, Weaviate, FAISS, vLLM, Ray, Distributed Training |
| Programming | Python, Rust, Go, Scala, C++ |
| Governance | AI Safety, HIPAA, SOC 2, Explainability |

---

## Running tests

```bash
# From the project root
python -m pytest tests/ -v
```

---

## Design principles

- **No hallucination** — skills are only extracted if they appear verbatim in the posting
- **No fabricated salaries** — jobs without parseable salary are discarded
- **No synthetic jobs** — all data comes from live public ATS APIs
- **Deterministic** — same text always produces the same skill set
- **Transparent** — every job links directly to its source posting

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MIN_SALARY` | `150000` | Minimum salary threshold in USD |
| `DB_PATH` | `./data/healthai_jobs.db` | SQLite database path |
| `FETCH_WORKERS` | `4` | Concurrent fetch threads |
| `USER_AGENT` | Mozilla/5.0 | HTTP user agent string |

---

## Notes

- Salary data is sparse in many job APIs. Jobs without explicit salary info in the description or metadata are excluded rather than guessed.
- Company ATS slugs may change over time. If a company returns 0 jobs, they may have changed their slug — check their careers page.
- Trend data accumulates over time with each fetch run (daily snapshots). The trend tab becomes meaningful after a week of daily fetches.
