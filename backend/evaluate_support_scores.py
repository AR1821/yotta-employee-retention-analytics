
"""Evaluate support-priority scores against the held-out ground truth.

The scores are built only from data on or before the feature cutoff
(2026-10-31). Ground-truth labels cover the following 12 months and are
read here for the first time, so they cannot leak into the scores.

Run after support_scoring.py:
    python evaluate_support_scores.py
"""

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSESSMENT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "support_assessments.csv"
)
GROUND_TRUTH_FILE = (
    PROJECT_ROOT / "data" / "ground_truth" / "attrition_ground_truth.csv"
)
REPORT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "evaluation_report.json"
)

PRIORITIES = ["HIGH", "MODERATE", "ROUTINE"]


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def roc_auc(scores, labels):
    """Probability that a random leaver outscores a random stayer.

    Uses average ranks, so tied scores count as half.
    """

    ordered = sorted(zip(scores, labels))
    ranks = [0.0] * len(ordered)

    start = 0
    while start < len(ordered):
        end = start
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[start][0]:
            end += 1

        average_rank = (start + end) / 2 + 1
        for index in range(start, end + 1):
            ranks[index] = average_rank

        start = end + 1

    positives = sum(1 for _, label in ordered if label)
    negatives = len(ordered) - positives

    positive_rank_sum = sum(
        rank for rank, (_, label) in zip(ranks, ordered) if label
    )

    return (
        positive_rank_sum - positives * (positives + 1) / 2
    ) / (positives * negatives)


def flagged_metrics(rows, flagged_levels, base_rate):
    flagged = [row for row in rows if row["priority"] in flagged_levels]
    true_positives = sum(row["label"] for row in flagged)
    positives = sum(row["label"] for row in rows)

    precision = true_positives / len(flagged) if flagged else 0.0

    return {
        "flagged_employees": len(flagged),
        "voluntary_leavers_flagged": true_positives,
        "precision": round(precision, 4),
        "recall": round(true_positives / positives, 4),
        "lift_over_base_rate": round(precision / base_rate, 2),
    }


def main():
    assessments = read_csv(ASSESSMENT_FILE)
    ground_truth = {
        row["employee_id"]: row for row in read_csv(GROUND_TRUTH_FILE)
    }

    rows = []
    for assessment in assessments:
        outcome = ground_truth[assessment["employee_id"]]
        rows.append({
            "score": int(assessment["support_priority_score"]),
            "priority": assessment["priority_level"],
            "label": outcome["outcome_label"].strip().lower() == "true",
        })

    total = len(rows)
    leavers = sum(row["label"] for row in rows)
    base_rate = leavers / total

    by_priority = {}
    for level in PRIORITIES:
        group = [row for row in rows if row["priority"] == level]
        group_leavers = sum(row["label"] for row in group)
        rate = group_leavers / len(group) if group else 0.0

        by_priority[level] = {
            "employees": len(group),
            "voluntary_leavers": group_leavers,
            "voluntary_attrition_rate": round(rate, 4),
            "lift_over_base_rate": round(rate / base_rate, 2),
        }

    # Share of leavers found in the top 10% of scores.
    ranked = sorted(rows, key=lambda row: row["score"], reverse=True)
    top_decile = ranked[: total // 10]
    top_decile_leavers = sum(row["label"] for row in top_decile)

    report = {
        "evaluated_employees": total,
        "voluntary_leavers": leavers,
        "base_rate": round(base_rate, 4),
        "roc_auc": round(
            roc_auc([row["score"] for row in rows], [row["label"] for row in rows]),
            4,
        ),
        "by_priority": by_priority,
        "flag_high_only": flagged_metrics(rows, {"HIGH"}, base_rate),
        "flag_high_and_moderate": flagged_metrics(
            rows, {"HIGH", "MODERATE"}, base_rate
        ),
        "top_decile_capture_rate": round(top_decile_leavers / leavers, 4),
        "note": (
            "Synthetic labels were sampled with weights based on "
            "engagement, utilisation and working hours, so these metrics "
            "measure recovery of planted signal, not real-world accuracy."
        ),
    }

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\n========== SUPPORT SCORE EVALUATION ==========")
    print(f"Employees: {total}   Voluntary leavers: {leavers} "
          f"(base rate {base_rate:.1%})")
    print(f"ROC AUC: {report['roc_auc']:.3f}")
    for level, stats in by_priority.items():
        print(f"{level:<9} {stats['employees']:>5} employees  "
              f"attrition {stats['voluntary_attrition_rate']:.1%}  "
              f"lift {stats['lift_over_base_rate']}x")
    high = report["flag_high_only"]
    both = report["flag_high_and_moderate"]
    print(f"Flag HIGH:            precision {high['precision']:.1%}  "
          f"recall {high['recall']:.1%}")
    print(f"Flag HIGH + MODERATE: precision {both['precision']:.1%}  "
          f"recall {both['recall']:.1%}")
    print(f"Top-decile capture: {report['top_decile_capture_rate']:.1%}")
    print(f"\nReport: {REPORT_FILE}")
    print("===============================================")


if __name__ == "__main__":
    main()
