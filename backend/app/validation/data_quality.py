
from collections import defaultdict
from datetime import date

from app.models import (
    Employee,
    Role,
    Team,
    EmployeeAssignmentHistory,
    TenureSnapshot,
    EngagementSurvey,
    WorkloadSnapshot,
    CompensationBand,
    EmployeeCompensationHistory,
    PromotionHistory,
    AttritionOutcome,
    Intervention,
    InterventionEvent,
)


FEATURE_CUTOFF = date(2026, 10, 31)


def validate_database(session):
    """
    Validate the clean PostgreSQL dataset.

    Returns:
        A dictionary containing validation summary and detected issues.
    """

    issues = []

    def add_issue(rule_id, table, record_id, message, severity="ERROR"):
        issues.append({
            "rule_id": rule_id,
            "table": table,
            "record_id": str(record_id),
            "severity": severity,
            "message": message,
        })

    # -------------------------------------------------
    # 1. Load records
    # -------------------------------------------------

    employees = session.query(Employee).all()
    roles = session.query(Role).all()
    teams = session.query(Team).all()
    assignments = session.query(EmployeeAssignmentHistory).all()
    tenure_snapshots = session.query(TenureSnapshot).all()
    surveys = session.query(EngagementSurvey).all()
    workloads = session.query(WorkloadSnapshot).all()
    compensation_bands = session.query(CompensationBand).all()
    compensation_history = session.query(EmployeeCompensationHistory).all()
    promotions = session.query(PromotionHistory).all()
    outcomes = session.query(AttritionOutcome).all()
    interventions = session.query(Intervention).all()
    intervention_events = session.query(InterventionEvent).all()

    employee_map = {e.employee_id: e for e in employees}
    role_ids = {r.role_id for r in roles}
    team_ids = {t.team_id for t in teams}
    band_ids = {b.band_id for b in compensation_bands}
    intervention_ids = {i.intervention_id for i in interventions}

    # -------------------------------------------------
    # 2. Foreign-key integrity
    # -------------------------------------------------

    for row in assignments:
        if row.employee_id not in employee_map:
            add_issue("FK001", "employee_assignment_history",
                      row.assignment_id, "Employee does not exist.")

        if row.role_id not in role_ids:
            add_issue("FK002", "employee_assignment_history",
                      row.assignment_id, "Role does not exist.")

        if row.team_id not in team_ids:
            add_issue("FK003", "employee_assignment_history",
                      row.assignment_id, "Team does not exist.")

    for row in tenure_snapshots:
        if row.employee_id not in employee_map:
            add_issue("FK004", "tenure_snapshot",
                      row.snapshot_id, "Employee does not exist.")

    for row in surveys:
        if row.employee_id not in employee_map:
            add_issue("FK005", "engagement_survey",
                      row.survey_id, "Employee does not exist.")

    for row in workloads:
        if row.employee_id not in employee_map:
            add_issue("FK006", "workload_snapshot",
                      row.workload_id, "Employee does not exist.")

    for row in compensation_history:
        if row.employee_id not in employee_map:
            add_issue("FK007", "employee_compensation_history",
                      row.compensation_history_id, "Employee does not exist.")

        if row.band_id not in band_ids:
            add_issue("FK008", "employee_compensation_history",
                      row.compensation_history_id, "Compensation band does not exist.")

    for row in promotions:
        if row.employee_id not in employee_map:
            add_issue("FK009", "promotion_history",
                      row.promotion_id, "Employee does not exist.")

        if row.to_role_id not in role_ids:
            add_issue("FK010", "promotion_history",
                      row.promotion_id, "Destination role does not exist.")

        if row.from_role_id is not None and row.from_role_id not in role_ids:
            add_issue("FK011", "promotion_history",
                      row.promotion_id, "Previous role does not exist.")

    for row in outcomes:
        if row.employee_id not in employee_map:
            add_issue("FK012", "attrition_outcome",
                      row.outcome_id, "Employee does not exist.")

    for row in interventions:
        if row.employee_id not in employee_map:
            add_issue("FK013", "intervention",
                      row.intervention_id, "Employee does not exist.")

    for row in intervention_events:
        if row.intervention_id not in intervention_ids:
            add_issue("FK014", "intervention_event",
                      row.event_id, "Intervention does not exist.")

    # -------------------------------------------------
    # 3. Assignment and compensation history
    # -------------------------------------------------

    assignments_by_employee = defaultdict(list)

    for row in assignments:
        if row.employee_id not in employee_map:
            continue

        employee = employee_map[row.employee_id]

        if row.effective_start < employee.hire_date:
            add_issue(
                "DATE001", "employee_assignment_history",
                row.assignment_id,
                "Assignment starts before employee hire date."
            )

        if row.effective_end and row.effective_end < row.effective_start:
            add_issue(
                "DATE002", "employee_assignment_history",
                row.assignment_id,
                "Assignment end date is before start date."
            )

        assignments_by_employee[row.employee_id].append(row)

    for employee_id, rows in assignments_by_employee.items():
        rows.sort(key=lambda x: x.effective_start)

        for previous, current in zip(rows, rows[1:]):
            if previous.effective_end is None:
                add_issue(
                    "HIST001", "employee_assignment_history",
                    current.assignment_id,
                    f"Overlapping assignment history for {employee_id}."
                )
            elif current.effective_start <= previous.effective_end:
                add_issue(
                    "HIST001", "employee_assignment_history",
                    current.assignment_id,
                    f"Overlapping assignment history for {employee_id}."
                )

    compensation_by_employee = defaultdict(list)

    for row in compensation_history:
        if row.employee_id in employee_map:
            compensation_by_employee[row.employee_id].append(row)

        if row.effective_end and row.effective_end < row.effective_start:
            add_issue(
                "DATE003", "employee_compensation_history",
                row.compensation_history_id,
                "Compensation end date is before start date."
            )

    for employee_id, rows in compensation_by_employee.items():
        rows.sort(key=lambda x: x.effective_start)

        for previous, current in zip(rows, rows[1:]):
            if previous.effective_end is None:
                add_issue(
                    "HIST002", "employee_compensation_history",
                    current.compensation_history_id,
                    f"Overlapping compensation history for {employee_id}."
                )
            elif current.effective_start <= previous.effective_end:
                add_issue(
                    "HIST002", "employee_compensation_history",
                    current.compensation_history_id,
                    f"Overlapping compensation history for {employee_id}."
                )

    # -------------------------------------------------
    # 4. Tenure snapshot validation
    # -------------------------------------------------

    for row in tenure_snapshots:
        employee = employee_map.get(row.employee_id)

        if employee is None:
            continue

        if row.as_of_date < employee.hire_date:
            add_issue(
                "TEN001", "tenure_snapshot", row.snapshot_id,
                "Snapshot date is before employee hire date."
            )
            continue

        expected_days = (row.as_of_date - employee.hire_date).days
        expected_months = (
            (row.as_of_date.year - employee.hire_date.year) * 12
            + row.as_of_date.month - employee.hire_date.month
        )

        if row.tenure_days != expected_days:
            add_issue(
                "TEN002", "tenure_snapshot", row.snapshot_id,
                f"Incorrect tenure_days. Expected {expected_days}."
            )

        if row.tenure_months != expected_months:
            add_issue(
                "TEN003", "tenure_snapshot", row.snapshot_id,
                f"Incorrect tenure_months. Expected {expected_months}."
            )

        if row.as_of_date > FEATURE_CUTOFF:
            add_issue(
                "LEAK001", "tenure_snapshot", row.snapshot_id,
                "Snapshot occurs after the feature cutoff date."
            )

    # -------------------------------------------------
    # 5. Engagement survey validation
    # -------------------------------------------------

    for row in surveys:
        employee = employee_map.get(row.employee_id)

        if employee and row.survey_date < employee.hire_date:
            add_issue(
                "SURV001", "engagement_survey", row.survey_id,
                "Survey date is before employee hire date."
            )

        if row.response_status == "COMPLETED":
            if row.engagement_score is None:
                add_issue(
                    "SURV002", "engagement_survey", row.survey_id,
                    "Completed survey has no engagement score."
                )
            elif not 1 <= row.engagement_score <= 10:
                add_issue(
                    "SURV003", "engagement_survey", row.survey_id,
                    "Engagement score must be between 1 and 10."
                )

        elif row.response_status == "MISSING":
            if row.engagement_score is not None:
                add_issue(
                    "SURV004", "engagement_survey", row.survey_id,
                    "Missing survey must have a NULL score."
                )

        else:
            add_issue(
                "SURV005", "engagement_survey", row.survey_id,
                f"Unknown response status: {row.response_status}."
            )

        if row.survey_date > FEATURE_CUTOFF:
            add_issue(
                "LEAK002", "engagement_survey", row.survey_id,
                "Survey occurs after the feature cutoff date."
            )

    # -------------------------------------------------
    # 6. Workload validation
    # -------------------------------------------------

    for row in workloads:
        employee = employee_map.get(row.employee_id)

        if row.period_end < row.period_start:
            add_issue(
                "WORK001", "workload_snapshot", row.workload_id,
                "Workload period end is before its start."
            )

        if employee and row.period_start < employee.hire_date:
            add_issue(
                "WORK002", "workload_snapshot", row.workload_id,
                "Workload period starts before employee hire date."
            )

        if row.avg_weekly_hours < 0:
            add_issue(
                "WORK003", "workload_snapshot", row.workload_id,
                "Weekly working hours cannot be negative."
            )

        if row.task_count < 0:
            add_issue(
                "WORK004", "workload_snapshot", row.workload_id,
                "Task count cannot be negative."
            )

        if row.capacity_utilization_pct < 0:
            add_issue(
                "WORK005", "workload_snapshot", row.workload_id,
                "Capacity utilization cannot be negative."
            )

        if row.period_end > FEATURE_CUTOFF:
            add_issue(
                "LEAK003", "workload_snapshot", row.workload_id,
                "Workload period ends after the feature cutoff date."
            )

    # -------------------------------------------------
    # 7. Promotion validation
    # -------------------------------------------------

    for row in promotions:
        employee = employee_map.get(row.employee_id)

        if employee and row.effective_date < employee.hire_date:
            add_issue(
                "PROM001", "promotion_history", row.promotion_id,
                "Promotion or move occurs before hire date."
            )

        if row.effective_date > FEATURE_CUTOFF:
            add_issue(
                "LEAK004", "promotion_history", row.promotion_id,
                "Promotion occurs after the feature cutoff date."
            )

        if row.promotion_type not in {"PROMOTION", "LATERAL_MOVE"}:
            add_issue(
                "PROM002", "promotion_history", row.promotion_id,
                f"Invalid promotion type: {row.promotion_type}."
            )

    # -------------------------------------------------
    # 8. Attrition outcome validation
    # -------------------------------------------------

    voluntary_count = 0

    for row in outcomes:
        if row.separation_type == "VOLUNTARY":
            voluntary_count += 1

            if row.outcome_label is not True or row.outcome_date is None:
                add_issue(
                    "OUT001", "attrition_outcome", row.outcome_id,
                    "Voluntary outcome must have TRUE label and an outcome date."
                )

        elif row.separation_type == "INVOLUNTARY":
            if row.outcome_label is not False or row.outcome_date is None:
                add_issue(
                    "OUT002", "attrition_outcome", row.outcome_id,
                    "Involuntary outcome must have FALSE label and an outcome date."
                )

        elif row.separation_type == "NO_EXIT":
            if row.outcome_label is not False or row.outcome_date is not None:
                add_issue(
                    "OUT003", "attrition_outcome", row.outcome_id,
                    "No-exit outcome must have FALSE label and no outcome date."
                )

        else:
            add_issue(
                "OUT004", "attrition_outcome", row.outcome_id,
                f"Unknown separation type: {row.separation_type}."
            )

        if row.horizon_end < row.horizon_start:
            add_issue(
                "OUT005", "attrition_outcome", row.outcome_id,
                "Outcome horizon end is before its start."
            )

        if row.outcome_date is not None:
            if not row.horizon_start <= row.outcome_date <= row.horizon_end:
                add_issue(
                    "OUT006", "attrition_outcome", row.outcome_id,
                    "Outcome date is outside the prediction horizon."
                )

    voluntary_rate = (
        voluntary_count / len(outcomes) * 100
        if outcomes else 0
    )

    if outcomes and not 5 <= voluntary_rate <= 15:
        add_issue(
            "OUT007", "attrition_outcome", "DATASET",
            f"Voluntary attrition rate is {voluntary_rate:.2f}%, "
            "outside the expected 5–15% range.",
            severity="WARNING"
        )

    # -------------------------------------------------
    # 9. Final report
    # -------------------------------------------------

    error_count = sum(
        1 for issue in issues if issue["severity"] == "ERROR"
    )
    warning_count = sum(
        1 for issue in issues if issue["severity"] == "WARNING"
    )

    return {
        "feature_cutoff": FEATURE_CUTOFF.isoformat(),
        "total_employees": len(employees),
        "total_roles": len(roles),
        "total_teams": len(teams),
        "total_assignments": len(assignments),
        "total_tenure_snapshots": len(tenure_snapshots),
        "total_surveys": len(surveys),
        "total_workload_snapshots": len(workloads),
        "total_compensation_history": len(compensation_history),
        "total_promotions": len(promotions),
        "total_outcomes": len(outcomes),
        "voluntary_attrition_rate_pct": round(voluntary_rate, 2),
        "total_interventions": len(interventions),
        "total_intervention_events": len(intervention_events),
        "error_count": error_count,
        "warning_count": warning_count,
        "passed": error_count == 0,
        "issues": issues,
    }
