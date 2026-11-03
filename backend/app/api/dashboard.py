
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.support_scoring import (
    CAREER_MAX,
    ENGAGEMENT_MAX,
    WORKLOAD_MAX,
)
from app.database import get_db
from app.models import AssessmentReview, Intervention
from app.services.assessment_service import get_all_assessments


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


def average(assessments, field):
    if not assessments:
        return 0.0

    total = sum(float(item[field]) for item in assessments)
    return round(total / len(assessments), 1)


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Aggregate assessment and review metrics for the overview page."""

    assessments = get_all_assessments()

    priority_counts = {"HIGH": 0, "MODERATE": 0, "ROUTINE": 0}

    for item in assessments:
        level = item["priority_level"].upper()
        priority_counts[level] = priority_counts.get(level, 0) + 1

    # A review only counts for the rule version it was recorded against.
    reviewed = {
        (employee_id, rule_version)
        for employee_id, rule_version in db.query(
            AssessmentReview.employee_id,
            AssessmentReview.rule_version,
        )
    }

    pending_reviews = sum(
        1
        for item in assessments
        if item["human_review_required"].strip().lower() == "true"
        and (item["employee_id"], item["rule_version"]) not in reviewed
    )

    return {
        "total_assessed": len(assessments),
        "priority_counts": priority_counts,
        "average_score": average(assessments, "support_priority_score"),
        "pending_reviews": pending_reviews,
        "reviews_recorded": len(reviewed),
        "interventions_total": db.query(Intervention).count(),
        "component_averages": [
            {
                "component": "Engagement",
                "average": average(
                    assessments, "engagement_component_score"
                ),
                "max": ENGAGEMENT_MAX,
            },
            {
                "component": "Workload",
                "average": average(
                    assessments, "workload_component_score"
                ),
                "max": WORKLOAD_MAX,
            },
            {
                "component": "Career",
                "average": average(
                    assessments, "career_component_score"
                ),
                "max": CAREER_MAX,
            },
        ],
    }
