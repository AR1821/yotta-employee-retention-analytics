
import csv
from pathlib import Path
from datetime import date


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_FILE = (
    PROJECT_ROOT / "data" / "processed" / "employee_features.csv"
)

EXPECTED_EMPLOYEES = 10_000
FEATURE_CUTOFF = date(2026, 10, 31)


def to_number(value):
    if value is None or value == "":
        return None
    return float(value)


def main():
    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_FILE}"
        )

    with open(FEATURE_FILE, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        columns = reader.fieldnames or []

    errors = []

    # 1. Row count
    if len(rows) != EXPECTED_EMPLOYEES:
        errors.append(
            f"Expected {EXPECTED_EMPLOYEES} rows, found {len(rows)}."
        )

    # 2. Required columns
    required_columns = {
        "employee_id",
        "feature_cutoff_date",
        "tenure_days",
        "average_engagement",
        "latest_engagement",
        "previous_engagement",
        "engagement_change",
        "survey_response_rate_pct",
        "average_weekly_hours",
        "average_capacity_utilization_pct",
        "promotion_count",
        "days_since_last_promotion",
    }

    missing_columns = required_columns - set(columns)

    if missing_columns:
        errors.append(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # 3. Unique employee IDs
    employee_ids = [row["employee_id"] for row in rows]

    if len(employee_ids) != len(set(employee_ids)):
        errors.append("Duplicate employee IDs detected.")

    # 4. Feature cutoff
    for row in rows:
        if row["feature_cutoff_date"] != FEATURE_CUTOFF.isoformat():
            errors.append(
                f"{row['employee_id']}: incorrect feature cutoff date."
            )

    # 5. Engagement score range
    engagement_columns = [
        "average_engagement",
        "latest_engagement",
        "previous_engagement",
    ]

    for row in rows:
        for column in engagement_columns:
            value = to_number(row[column])

            if value is not None and not 1 <= value <= 10:
                errors.append(
                    f"{row['employee_id']}: {column} outside 1–10."
                )

    # 6. Survey response rate
    for row in rows:
        rate = to_number(row["survey_response_rate_pct"])

        if rate is not None and not 0 <= rate <= 100:
            errors.append(
                f"{row['employee_id']}: invalid survey response rate."
            )

    # 7. Survey missingness consistency
    for row in rows:
        total = int(row["total_surveys"])
        completed = int(row["completed_surveys"])
        missing = int(row["missing_surveys"])

        if completed + missing != total:
            errors.append(
                f"{row['employee_id']}: survey counts do not add up."
            )

        if completed == 0 and row["average_engagement"] != "":
            errors.append(
                f"{row['employee_id']}: no completed surveys, "
                "but average engagement is present."
            )

        if total == 0 and row["survey_response_rate_pct"] != "":
            errors.append(
                f"{row['employee_id']}: no surveys, "
                "but response rate is present."
            )

    # 8. Workload values
    for row in rows:
        hours = to_number(row["average_weekly_hours"])
        utilization = to_number(
            row["average_capacity_utilization_pct"]
        )

        if hours is not None and hours < 0:
            errors.append(
                f"{row['employee_id']}: negative average weekly hours."
            )

        if utilization is not None and utilization < 0:
            errors.append(
                f"{row['employee_id']}: negative capacity utilization."
            )

    # 9. Promotion consistency
    for row in rows:
        promotion_count = int(row["promotion_count"])
        days_since = row["days_since_last_promotion"]

        if promotion_count == 0 and days_since != "":
            errors.append(
                f"{row['employee_id']}: no promotions, "
                "but days since promotion is present."
            )

        if promotion_count > 0 and days_since == "":
            errors.append(
                f"{row['employee_id']}: promotion exists, "
                "but last promotion date is missing."
            )

        if days_since != "" and int(days_since) < 0:
            errors.append(
                f"{row['employee_id']}: negative days since promotion."
            )

    # 10. Prevent target leakage through exported columns
    forbidden_terms = (
        "outcome_label",
        "separation_type",
        "outcome_date",
        "attrition_outcome",
        "ground_truth",
    )

    leaked_columns = [
        column for column in columns
        if any(term in column.lower() for term in forbidden_terms)
    ]

    if leaked_columns:
        errors.append(
            f"Possible target leakage columns: {leaked_columns}"
        )

    # Final report
    print("\n========== FEATURE QUALITY REPORT ==========")
    print(f"Feature records: {len(rows)}")
    print(f"Feature columns: {len(columns)}")
    print(f"Unique employees: {len(set(employee_ids))}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nDetected problems:")
        for error in errors[:30]:
            print(f"[ERROR] {error}")

        print("\nFeature quality: FAILED")
        raise SystemExit(1)

    print("\nFeature quality: PASSED")
    print("All implemented feature checks passed.")


if __name__ == "__main__":
    main()
