
import csv
import json
from pathlib import Path
from collections import Counter
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "support_assessments.csv"
REPORT_FILE = PROJECT_ROOT / "data" / "processed" / "support_validation_report.json"
ISSUES_FILE = PROJECT_ROOT / "data" / "processed" / "support_validation_issues.csv"

EXPECTED_ROWS = 10_000
CUTOFF_DATE = date(2026, 10, 31)

REQUIRED_COLUMNS = {
    "employee_id",
    "feature_cutoff_date",
    "rule_version",
    "engagement_component_score",
    "workload_component_score",
    "career_component_score",
    "support_priority_score",
    "priority_level",
    "reason_codes",
    "data_limitations",
    "human_review_required",
    "human_reviewed",
    "assessment_status",
}

issues = []
priority_counts = Counter()


def add_issue(row_number, employee_id, check, message):
    issues.append({
        "row_number": row_number,
        "employee_id": employee_id,
        "check": check,
        "message": message,
    })


def parse_score(row, column, row_number):
    try:
        value = float(row[column])
        if not value.is_integer():
            raise ValueError("Score must be a whole number.")
        return int(value)
    except (ValueError, TypeError):
        add_issue(
            row_number,
            row.get("employee_id", ""),
            column,
            f"Invalid score value: {row.get(column)}"
        )
        return None


def expected_priority(score):
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MODERATE"
    return "ROUTINE"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Assessment file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        columns = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - columns

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        rows = list(reader)

    if len(rows) != EXPECTED_ROWS:
        add_issue(
            0, "", "row_count",
            f"Expected {EXPECTED_ROWS} rows, found {len(rows)}."
        )

    seen_employee_ids = set()

    for row_number, row in enumerate(rows, start=2):
        employee_id = row.get("employee_id", "").strip()

        # 1. Employee ID checks
        if not employee_id:
            add_issue(row_number, employee_id, "employee_id",
                      "Employee ID is missing.")
        elif employee_id in seen_employee_ids:
            add_issue(row_number, employee_id, "duplicate_employee",
                      "Duplicate employee assessment found.")
        seen_employee_ids.add(employee_id)

        # 2. Score checks
        engagement = parse_score(
            row, "engagement_component_score", row_number
        )
        workload = parse_score(
            row, "workload_component_score", row_number
        )
        career = parse_score(
            row, "career_component_score", row_number
        )
        total = parse_score(
            row, "support_priority_score", row_number
        )

        if engagement is not None and not 0 <= engagement <= 40:
            add_issue(row_number, employee_id, "engagement_score",
                      f"Score outside 0-40: {engagement}")

        if workload is not None and not 0 <= workload <= 40:
            add_issue(row_number, employee_id, "workload_score",
                      f"Score outside 0-40: {workload}")

        if career is not None and not 0 <= career <= 20:
            add_issue(row_number, employee_id, "career_score",
                      f"Score outside 0-20: {career}")

        if total is not None and not 0 <= total <= 100:
            add_issue(row_number, employee_id, "total_score",
                      f"Score outside 0-100: {total}")

        # 3. Total must equal component sum
        if None not in (engagement, workload, career, total):
            calculated_total = engagement + workload + career

            if total != calculated_total:
                add_issue(
                    row_number, employee_id, "score_calculation",
                    f"Total is {total}, but components sum to "
                    f"{calculated_total}."
                )

            # 4. Priority classification
            expected = expected_priority(total)
            actual = row.get("priority_level", "").strip().upper()

            priority_counts[actual] += 1

            if actual != expected:
                add_issue(
                    row_number, employee_id, "priority_classification",
                    f"Expected {expected}, found {actual}."
                )

        # 5. Explainability checks
        reasons = [
            code.strip()
            for code in row.get("reason_codes", "").split("|")
            if code.strip()
        ]

        if total is not None and total > 0 and not reasons:
            add_issue(
                row_number, employee_id, "missing_reason_codes",
                "Positive support score has no explanation."
            )

        if total == 0 and reasons:
            add_issue(
                row_number, employee_id, "zero_score_reasons",
                "Zero score unexpectedly contains reason codes."
            )

        # 6. Human-review checks
        if row.get("human_review_required", "").strip().lower() != "true":
            add_issue(
                row_number, employee_id, "human_review_required",
                "Human review must be required."
            )

        if row.get("human_reviewed", "").strip().lower() != "false":
            add_issue(
                row_number, employee_id, "human_reviewed",
                "Generated assessment must not be pre-marked as reviewed."
            )

        if row.get("assessment_status", "").strip() != "PENDING_HUMAN_REVIEW":
            add_issue(
                row_number, employee_id, "assessment_status",
                "Assessment must be pending human review."
            )

        # 7. Feature cutoff check
        try:
            cutoff = date.fromisoformat(row["feature_cutoff_date"])
            if cutoff != CUTOFF_DATE:
                add_issue(
                    row_number, employee_id, "feature_cutoff_date",
                    f"Expected {CUTOFF_DATE}, found {cutoff}."
                )
        except (ValueError, TypeError, KeyError):
            add_issue(
                row_number, employee_id, "feature_cutoff_date",
                "Invalid or missing feature cutoff date."
            )

        if not row.get("rule_version", "").strip():
            add_issue(row_number, employee_id, "rule_version",
                      "Rule version is missing.")

    # 8. Write issue report
    ISSUES_FILE.parent.mkdir(parents=True, exist_ok=True)

    with ISSUES_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["row_number", "employee_id", "check", "message"]
        )
        writer.writeheader()
        writer.writerows(issues)

    # 9. Write summary report
    report = {
        "total_assessments": len(rows),
        "unique_employee_ids": len(seen_employee_ids),
        "priority_distribution": dict(priority_counts),
        "validation_errors": len(issues),
        "passed": len(issues) == 0,
        "checks": [
            "row_count",
            "unique_employee_ids",
            "score_ranges",
            "component_sum",
            "priority_classification",
            "reason_code_explainability",
            "human_review_requirements",
            "assessment_status",
            "feature_cutoff_date",
            "rule_version",
        ],
    }

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\n===== SUPPORT ASSESSMENT VALIDATION =====")
    print(f"Assessments: {len(rows)}")
    print(f"Unique employees: {len(seen_employee_ids)}")
    print(f"Priority distribution: {dict(priority_counts)}")
    print(f"Validation errors: {len(issues)}")
    print(f"Passed: {len(issues) == 0}")
    print(f"\nReport: {REPORT_FILE}")
    print(f"Issues: {ISSUES_FILE}")


if __name__ == "__main__":
    main()
