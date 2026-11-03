
import random
from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Employee,
    Role,
    Team,
    CompensationBand,
    EmployeeAssignmentHistory,
    EmployeeCompensationHistory,
    TenureSnapshot,
    WorkloadSnapshot,
    EngagementSurvey,
    PromotionHistory,
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
rng = random.Random(SEED)

DATA_START = date(2024, 11, 1)
DATA_END = date(2026, 10, 31)

# Period start, period end, year, quarter
PERIODS = [
    (date(2024, 11, 1), date(2024, 12, 31), 2024, 4),
    (date(2025, 1, 1), date(2025, 3, 31), 2025, 1),
    (date(2025, 4, 1), date(2025, 6, 30), 2025, 2),
    (date(2025, 7, 1), date(2025, 9, 30), 2025, 3),
    (date(2025, 10, 1), date(2025, 12, 31), 2025, 4),
    (date(2026, 1, 1), date(2026, 3, 31), 2026, 1),
    (date(2026, 4, 1), date(2026, 6, 30), 2026, 2),
    (date(2026, 7, 1), date(2026, 9, 30), 2026, 3),
    (date(2026, 10, 1), date(2026, 10, 31), 2026, 4),
]


# --------------------------------------------------
# MAIN GENERATOR
# --------------------------------------------------

def generate_historical_data():

    with SessionLocal() as session:

        # Prevent accidental duplicate generation.
        existing = session.scalar(
            select(TenureSnapshot.snapshot_id).limit(1)
        )

        if existing:
            raise RuntimeError(
                "Historical data already exists. "
                "Skipping to prevent duplicate records."
            )

        employees = session.scalars(
            select(Employee).order_by(Employee.employee_id)
        ).all()

        roles = session.scalars(
            select(Role).order_by(Role.role_id)
        ).all()

        bands = session.scalars(
            select(CompensationBand).order_by(
                CompensationBand.band_id
            )
        ).all()

        assignments = session.scalars(
            select(EmployeeAssignmentHistory).order_by(
                EmployeeAssignmentHistory.employee_id
            )
        ).all()

        compensation_histories = session.scalars(
            select(EmployeeCompensationHistory).order_by(
                EmployeeCompensationHistory.employee_id
            )
        ).all()

        if not employees:
            raise RuntimeError(
                "No employees found. Run master_data.py first."
            )

        if not assignments or not compensation_histories:
            raise RuntimeError(
                "Missing assignment or compensation history."
            )

        # Lookups
        roles_by_id = {r.role_id: r for r in roles}

        bands_by_level = {
            b.job_level: b for b in bands
        }

        assignment_by_employee = {
            a.employee_id: a for a in assignments
            if a.effective_end is None
        }

        compensation_by_employee = {
            c.employee_id: c for c in compensation_histories
            if c.effective_end is None
        }

        roles_by_department = defaultdict(list)

        for role in roles:
            roles_by_department[role.department].append(role)

        for department in roles_by_department:
            roles_by_department[department].sort(
                key=lambda r: (r.job_level, r.role_id)
            )

        tenure_records = []
        workload_records = []
        survey_records = []
        promotion_records = []

        survey_counters = defaultdict(int)

        # --------------------------------------------------
        # 1. PROMOTION AND LATERAL MOVE HISTORY
        # --------------------------------------------------

        for employee in employees:

            # Approximately 6% of employees receive a career move.
            if rng.random() >= 0.06:
                continue

            current_assignment = assignment_by_employee.get(
                employee.employee_id
            )

            current_compensation = compensation_by_employee.get(
                employee.employee_id
            )

            if not current_assignment or not current_compensation:
                continue

            current_role = roles_by_id[current_assignment.role_id]

            # Only consider moves after the employee has been
            # employed for at least 90 days.
            earliest_move = employee.hire_date + timedelta(days=90)

            if earliest_move >= DATA_END:
                continue

            move_date = earliest_move + timedelta(
                days=rng.randint(
                    0,
                    (DATA_END - earliest_move).days
                )
            )

            same_department_roles = roles_by_department[
                current_role.department
            ]

            higher_roles = [
                role for role in same_department_roles
                if role.job_level > current_role.job_level
            ]

            if higher_roles:
                new_role = higher_roles[0]
                move_type = "PROMOTION"
            else:
                lateral_roles = [
                    role for role in roles
                    if role.department != current_role.department
                    and role.job_level == current_role.job_level
                ]

                if not lateral_roles:
                    continue

                new_role = rng.choice(lateral_roles)
                move_type = "LATERAL_MOVE"

            new_band = bands_by_level[new_role.job_level]

            # Close previous assignment and compensation periods.
            current_assignment.effective_end = (
                move_date - timedelta(days=1)
            )

            current_compensation.effective_end = (
                move_date - timedelta(days=1)
            )

            promotion_id = (
                f"PROM-{employee.employee_id}-001"
            )

            promotion_records.append(
                PromotionHistory(
                    promotion_id=promotion_id,
                    employee_id=employee.employee_id,
                    from_role_id=current_role.role_id,
                    to_role_id=new_role.role_id,
                    effective_date=move_date,
                    promotion_type=move_type,
                )
            )

            # Create the new assignment.
            new_assignment = EmployeeAssignmentHistory(
                assignment_id=f"ASG-{employee.employee_id}-002",
                employee_id=employee.employee_id,
                role_id=new_role.role_id,
                team_id=current_assignment.team_id,
                effective_start=move_date,
                effective_end=None,
            )

            # Create the new compensation history.
            new_compensation = EmployeeCompensationHistory(
                compensation_history_id=(
                    f"COMP-{employee.employee_id}-002"
                ),
                employee_id=employee.employee_id,
                band_id=new_band.band_id,
                effective_start=move_date,
                effective_end=None,
            )

            session.add(new_assignment)
            session.add(new_compensation)

        session.flush()

        # --------------------------------------------------
        # 2. QUARTERLY SNAPSHOTS, WORKLOAD AND SURVEYS
        # --------------------------------------------------

        for employee in employees:

            for period_start, period_end, year, quarter in PERIODS:

                if employee.hire_date > period_end:
                    continue

                # No record can precede the employee's hire date.
                actual_start = max(
                    period_start,
                    employee.hire_date
                )

                actual_end = period_end

                if actual_start > actual_end:
                    continue

                quarter_label = f"{year}Q{quarter}"

                # ------------------------------------------
                # TENURE SNAPSHOT
                # ------------------------------------------

                tenure_days = (
                    actual_end - employee.hire_date
                ).days

                tenure_months = (
                    (actual_end.year - employee.hire_date.year) * 12
                    + actual_end.month
                    - employee.hire_date.month
                )

                tenure_records.append(
                    TenureSnapshot(
                        snapshot_id=(
                            f"SNAP-{employee.employee_id}-"
                            f"{quarter_label}"
                        ),
                        employee_id=employee.employee_id,
                        as_of_date=actual_end,
                        tenure_days=tenure_days,
                        tenure_months=max(0, tenure_months),
                    )
                )

                # ------------------------------------------
                # WORKLOAD SNAPSHOT
                # ------------------------------------------

                avg_weekly_hours = round(
                    rng.uniform(32, 55), 2
                )

                task_count = rng.randint(15, 80)

                capacity_utilization = round(
                    rng.uniform(50, 125), 2
                )

                workload_records.append(
                    WorkloadSnapshot(
                        workload_id=(
                            f"WORK-{employee.employee_id}-"
                            f"{quarter_label}"
                        ),
                        employee_id=employee.employee_id,
                        period_start=actual_start,
                        period_end=actual_end,
                        avg_weekly_hours=avg_weekly_hours,
                        task_count=task_count,
                        capacity_utilization_pct=(
                            capacity_utilization
                        ),
                    )
                )

                # ------------------------------------------
                # ENGAGEMENT SURVEY
                # ------------------------------------------

                # 18% probability of a missing survey.
                is_missing = rng.random() < 0.18

                survey_counters[year] += 1

                survey_id = (
                    f"SURV-{year}-"
                    f"{survey_counters[year]:06d}"
                )

                if is_missing:
                    engagement_score = None
                    response_status = "MISSING"
                else:
                    engagement_score = rng.randint(3, 10)
                    response_status = "COMPLETED"

                survey_records.append(
                    EngagementSurvey(
                        survey_id=survey_id,
                        employee_id=employee.employee_id,
                        survey_date=actual_end,
                        engagement_score=engagement_score,
                        response_status=response_status,
                    )
                )

        # --------------------------------------------------
        # 3. SAVE ALL GENERATED RECORDS
        # --------------------------------------------------

        session.add_all(promotion_records)
        session.add_all(tenure_records)
        session.add_all(workload_records)
        session.add_all(survey_records)

        session.commit()

        print("\nHistorical data generated successfully!")

        print(f"Employees processed: {len(employees)}")
        print(f"Tenure snapshots: {len(tenure_records)}")
        print(f"Workload snapshots: {len(workload_records)}")
        print(f"Engagement surveys: {len(survey_records)}")
        print(f"Promotions and lateral moves: {len(promotion_records)}")

        missing_surveys = sum(
            1 for record in survey_records
            if record.response_status == "MISSING"
        )

        print(f"Missing surveys: {missing_surveys}")
        print(
            "Completed surveys: "
            f"{len(survey_records) - missing_surveys}"
        )


if __name__ == "__main__":
    generate_historical_data()
