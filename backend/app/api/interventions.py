
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AssessmentReview,
    Employee,
    Intervention,
    InterventionEvent,
)
from app.schemas.intervention import (
    InterventionCreate,
    InterventionStatusUpdate,
)
from app.services.assessment_service import get_assessment


router = APIRouter(
    prefix="/api/interventions",
    tags=["Interventions"],
)


def create_event(
    db: Session,
    intervention_id: str,
    event_type: str,
    actor_role: str,
    notes: str | None = None,
):
    event = InterventionEvent(
        event_id=f"EVT-{uuid4().hex}",
        intervention_id=intervention_id,
        event_type=event_type,
        actor_role=actor_role,
        event_at=datetime.now(timezone.utc),
        notes=notes,
    )

    db.add(event)
    return event


@router.post("", status_code=201)
def create_intervention(
    payload: InterventionCreate,
    db: Session = Depends(get_db),
):
    # 1. Verify employee exists.
    employee = db.get(Employee, payload.employee_id)

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found.",
        )

    # 2. Verify assessment exists.
    assessment = get_assessment(payload.employee_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Employee support assessment not found.",
        )

    # 3. Verify that a human review has been saved for this assessment.
    review = (
        db.query(AssessmentReview)
        .filter(
            AssessmentReview.employee_id == payload.employee_id,
            AssessmentReview.rule_version == assessment["rule_version"],
        )
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=409,
            detail="A human review is required before creating an intervention.",
        )

    if review.decision == "NO_ACTION":
        raise HTTPException(
            status_code=400,
            detail=(
                "The reviewer selected NO_ACTION. "
                "An intervention cannot be created."
            ),
        )

    # 4. Create intervention.
    intervention_id = f"INT-{uuid4().hex[:26]}"

    intervention = Intervention(
        intervention_id=intervention_id,
        employee_id=payload.employee_id,
        intervention_type=payload.intervention_type,
        assigned_to_role=payload.assigned_to_role,
        recommended_action=payload.recommended_action,
        status="OPEN",
        human_reviewed=True,
    )

    try:
        db.add(intervention)
        db.flush()

        # 5. Record creation in event history.
        create_event(
            db=db,
            intervention_id=intervention_id,
            event_type="INTERVENTION_CREATED",
            actor_role=payload.actor_role,
            notes=payload.notes,
        )

        db.commit()
        db.refresh(intervention)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Intervention created successfully.",
        "intervention": {
            "intervention_id": intervention.intervention_id,
            "employee_id": intervention.employee_id,
            "intervention_type": intervention.intervention_type,
            "assigned_to_role": intervention.assigned_to_role,
            "recommended_action": intervention.recommended_action,
            "status": intervention.status,
            "human_reviewed": intervention.human_reviewed,
            "created_at": (
                intervention.created_at.isoformat()
                if intervention.created_at else None
            ),
        },
    }


@router.get("")
def list_interventions(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Intervention)

    if status:
        status = status.upper()

        if status not in {
            "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid intervention status.",
            )

        query = query.filter(Intervention.status == status)

    total = query.count()

    records = (
        query.order_by(Intervention.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "interventions": [
            {
                "intervention_id": item.intervention_id,
                "employee_id": item.employee_id,
                "intervention_type": item.intervention_type,
                "assigned_to_role": item.assigned_to_role,
                "status": item.status,
                "human_reviewed": item.human_reviewed,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at else None
                ),
            }
            for item in records
        ],
    }


@router.get("/{intervention_id}")
def get_intervention(
    intervention_id: str,
    db: Session = Depends(get_db),
):
    intervention = db.get(Intervention, intervention_id)

    if not intervention:
        raise HTTPException(
            status_code=404,
            detail="Intervention not found.",
        )

    events = (
        db.query(InterventionEvent)
        .filter(
            InterventionEvent.intervention_id == intervention_id
        )
        .order_by(InterventionEvent.event_at.asc())
        .all()
    )

    return {
        "intervention": {
            "intervention_id": intervention.intervention_id,
            "employee_id": intervention.employee_id,
            "intervention_type": intervention.intervention_type,
            "assigned_to_role": intervention.assigned_to_role,
            "recommended_action": intervention.recommended_action,
            "status": intervention.status,
            "human_reviewed": intervention.human_reviewed,
            "created_at": (
                intervention.created_at.isoformat()
                if intervention.created_at else None
            ),
        },
        "events": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor_role": event.actor_role,
                "event_at": event.event_at.isoformat(),
                "notes": event.notes,
            }
            for event in events
        ],
    }


@router.patch("/{intervention_id}/status")
def update_intervention_status(
    intervention_id: str,
    payload: InterventionStatusUpdate,
    db: Session = Depends(get_db),
):
    intervention = db.get(Intervention, intervention_id)

    if not intervention:
        raise HTTPException(
            status_code=404,
            detail="Intervention not found.",
        )

    allowed_transitions = {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    if payload.status not in allowed_transitions[intervention.status]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change status from "
                f"{intervention.status} to {payload.status}."
            ),
        )

    old_status = intervention.status

    try:
        intervention.status = payload.status

        create_event(
            db=db,
            intervention_id=intervention_id,
            event_type="STATUS_CHANGED",
            actor_role=payload.actor_role,
            notes=(
                f"{old_status} -> {payload.status}. "
                f"{payload.notes or ''}"
            ).strip(),
        )

        db.commit()
        db.refresh(intervention)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Intervention status updated.",
        "intervention_id": intervention_id,
        "old_status": old_status,
        "new_status": intervention.status,
    }
