
import csv
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/api/data-quality",
    tags=["Data Quality"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

MAX_ISSUES = 100

# Each saved report and the validation script that produces it.
REPORTS = {
    "dataset": {
        "title": "Synthetic Dataset Validation",
        "script": "validate_data.py",
        "report": PROCESSED_DIR / "validation_report.json",
        "issues": PROCESSED_DIR / "validation_issues.csv",
    },
    "assessments": {
        "title": "Support Assessment Validation",
        "script": "validate_support_assessments.py",
        "report": PROCESSED_DIR / "support_validation_report.json",
        "issues": PROCESSED_DIR / "support_validation_issues.csv",
    },
}

EDGE_CASE_FILE = DATA_DIR / "edge_cases" / "edge_case_catalog.json"


def read_issues(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_report(key: str, config: dict):
    if not config["report"].exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"{config['title']} report not found. "
                f"Run {config['script']} first."
            ),
        )

    with config["report"].open("r", encoding="utf-8") as file:
        report = json.load(file)

    issues = read_issues(config["issues"])

    return {
        "key": key,
        "title": config["title"],
        "script": config["script"],
        "passed": bool(report.get("passed")),
        "error_count": report.get(
            "validation_errors", report.get("error_count", 0)
        ),
        "warning_count": report.get("warning_count", 0),
        "report": report,
        "issues_file_available": issues is not None,
        "total_issues": len(issues or []),
        "issues": (issues or [])[:MAX_ISSUES],
    }


@router.get("/summary")
def get_data_quality_summary():
    """Return the saved validation reports and labelled edge cases."""

    reports = [
        load_report(key, config)
        for key, config in REPORTS.items()
    ]

    edge_cases = []

    if EDGE_CASE_FILE.exists():
        with EDGE_CASE_FILE.open("r", encoding="utf-8") as file:
            edge_cases = json.load(file).get("edge_cases", [])

    return {
        "passed": all(item["passed"] for item in reports),
        "reports": reports,
        "edge_cases": edge_cases,
    }
