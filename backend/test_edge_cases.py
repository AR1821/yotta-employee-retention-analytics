
import json
from pathlib import Path
from datetime import date


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "data" / "edge_cases" / "edge_case_catalog.json"


def detect_edge_case(case, cutoff):
    record = case["record"]
    label = case["label"]

    if label == "FUTURE_INFORMATION_LEAKAGE":
        feature_date = date.fromisoformat(record["feature_date"])

        if feature_date > cutoff:
            return "LEAKAGE001: Feature date is after prediction cutoff."

    elif label == "MISSING_SURVEY_TREATED_AS_NEGATIVE":
        if (
            record["response_status"] == "MISSING"
            and record["engagement_score"] is None
            and record["derived_engagement_score"] == 0
            and record["missing_handling"] == "IMPUTED_AS_LOW"
        ):
            return "SURVEY001: Missing response was incorrectly treated as low engagement."

    elif label == "INCONSISTENT_ATTRITION_OUTCOME":
        if (
            record["separation_type"] == "VOLUNTARY"
            and record["outcome_label"] is not True
        ):
            return "OUTCOME001: Voluntary separation has an incorrect outcome label."

    elif label == "UNEXPLAINED_UNREVIEWED_SUPPORT_SCORE":
        if (
            record["support_score"] is not None
            and not record["reason_codes"]
            and record["human_reviewed"] is False
        ):
            return "SUPPORT001: Score has no explanation and has not been human-reviewed."

    return None


def main():
    with open(CATALOG_PATH, "r", encoding="utf-8") as file:
        catalog = json.load(file)

    cutoff = date.fromisoformat(catalog["feature_cutoff"])
    cases = catalog["edge_cases"]

    detected = 0

    print("\n========== EDGE-CASE TEST REPORT ==========")

    for case in cases:
        issue = detect_edge_case(case, cutoff)

        if issue:
            detected += 1
            print(f"[DETECTED] {case['case_id']} | {case['label']}")
            print(f"           {issue}")
        else:
            print(f"[MISSED]   {case['case_id']} | {case['label']}")

    total = len(cases)
    passed = detected == total

    print("-------------------------------------------")
    print(f"Total test cases: {total}")
    print(f"Detected: {detected}")
    print(f"Missed: {total - detected}")
    print(f"Passed: {passed}")
    print("===========================================")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
