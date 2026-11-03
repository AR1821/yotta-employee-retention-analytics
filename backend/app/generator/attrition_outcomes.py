
import csv
import json
import math
import random

from pathlib import Path
from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Employee,
    EngagementSurvey,
    WorkloadSnapshot,
    PromotionHistory,
    AttritionOutcome,
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
rng = random.Random(SEED)

FEATURE_CUTOFF = date(2026, 10, 31)

HORIZON_START = date(2026, 11, 1)
HORIZON_END = date(2027, 10, 31)

VOLUNTARY_RATE = 0.10
INVOLUNTARY_RATE = 0.04

# Project root: Retention Analytics System
PROJECT_ROOT = Path(__file__).resolve().parents[3]

GROUND_TRUTH_DIR = (
    PROJECT_ROOT / "data" / "ground_truth"
)


# --------------------------------------------------
# WEIGHTED SAMPLING
# --------------------------------------------------

def weighted_sample_without_replacement(
    employee_weights,
    count,
):
    """
    Select unique employees using weighted random sampling.

    Higher weight means a higher chance of selection.
    """

    ranked = []

    for employee_id, weight in employee_weights.items():

        random_value = max(rng.random(), 1e-12)

        key = random_value ** (1.0 / weight)

        ranked.append((key, employee_id))

    ranked.sort(reverse=True)

    return {
        employee_id
        for _, employee_id in ranked[:count]
    }


# --------------------------------------------------
# MAIN GENERATOR
# --------------------------------------------------

def generate_attrition_outcomes():

    with SessionLocal() as session:

        # Prevent duplicate generation.
        existing = session.scalar(
            select(AttritionOutcome.outcome_id).limit(1)
        )

        if existing is not None:
            raise RuntimeError(
                "Attrition outcomes already exist. "
                "Refusing to generate duplicate records."
            )

        employees = session.scalars(
            select(Employee).order_by(Employee.employee_id)
        ).all()

        surveys = session.scalars(
            select(EngagementSurvey)
            .where(
                EngagementSurvey.survey_date <= FEATURE_CUTOFF
            )
            .order_by(EngagementSurvey.survey_date)
        ).all()

        workloads = session.scalars(
            select(WorkloadSnapshot)
            .where(
                WorkloadSnapshot.period_end <= FEATURE_CUTOFF
            )
            .order_by(WorkloadSnapshot.period_end)
        ).all()

        promotions = session.scalars(
            select(PromotionHistory)
            .where(
                PromotionHistory.effective_date <= FEATURE_CUTOFF
            )
            .order_by(PromotionHistory.effective_date)
        ).all()

        if not employees:
            raise RuntimeError(
                "No employees found. Run master_data.py first."
            )

        # ------------------------------------------
        # 1. FIND LATEST HISTORICAL SIGNALS
        # ------------------------------------------

        latest_surveys = {}
        latest_workloads = {}
        latest_promotions = {}

        for survey in surveys:
            latest_surveys[survey.employee_id] = survey

        for workload in workloads:
            latest_workloads[workload.employee_id] = workload

        for promotion in promotions:
            latest_promotions[promotion.employee_id] = promotion

        # ------------------------------------------
        # 2. CALCULATE SYNTHETIC SAMPLING WEIGHTS
        # ------------------------------------------

        employee_weights = {}

        for employee in employees:

            weight = 1.0

            survey = latest_surveys.get(
                employee.employee_id
            )

            workload = latest_workloads.get(
                employee.employee_id
            )

            promotion = latest_promotions.get(
                employee.employee_id
            )

            # Lower engagement increases the synthetic
            # chance of voluntary exit.
            #
            # Missing survey = neutral contribution.
            if (
                survey is not None
                and survey.response_status == "COMPLETED"
                and survey.engagement_score is not None
            ):
                weight += (
                    (10 - survey.engagement_score) * 0.12
                )

            # Higher capacity utilization increases weight.
            if workload is not None:
                weight += (
                    max(
                        0,
                        workload.capacity_utilization_pct - 80
                    ) * 0.02
                )

                # Sustained long working hours add a smaller
                # contribution.
                weight += (
                    max(0, workload.avg_weekly_hours - 45)
                    * 0.03
                )

            # A recent career move slightly reduces the
            # synthetic voluntary-exit weight.
            if promotion is not None:
                days_since_promotion = (
                    FEATURE_CUTOFF - promotion.effective_date
                ).days

                if 0 <= days_since_promotion <= 180:
                    weight *= 0.85

            employee_weights[employee.employee_id] = max(
                0.2,
                weight
            )

        # ------------------------------------------
        # 3. SELECT OUTCOME GROUPS
        # ------------------------------------------

        total_employees = len(employees)

        voluntary_count = round(
            total_employees * VOLUNTARY_RATE
        )

        involuntary_count = round(
            total_employees * INVOLUNTARY_RATE
        )

        voluntary_ids = weighted_sample_without_replacement(
            employee_weights,
            voluntary_count,
        )

        remaining_ids = [
            employee.employee_id
            for employee in employees
            if employee.employee_id not in voluntary_ids
        ]

        involuntary_ids = set(
            rng.sample(
                remaining_ids,
                min(involuntary_count, len(remaining_ids)),
            )
        )

        # ------------------------------------------
        # 4. GENERATE OUTCOME RECORDS
        # ------------------------------------------

        horizon_days = (
            HORIZON_END - HORIZON_START
        ).days

        outcome_records = []
        ground_truth_records = []

        for employee in employees:

            employee_id = employee.employee_id

            if employee_id in voluntary_ids:

                separation_type = "VOLUNTARY"
                outcome_label = True

            elif employee_id in involuntary_ids:

                separation_type = "INVOLUNTARY"
                outcome_label = False

            else:

                separation_type = "NO_EXIT"
                outcome_label = False

            if separation_type == "NO_EXIT":
                outcome_date = None
            else:
                outcome_date = (
                    HORIZON_START
                    + timedelta(
                        days=rng.randint(0, horizon_days)
                    )
                )

            outcome_id = f"OUT-{employee_id}-2026"

            outcome_records.append(
                AttritionOutcome(
                    outcome_id=outcome_id,
                    employee_id=employee_id,
                    horizon_start=HORIZON_START,
                    horizon_end=HORIZON_END,
                    outcome_label=outcome_label,
                    separation_type=separation_type,
                    outcome_date=outcome_date,
                )
            )

            ground_truth_records.append(
                {
                    "outcome_id": outcome_id,
                    "employee_id": employee_id,
                    "horizon_start": HORIZON_START.isoformat(),
                    "horizon_end": HORIZON_END.isoformat(),
                    "outcome_label": outcome_label,
                    "separation_type": separation_type,
                    "outcome_date": (
                        outcome_date.isoformat()
                        if outcome_date else None
                    ),
                }
            )

        # ------------------------------------------
        # 5. SAVE TO DATABASE
        # ------------------------------------------

        session.add_all(outcome_records)
        session.commit()

        # ------------------------------------------
        # 6. EXPORT SEPARATE GROUND TRUTH FILES
        # ------------------------------------------

        GROUND_TRUTH_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        csv_path = (
            GROUND_TRUTH_DIR / "attrition_ground_truth.csv"
        )

        json_path = (
            GROUND_TRUTH_DIR / "attrition_ground_truth.json"
        )

        fieldnames = list(ground_truth_records[0].keys())

        with open(
            csv_path,
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(ground_truth_records)

        with open(
            json_path,
            "w",
            encoding="utf-8",
        ) as json_file:

            json.dump(
                ground_truth_records,
                json_file,
                indent=4,
            )

        # ------------------------------------------
        # 7. SUMMARY
        # ------------------------------------------

        voluntary_total = len(voluntary_ids)
        involuntary_total = len(involuntary_ids)

        no_exit_total = (
            total_employees
            - voluntary_total
            - involuntary_total
        )

        actual_voluntary_rate = (
            voluntary_total / total_employees * 100
        )

        print("\nAttrition outcomes generated successfully!")

        print(f"Total employees: {total_employees}")
        print(f"Voluntary exits: {voluntary_total}")
        print(f"Involuntary exits: {involuntary_total}")
        print(f"No exit: {no_exit_total}")

        print(
            f"Voluntary attrition rate: "
            f"{actual_voluntary_rate:.2f}%"
        )

        print(f"\nGround truth CSV: {csv_path}")
        print(f"Ground truth JSON: {json_path}")


if __name__ == "__main__":
    generate_attrition_outcomes()
