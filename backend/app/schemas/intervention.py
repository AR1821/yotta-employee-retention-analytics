
from typing import Literal

from pydantic import BaseModel, Field


InterventionType = Literal[
    "ENGAGEMENT_CHECK_IN",
    "WORKLOAD_SUPPORT",
    "CAREER_DEVELOPMENT",
    "MANAGER_CONVERSATION",
]

ReviewerRole = Literal[
    "HR_PARTNER",
    "MANAGER",
    "PEOPLE_PARTNER",
]

InterventionStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
]


class InterventionCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=20)

    intervention_type: InterventionType

    assigned_to_role: ReviewerRole

    recommended_action: str = Field(
        min_length=10,
        max_length=2000,
    )

    actor_role: ReviewerRole

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class InterventionStatusUpdate(BaseModel):
    status: Literal[
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ]

    actor_role: ReviewerRole

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )
