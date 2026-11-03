
import csv
from pathlib import Path


RULE_VERSION = "1.0"
ENGAGEMENT_MAX = 40
WORKLOAD_MAX = 40
CAREER_MAX = 20


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "employee_features.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "support_assessments.csv"
)


def number(value):
    """Convert CSV values into numbers while preserving missing values."""
    if value is None or value == "":
        return None
    return float(value)


def calculate_engagement_score(row):
    score = 0
    reasons = []

    latest = number(row.get("latest_engagement"))
    decline = number(row.get("engagement_decline"))

    # Low latest engagement signal
    if latest is not None:
        if latest <= 4:
            score += 20
            reasons.append("LOW_LATEST_ENGAGEMENT")
        elif latest <= 5.5:
            score += 12
            reasons.append("BELOW_EXPECTED_ENGAGEMENT")
        elif latest <= 6.5:
            score += 6
            reasons.append("MODERATE_ENGAGEMENT_SIGNAL")

    # Recent engagement decline signal
    if decline is not None:
        if decline >= 2:
            score += 20
            reasons.append("SIGNIFICANT_ENGAGEMENT_DECLINE")
        elif decline >= 1:
            score += 12
            reasons.append("ENGAGEMENT_DECLINE")
        elif decline >= 0.5:
            score += 6
            reasons.append("SLIGHT_ENGAGEMENT_DECLINE")

    return min(score, ENGAGEMENT_MAX), reasons


def calculate_workload_score(row):
    score = 0
    reasons = []

    hours = number(row.get("average_weekly_hours"))
    utilization = number(
        row.get("average_capacity_utilization_pct")
    )

    # Average weekly working hours
    if hours is not None:
        if hours >= 50:
            score += 20
            reasons.append("VERY_HIGH_AVERAGE_WORKING_HOURS")
        elif hours >= 45:
            score += 12
            reasons.append("HIGH_AVERAGE_WORKING_HOURS")
        elif hours >= 40:
            score += 5
            reasons.append("ELEVATED_AVERAGE_WORKING_HOURS")

    # Average capacity utilization
    if utilization is not None:
        if utilization >= 110:
            score += 20
            reasons.append("VERY_HIGH_CAPACITY_UTILIZATION")
        elif utilization >= 100:
            score += 14
            reasons.append("HIGH_CAPACITY_UTILIZATION")
        elif utilization >= 90:
            score += 8
            reasons.append("ELEVATED_CAPACITY_UTILIZATION")

    return min(score, WORKLOAD_MAX), reasons


def calculate_career_score(row):
    score = 0
    reasons = []

    promotion_count = int(row.get("promotion_count") or 0)
    days_since = row.get("days_since_last_promotion")

    # No recorded promotion history is not negative evidence.
    if promotion_count == 0 or days_since in (None, ""):
        return 0, reasons

    days_since = int(days_since)

    if days_since >= 730:
        score = 20
        reasons.append("LONG_TIME_SINCE_LAST_RECORDED_PROMOTION")
    elif days_since >= 540:
        score = 15
        reasons.append("EXTENDED_TIME_SINCE_LAST_PROMOTION")
    elif days_since >= 365:
        score = 10
        reasons.append("TIME_SINCE_LAST_PROMOTION")
    elif days_since >= 180:
        score = 5
        reasons.append("RECENT_CAREER_PROGRESSION_GAP")

    return score, reasons


def assign_priority(score):
    if score >= 60:
        return "HIGH"

    if score >= 30:
        return "MODERATE"

    return "ROUTINE"


def create_assessment(row):
    engagement_score, engagement_reasons = (
        calculate_engagement_score(row)
    )

    workload_score, workload_reasons = (
        calculate_workload_score(row)
    )

    career_score, career_reasons = (
        calculate_career_score(row)
    )

    total_score = (
        engagement_score
        + workload_score
        + career_score
    )

    reasons = (
        engagement_reasons
        + workload_reasons
        + career_reasons
    )

    limitations = []

    if row.get("latest_engagement") in (None, ""):
        limitations.append("NO_COMPLETED_ENGAGEMENT_SURVEY")

    if row.get("promotion_count", "0") in ("", "0"):
        limitations.append("NO_RECORDED_PROMOTION_HISTORY")

    if row.get("average_weekly_hours") in (None, ""):
        limitations.append("NO_WORKLOAD_DATA")

    return {
        "employee_id": row["employee_id"],
        "feature_cutoff_date": row["feature_cutoff_date"],

        "rule_version": RULE_VERSION,

        "engagement_component_score": engagement_score,
        "workload_component_score": workload_score,
        "career_component_score": career_score,

        "support_priority_score": total_score,
        "priority_level": assign_priority(total_score),

        "reason_codes": "|".join(reasons),
        "data_limitations": "|".join(limitations),

        "human_review_required": True,
        "human_reviewed": False,
        "assessment_status": "PENDING_HUMAN_REVIEW",
    }


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        feature_rows = list(reader)

    if not feature_rows:
        raise ValueError("No employee feature records found.")

    assessments = [
        create_assessment(row)
        for row in feature_rows
    ]

    with open(
        OUTPUT_FILE, "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(assessments[0].keys())
        )
        writer.writeheader()
        writer.writerows(assessments)

    # Summary
    priority_counts = {
        "HIGH": 0,
        "MODERATE": 0,
        "ROUTINE": 0,
    }

    for assessment in assessments:
        priority_counts[assessment["priority_level"]] += 1

    print("\n========== SUPPORT SCORING REPORT ==========")
    print(f"Employees assessed: {len(assessments)}")
    print(f"Rule version: {RULE_VERSION}")
    print(f"High priority: {priority_counts['HIGH']}")
    print(f"Moderate priority: {priority_counts['MODERATE']}")
    print(f"Routine priority: {priority_counts['ROUTINE']}")
    print("Human review required: All assessments")
    print(f"Output: {OUTPUT_FILE}")
    print("============================================")


if __name__ == "__main__":
    main()
