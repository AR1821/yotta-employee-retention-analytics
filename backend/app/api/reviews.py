
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AssessmentReview, Employee, Intervention
from app.schemas.review import AssessmentReviewCreate
from app.services.assessment_service import (
    get_all_assessments,
    get_assessment,
)


router = APIRouter(
    prefix="/api/employees",
    tags=["Assessment Reviews"],
)

queue_router = APIRouter(
    prefix="/api/reviews",
    tags=["Assessment Reviews"],
)


@queue_router.get("/eligible")
def list_intervention_eligible_reviews(db: Session = Depends(get_db)):
    """Reviews that allow an intervention for the current assessment."""

    reviews = (
        db.query(AssessmentReview)
        .filter(AssessmentReview.decision.in_(
            ["SUPPORT_NEEDED", "FOLLOW_UP"]
        ))
        .order_by(AssessmentReview.reviewed_at.desc())
        .all()
    )

    active = {
        employee_id
        for (employee_id,) in db.query(Intervention.employee_id).filter(
            Intervention.status.in_(["OPEN", "IN_PROGRESS"])
        )
    }

    eligible = []

    for review in reviews:
        assessment = get_assessment(review.employee_id)

        # Skip reviews recorded against an older rule version.
        if (
            not assessment
            or assessment["rule_version"] != review.rule_version
        ):
            continue

        eligible.append({
            "employee_id": review.employee_id,
            "decision": review.decision,
            "reviewed_by_role": review.reviewed_by_role,
            "reviewed_priority": review.reviewed_priority,
            "reviewed_score": review.reviewed_score,
            "reason_codes": assessment["reason_codes"],
            "has_active_intervention": review.employee_id in active,
            "reviewed_at": review.reviewed_at.isoformat(),
        })

    return {"total": len(eligible), "reviews": eligible}


@queue_router.get("/pending")
def list_pending_reviews(
    search: str | None = Query(default=None, max_length=20),
    priority: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List assessments that still need a saved human review."""

    # A review only covers the rule version it was recorded against.
    reviewed = {
        (employee_id, rule_version)
        for employee_id, rule_version in db.query(
            AssessmentReview.employee_id,
            AssessmentReview.rule_version,
        )
    }

    pending = [
        item for item in get_all_assessments()
        if item["human_review_required"].strip().lower() == "true"
        and (item["employee_id"], item["rule_version"]) not in reviewed
    ]

    if priority:
        priority = priority.upper()
        if priority not in {"HIGH", "MODERATE", "ROUTINE"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid priority. Use HIGH, MODERATE or ROUTINE."
            )

        pending = [
            item for item in pending
            if item["priority_level"].upper() == priority
        ]

    if search:
        term = search.strip().lower()
        pending = [
            item for item in pending
            if term in item["employee_id"].lower()
        ]

    # Highest support scores first, so reviewers see them sooner.
    pending.sort(
        key=lambda item: (
            -int(item["support_priority_score"]),
            item["employee_id"],
        )
    )

    page = pending[offset:offset + limit]

    return {
        "total": len(pending),
        "limit": limit,
        "offset": offset,
        "returned": len(page),
        "employees": [
            {
                "employee_id": item["employee_id"],
                "assessment": item,
            }
            for item in page
        ],
    }


@router.post("/{employee_id}/review", status_code=201)
def create_assessment_review(
    employee_id: str,
    payload: AssessmentReviewCreate,
    db: Session = Depends(get_db),
):
    # Verify employee exists.
    employee = db.get(Employee, employee_id)

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found.",
        )

    # Retrieve the assessment being reviewed.
    assessment = get_assessment(employee_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Employee assessment not found.",
        )

    # Prevent duplicate reviews for the same rule version.
    existing_review = (
        db.query(AssessmentReview)
        .filter(
            AssessmentReview.employee_id == employee_id,
            AssessmentReview.rule_version == assessment["rule_version"],
        )
        .first()
    )

    if existing_review:
        raise HTTPException(
            status_code=409,
            detail="This assessment has already been reviewed.",
        )

    review = AssessmentReview(
        review_id=f"REV-{uuid4().hex}",
        employee_id=employee_id,
        rule_version=assessment["rule_version"],
        feature_cutoff_date=assessment["feature_cutoff_date"],
        reviewed_score=int(assessment["support_priority_score"]),
        reviewed_priority=assessment["priority_level"].upper(),
        decision=payload.decision,
        reviewed_by_role=payload.reviewed_by_role,
        review_notes=payload.review_notes,
    )

    try:
        db.add(review)
        db.commit()
        db.refresh(review)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A review already exists for this assessment.",
        )

    return {
        "message": "Assessment review recorded successfully.",
        "review": {
            "review_id": review.review_id,
            "employee_id": review.employee_id,
            "reviewed_score": review.reviewed_score,
            "reviewed_priority": review.reviewed_priority,
            "decision": review.decision,
            "reviewed_by_role": review.reviewed_by_role,
            "reviewed_at": review.reviewed_at.isoformat(),
        },
    }


@router.get("/{employee_id}/review")
def get_assessment_review(
    employee_id: str,
    db: Session = Depends(get_db),
):
    review = (
        db.query(AssessmentReview)
        .filter(AssessmentReview.employee_id == employee_id)
        .order_by(AssessmentReview.reviewed_at.desc())
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="No assessment review found.",
        )

    return {
        "review_id": review.review_id,
        "employee_id": review.employee_id,
        "rule_version": review.rule_version,
        "reviewed_score": review.reviewed_score,
        "reviewed_priority": review.reviewed_priority,
        "decision": review.decision,
        "reviewed_by_role": review.reviewed_by_role,
        "review_notes": review.review_notes,
        "reviewed_at": review.reviewed_at.isoformat(),
    }
