
from sqlalchemy import (
    String, Integer, Float, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, UniqueConstraint,
    Numeric, Text, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime

from app.database import Base


# 1. EMPLOYEE
class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# 2. ROLE
class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    role_title: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    department: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    job_level: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    __table_args__ = (
        CheckConstraint("job_level BETWEEN 1 AND 10"),
    )


# 3. TEAM
class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    team_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# 4. EMPLOYEE ASSIGNMENT HISTORY
class EmployeeAssignmentHistory(Base):
    __tablename__ = "employee_assignment_history"

    assignment_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.role_id"), nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"), nullable=False
    )
    effective_start: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint(
            "effective_end IS NULL OR effective_end >= effective_start"
        ),
        Index("ix_assignment_employee", "employee_id"),
    )


# 5. TENURE SNAPSHOT
class TenureSnapshot(Base):
    __tablename__ = "tenure_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(60), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    tenure_days: Mapped[int] = mapped_column(Integer, nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("employee_id", "as_of_date"),
        CheckConstraint("tenure_days >= 0"),
        CheckConstraint("tenure_months >= 0"),
    )


# 6. ENGAGEMENT SURVEY
class EngagementSurvey(Base):
    __tablename__ = "engagement_surveys"

    survey_id: Mapped[str] = mapped_column(
        String(30), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    survey_date: Mapped[date] = mapped_column(Date, nullable=False)
    engagement_score: Mapped[int | None] = mapped_column(Integer)
    response_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "engagement_score IS NULL OR "
            "engagement_score BETWEEN 1 AND 10"
        ),
        CheckConstraint(
            "(response_status = 'COMPLETED' AND engagement_score IS NOT NULL)"
            " OR "
            "(response_status = 'MISSING' AND engagement_score IS NULL)"
        ),
        UniqueConstraint("employee_id", "survey_date"),
    )


# 7. WORKLOAD SNAPSHOT
class WorkloadSnapshot(Base):
    __tablename__ = "workload_snapshots"

    workload_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    avg_weekly_hours: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    task_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    capacity_utilization_pct: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    __table_args__ = (
        CheckConstraint("period_end >= period_start"),
        CheckConstraint("avg_weekly_hours >= 0"),
        CheckConstraint("task_count >= 0"),
        CheckConstraint("capacity_utilization_pct >= 0"),
        UniqueConstraint("employee_id", "period_start"),
    )


# 8. COMPENSATION BAND MASTER
class CompensationBand(Base):
    __tablename__ = "compensation_bands"

    band_id: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    band_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    job_level: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="INR"
    )
    min_annual_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    max_annual_salary: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    __table_args__ = (
        CheckConstraint("min_annual_salary >= 0"),
        CheckConstraint("max_annual_salary >= min_annual_salary"),
    )


# 9. EMPLOYEE COMPENSATION HISTORY
class EmployeeCompensationHistory(Base):
    __tablename__ = "employee_compensation_history"

    compensation_history_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    band_id: Mapped[str] = mapped_column(
        ForeignKey("compensation_bands.band_id"), nullable=False
    )
    effective_start: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint(
            "effective_end IS NULL OR effective_end >= effective_start"
        ),
    )


# 10. PROMOTION HISTORY
class PromotionHistory(Base):
    __tablename__ = "promotion_history"

    promotion_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    from_role_id: Mapped[str | None] = mapped_column(
        ForeignKey("roles.role_id")
    )
    to_role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.role_id"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    promotion_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "promotion_type IN ('PROMOTION', 'LATERAL_MOVE')"
        ),
    )


# 11. ATTRITION OUTCOME
class AttritionOutcome(Base):
    __tablename__ = "attrition_outcomes"

    outcome_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"),
        unique=True,
        nullable=False
    )
    horizon_start: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_end: Mapped[date] = mapped_column(Date, nullable=False)
    outcome_label: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    separation_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    outcome_date: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint("horizon_end >= horizon_start"),
        CheckConstraint(
            "(separation_type = 'VOLUNTARY' AND "
            "outcome_label = TRUE AND outcome_date IS NOT NULL) OR "
            "(separation_type = 'INVOLUNTARY' AND "
            "outcome_label = FALSE AND outcome_date IS NOT NULL) OR "
            "(separation_type = 'NO_EXIT' AND "
            "outcome_label = FALSE AND outcome_date IS NULL)"
        ),
    )


# 12. INTERVENTION
class Intervention(Base):
    __tablename__ = "interventions"

    intervention_id: Mapped[str] = mapped_column(
        String(30), primary_key=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), nullable=False
    )
    intervention_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    assigned_to_role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    recommended_action: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    human_reviewed: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# 13. INTERVENTION EVENT HISTORY
class InterventionEvent(Base):
    __tablename__ = "intervention_events"

    event_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )
    intervention_id: Mapped[str] = mapped_column(
        ForeignKey("interventions.intervention_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    actor_role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)


# 14. ASSESSMENT REVIEW AUDIT
class AssessmentReview(Base):
    __tablename__ = "assessment_reviews"

    review_id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )

    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    rule_version: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    feature_cutoff_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )

    reviewed_score: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    reviewed_priority: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    decision: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    reviewed_by_role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    review_notes: Mapped[str | None] = mapped_column(Text)

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "rule_version",
            name="uq_assessment_review_employee_version"
        ),
        CheckConstraint(
            "reviewed_score BETWEEN 0 AND 100"
        ),
        CheckConstraint(
            "reviewed_priority IN ('HIGH', 'MODERATE', 'ROUTINE')"
        ),
        CheckConstraint(
            "decision IN ('SUPPORT_NEEDED', 'NO_ACTION', 'FOLLOW_UP')"
        ),
        CheckConstraint(
            "reviewed_by_role IN ('HR_PARTNER', 'MANAGER', 'PEOPLE_PARTNER')"
        ),
    )


