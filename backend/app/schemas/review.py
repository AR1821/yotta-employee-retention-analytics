
from typing import Literal

from pydantic import BaseModel, Field


class AssessmentReviewCreate(BaseModel):
    decision: Literal[
        "SUPPORT_NEEDED",
        "NO_ACTION",
        "FOLLOW_UP",
    ]

    reviewed_by_role: Literal[
        "HR_PARTNER",
        "MANAGER",
        "PEOPLE_PARTNER",
    ]

    review_notes: str | None = Field(
        default=None,
        max_length=2000,
    )
