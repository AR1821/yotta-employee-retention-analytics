
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

from app.database import SessionLocal
from app.models import (
    Employee,
    Role,
    Team,
    EmployeeAssignmentHistory,
    EngagementSurvey,
    WorkloadSnapshot,
    PromotionHistory,
)


FEATURE_CUTOFF = date(2026, 10, 31)


def build_employee_features(session, cutoff=FEATURE_CUTOFF):
    """
    Build one feature record per employee using information
    available on or before the prediction cutoff.

    AttritionOutcome and future ground-truth labels are
    intentionally not queried or used here.
    """

    employees = session.query(Employee).all()
    roles = session.query(Role).all()
    teams = session.query(Team).all()

    surveys = (
        session.query(EngagementSurvey)
        .filter(EngagementSurvey.survey_date <= cutoff)
        .all()
    )

    workloads = (
        session.query(WorkloadSnapshot)
        .filter(WorkloadSnapshot.period_end <= cutoff)
        .all()
    )

    promotions = (
        session.query(PromotionHistory)
        .filter(PromotionHistory.effective_date <= cutoff)
        .all()
    )

    assignments = (
        session.query(EmployeeAssignmentHistory)
        .filter(EmployeeAssignmentHistory.effective_start <= cutoff)
        .all()
    )

    # Lookup dictionaries
    role_map = {row.role_id: row for row in roles}
    team_map = {row.team_id: row for row in teams}

    # Group historical records by employee
    surveys_by_employee = defaultdict(list)
    workloads_by_employee = defaultdict(list)
    promotions_by_employee = defaultdict(list)
    assignments_by_employee = defaultdict(list)

    for row in surveys:
        surveys_by_employee[row.employee_id].append(row)

    for row in workloads:
        workloads_by_employee[row.employee_id].append(row)

    for row in promotions:
        promotions_by_employee[row.employee_id].append(row)

    for row in assignments:
        if row.effective_end is None or row.effective_end >= cutoff:
            assignments_by_employee[row.employee_id].append(row)

    features = []

    for employee in employees:
        employee_id = employee.employee_id

        # -----------------------------------------
        # 1. Tenure features
        # -----------------------------------------

        tenure_days = (cutoff - employee.hire_date).days

        tenure_months = (
            (cutoff.year - employee.hire_date.year) * 12
            + cutoff.month - employee.hire_date.month
        )

        # -----------------------------------------
        # 2. Engagement features
        # -----------------------------------------

        employee_surveys = sorted(
            surveys_by_employee[employee_id],
            key=lambda x: x.survey_date
        )

        completed_surveys = [
            row for row in employee_surveys
            if row.response_status == "COMPLETED"
            and row.engagement_score is not None
        ]

        missing_survey_count = sum(
            1 for row in employee_surveys
            if row.response_status == "MISSING"
        )

        total_survey_count = len(employee_surveys)
        completed_survey_count = len(completed_surveys)

        if completed_survey_count:
            engagement_scores = [
                row.engagement_score for row in completed_surveys
            ]

            average_engagement = round(mean(engagement_scores), 2)
            latest_engagement = engagement_scores[-1]
            latest_survey_date = completed_surveys[-1].survey_date

        else:
            average_engagement = None
            latest_engagement = None
            latest_survey_date = None

        if completed_survey_count >= 2:
            previous_engagement = completed_surveys[-2].engagement_score

            engagement_change = round(
                latest_engagement - previous_engagement, 2
            )

            engagement_decline = round(
                max(0, previous_engagement - latest_engagement), 2
            )
        else:
            previous_engagement = None
            engagement_change = None
            engagement_decline = None

        survey_response_rate = (
            round(
                completed_survey_count / total_survey_count * 100,
                2
            )
            if total_survey_count else None
        )

        # -----------------------------------------
        # 3. Workload features
        # -----------------------------------------

        employee_workloads = sorted(
            workloads_by_employee[employee_id],
            key=lambda x: x.period_end
        )

        if employee_workloads:
            average_weekly_hours = round(
                mean(row.avg_weekly_hours for row in employee_workloads),
                2
            )

            average_utilization = round(
                mean(
                    row.capacity_utilization_pct
                    for row in employee_workloads
                ),
                2
            )

            average_task_count = round(
                mean(row.task_count for row in employee_workloads),
                2
            )

            latest_workload = employee_workloads[-1]

            latest_weekly_hours = latest_workload.avg_weekly_hours
            latest_utilization = latest_workload.capacity_utilization_pct

            high_hours_periods = sum(
                1 for row in employee_workloads
                if row.avg_weekly_hours > 45
            )

            high_utilization_periods = sum(
                1 for row in employee_workloads
                if row.capacity_utilization_pct > 100
            )

            if len(employee_workloads) >= 2:
                previous_workload = employee_workloads[-2]

                weekly_hours_change = round(
                    latest_weekly_hours
                    - previous_workload.avg_weekly_hours,
                    2
                )
            else:
                weekly_hours_change = None

        else:
            average_weekly_hours = None
            average_utilization = None
            average_task_count = None
            latest_weekly_hours = None
            latest_utilization = None
            high_hours_periods = 0
            high_utilization_periods = 0
            weekly_hours_change = None

        # -----------------------------------------
        # 4. Career progression features
        # -----------------------------------------

        employee_promotions = sorted(
            promotions_by_employee[employee_id],
            key=lambda x: x.effective_date
        )

        promotion_count = len(employee_promotions)

        if employee_promotions:
            last_promotion_date = employee_promotions[-1].effective_date
            days_since_last_promotion = (
                cutoff - last_promotion_date
            ).days
        else:
            last_promotion_date = None
            days_since_last_promotion = None

        # -----------------------------------------
        # 5. Current role and team as of cutoff
        # -----------------------------------------

        employee_assignments = sorted(
            assignments_by_employee[employee_id],
            key=lambda x: x.effective_start
        )

        if employee_assignments:
            current_assignment = employee_assignments[-1]

            current_role = role_map.get(current_assignment.role_id)
            current_team = team_map.get(current_assignment.team_id)

            role_title = current_role.role_title if current_role else None
            department = current_role.department if current_role else None
            job_level = current_role.job_level if current_role else None
            team_name = current_team.team_name if current_team else None

        else:
            role_title = None
            department = None
            job_level = None
            team_name = None

        # -----------------------------------------
        # 6. Final employee feature record
        # -----------------------------------------

        features.append({
            "employee_id": employee_id,
            "feature_cutoff_date": cutoff.isoformat(),

            "hire_date": employee.hire_date.isoformat(),
            "tenure_days": tenure_days,
            "tenure_months": tenure_months,

            "department": department,
            "role_title": role_title,
            "job_level": job_level,
            "team_name": team_name,

            "total_surveys": total_survey_count,
            "completed_surveys": completed_survey_count,
            "missing_surveys": missing_survey_count,
            "survey_response_rate_pct": survey_response_rate,

            "average_engagement": average_engagement,
            "latest_engagement": latest_engagement,
            "previous_engagement": previous_engagement,
            "engagement_change": engagement_change,
            "engagement_decline": engagement_decline,
            "latest_survey_date": (
                latest_survey_date.isoformat()
                if latest_survey_date else None
            ),

            "average_weekly_hours": average_weekly_hours,
            "latest_weekly_hours": latest_weekly_hours,
            "weekly_hours_change": weekly_hours_change,
            "average_capacity_utilization_pct": average_utilization,
            "latest_capacity_utilization_pct": latest_utilization,
            "average_task_count": average_task_count,
            "high_hours_periods": high_hours_periods,
            "high_utilization_periods": high_utilization_periods,

            "promotion_count": promotion_count,
            "last_promotion_date": (
                last_promotion_date.isoformat()
                if last_promotion_date else None
            ),
            "days_since_last_promotion": days_since_last_promotion,
        })

    return features


def export_employee_features(features):
    project_root = Path(__file__).resolve().parents[3]

    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "employee_features.csv"

    if not features:
        raise ValueError("No employee features were generated.")

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(features[0].keys())
        )
        writer.writeheader()
        writer.writerows(features)

    print(f"Exported {len(features)} employee feature records.")
    print(f"Output file: {output_file}")

    return output_file


def main():
    session = SessionLocal()

    try:
        features = build_employee_features(session)
        export_employee_features(features)

    finally:
        session.close()


if __name__ == "__main__":
    main()
