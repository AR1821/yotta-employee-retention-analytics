
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AssessmentReview,
    Employee,
    EmployeeAssignmentHistory,
    Role,
    Team,
)
from app.services.assessment_service import (
    get_assessment,
    get_all_assessments,
)

router = APIRouter(
    prefix="/api/employees",
    tags=["Employees"],
)


def current_assignments(db: Session, employee_ids: list[str]):
    """Role and team details at the assessment cutoff, keyed by employee."""

    cutoff = employee_assessment_cutoff()

    rows = (
        db.query(
            EmployeeAssignmentHistory.employee_id,
            Role,
            Team,
        )
        .join(Role, EmployeeAssignmentHistory.role_id == Role.role_id)
        .join(Team, EmployeeAssignmentHistory.team_id == Team.team_id)
        .filter(
            EmployeeAssignmentHistory.employee_id.in_(employee_ids),
            EmployeeAssignmentHistory.effective_start <= cutoff,
        )
        .filter(
            (EmployeeAssignmentHistory.effective_end.is_(None))
            | (EmployeeAssignmentHistory.effective_end >= cutoff)
        )
        .order_by(EmployeeAssignmentHistory.effective_start.asc())
        .all()
    )

    # Later assignments overwrite earlier ones, leaving the latest.
    return {
        employee_id: {
            "role_title": role.role_title,
            "department": role.department,
            "job_level": role.job_level,
            "team_name": team.team_name,
        }
        for employee_id, role, team in rows
    }


@router.get("")
def list_employees(
    limit: int = Query(default=20, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """List employees with their support assessments."""

    assessments = sorted(
        get_all_assessments(),
        key=lambda item: item["employee_id"],
    )

    if priority:
        priority = priority.upper()
        if priority not in {"HIGH", "MODERATE", "ROUTINE"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid priority. Use HIGH, MODERATE or ROUTINE."
            )

        assessments = [
            item for item in assessments
            if item["priority_level"].upper() == priority
        ]

    # Page the assessments first so each query only touches this page.
    page = assessments[offset:offset + limit]
    page_ids = [item["employee_id"] for item in page]

    employees = {
        employee.employee_id: employee
        for employee in db.query(Employee).filter(
            Employee.employee_id.in_(page_ids)
        )
    }

    assignments = current_assignments(db, page_ids)

    reviews = {
        (review.employee_id, review.rule_version): review.decision
        for review in db.query(AssessmentReview).filter(
            AssessmentReview.employee_id.in_(page_ids)
        )
    }

    results = []

    for assessment in page:
        employee = employees.get(assessment["employee_id"])

        if not employee:
            continue

        results.append({
            "employee_id": employee.employee_id,
            "hire_date": employee.hire_date.isoformat(),
            **assignments.get(employee.employee_id, {}),
            "review_decision": reviews.get(
                (employee.employee_id, assessment["rule_version"])
            ),
            "assessment": assessment,
        })

    return {
        "total": len(assessments),
        "limit": limit,
        "offset": offset,
        "returned": len(results),
        "employees": results,
    }


@router.get("/{employee_id}/assessment")
def employee_assessment(
    employee_id: str,
    db: Session = Depends(get_db),
):
    """Get employee details and their support assessment."""

    employee = db.get(Employee, employee_id)

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    assessment = get_assessment(employee_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Support assessment not found."
        )

    assignment = (
        db.query(
            EmployeeAssignmentHistory,
            Role,
            Team,
        )
        .join(
            Role,
            EmployeeAssignmentHistory.role_id == Role.role_id,
        )
        .join(
            Team,
            EmployeeAssignmentHistory.team_id == Team.team_id,
        )
        .filter(
            EmployeeAssignmentHistory.employee_id == employee_id,
            EmployeeAssignmentHistory.effective_start <=
                employee_assessment_cutoff(),
        )
        .filter(
            (EmployeeAssignmentHistory.effective_end.is_(None))
            | (
                EmployeeAssignmentHistory.effective_end
                >= employee_assessment_cutoff()
            )
        )
        .order_by(
            EmployeeAssignmentHistory.effective_start.desc()
        )
        .first()
    )

    role_details = None

    if assignment:
        _, role, team = assignment

        role_details = {
            "role_title": role.role_title,
            "department": role.department,
            "job_level": role.job_level,
            "team_name": team.team_name,
        }

    return {
        "employee_id": employee.employee_id,
        "hire_date": employee.hire_date.isoformat(),
        "current_assignment": role_details,
        "assessment": assessment,
    }


def employee_assessment_cutoff():
    from datetime import date
    return date(2026, 10, 31)
