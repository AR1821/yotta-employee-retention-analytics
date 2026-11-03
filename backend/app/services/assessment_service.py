
import csv
from pathlib import Path
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ASSESSMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "support_assessments.csv"
)


@lru_cache(maxsize=1)
def load_assessments():
    """Load employee support assessments from the processed CSV."""

    if not ASSESSMENT_FILE.exists():
        raise FileNotFoundError(
            f"Assessment file not found: {ASSESSMENT_FILE}"
        )

    with ASSESSMENT_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)
        return {
            row["employee_id"]: row
            for row in reader
        }


def get_assessment(employee_id: str):
    """Return one employee's support assessment."""

    assessments = load_assessments()
    return assessments.get(employee_id)


def get_all_assessments():
    """Return all support assessments."""

    return list(load_assessments().values())


def refresh_assessments():
    """Clear the cache after regenerating the assessment CSV."""

    load_assessments.cache_clear()
