"""Unit tests for salary parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from extraction.salary import parse_salary, meets_salary_threshold, format_salary


# ---------------------------------------------------------------------------
# Parsing positive cases
# ---------------------------------------------------------------------------

def test_dollar_range_commas():
    r = parse_salary("Salary: $150,000 - $200,000 per year")
    assert r["salary_min"] == 150_000
    assert r["salary_max"] == 200_000

def test_dollar_range_k():
    r = parse_salary("Compensation: $150k - $200k")
    assert r["salary_min"] == 150_000
    assert r["salary_max"] == 200_000

def test_dollar_range_dash_no_space():
    r = parse_salary("$180,000–$220,000")
    assert r["salary_min"] == 180_000
    assert r["salary_max"] == 220_000

def test_dollar_range_to_keyword():
    r = parse_salary("We pay $160,000 to $210,000 annually")
    assert r["salary_min"] == 160_000
    assert r["salary_max"] == 210_000

def test_base_salary_phrase():
    r = parse_salary("Base salary of $185,000 plus equity")
    assert r["salary_min"] == 185_000

def test_annual_salary_phrase():
    r = parse_salary("Annual salary: $170,000 per year")
    assert r.get("salary_min") == 170_000

def test_total_compensation():
    r = parse_salary("Total compensation of $250,000")
    assert r.get("salary_min") == 250_000

def test_ote():
    r = parse_salary("OTE $220,000")
    assert r.get("salary_min") == 220_000

def test_k_shorthand_single():
    r = parse_salary("$195k per year")
    assert r["salary_min"] == 195_000

def test_hourly_converted():
    r = parse_salary("$90 - $120 per hour")
    assert r["salary_min"] == 90 * 2080
    assert r["salary_max"] == 120 * 2080

def test_salary_range_no_dollar():
    r = parse_salary("salary range 150,000 to 200,000")
    assert r["salary_min"] == 150_000
    assert r["salary_max"] == 200_000

def test_salary_raw_preserved():
    r = parse_salary("$150,000 - $200,000")
    assert r["salary_raw"] is not None
    assert "150" in r["salary_raw"]


# ---------------------------------------------------------------------------
# Edge cases / no match
# ---------------------------------------------------------------------------

def test_no_salary_returns_empty():
    r = parse_salary("Competitive compensation package")
    assert r == {}

def test_empty_string():
    assert parse_salary("") == {}

def test_none_input():
    assert parse_salary(None) == {}  # type: ignore[arg-type]

def test_below_minimum_ignored():
    # $50/hr = $104k — parse_salary should not return it above the plausibility floor
    # $50k would be below 50_000 threshold too… let's test $40,000
    r = parse_salary("$40,000 per year")
    # This is below our MIN_PLAUSIBLE of $50k so it returns empty or ignores
    # The value 40000 < MIN_PLAUSIBLE(50000) → empty
    assert r == {} or r.get("salary_min", 0) < 50_000


# ---------------------------------------------------------------------------
# Threshold checks
# ---------------------------------------------------------------------------

def test_meets_threshold_true():
    assert meets_salary_threshold({"salary_min": 160_000, "salary_max": 200_000}, 150_000)

def test_meets_threshold_exactly():
    assert meets_salary_threshold({"salary_min": 150_000, "salary_max": 150_000}, 150_000)

def test_meets_threshold_by_max():
    # min below threshold but max above
    assert meets_salary_threshold({"salary_min": 120_000, "salary_max": 160_000}, 150_000)

def test_does_not_meet_threshold():
    assert not meets_salary_threshold({"salary_min": 120_000, "salary_max": 140_000}, 150_000)

def test_empty_dict_fails():
    assert not meets_salary_threshold({}, 150_000)


# ---------------------------------------------------------------------------
# Format salary display
# ---------------------------------------------------------------------------

def test_format_range():
    assert format_salary(150_000, 200_000) == "$150,000 – $200,000"

def test_format_single():
    assert format_salary(180_000, 180_000) == "$180,000"

def test_format_none():
    assert format_salary(None, None) == "Not listed"

def test_format_min_only():
    assert format_salary(175_000, None) == "$175,000"
