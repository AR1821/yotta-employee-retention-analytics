
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Employee,
    Role,
    Team,
    CompensationBand,
    EmployeeAssignmentHistory,
    EmployeeCompensationHistory,
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
TOTAL_EMPLOYEES = 10_000

# A 24-month historical window ending October 2026.
DATA_START = date(2024, 11, 1)
DATA_END = date(2026, 10, 31)

# Fixed timestamp to keep generated records reproducible.
CREATED_AT = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)

rng = random.Random(SEED)


# --------------------------------------------------
# MASTER DATA DEFINITIONS
# --------------------------------------------------

ROLE_DATA = [
    ("ROLE-001", "Junior Software Engineer", "Engineering", 1),
    ("ROLE-002", "Software Engineer", "Engineering", 2),
    ("ROLE-003", "Senior Software Engineer", "Engineering", 3),
    ("ROLE-004", "Data Analyst", "Data Science", 2),
    ("ROLE-005", "Data Scientist", "Data Science", 3),
    ("ROLE-006", "Senior Data Scientist", "Data Science", 4),
    ("ROLE-007", "HR Executive", "Human Resources", 2),
    ("ROLE-008", "HR Manager", "Human Resources", 5),
    ("ROLE-009", "Business Analyst", "Business", 2),
    ("ROLE-010", "Project Manager", "Management", 6),
]

TEAM_NAMES = [
    "Engineering Alpha",
    "Engineering Beta",
    "Data Science Alpha",
    "Data Science Beta",
    "Human Resources",
    "Business Operations",
    "Product Development",
    "Quality Assurance",
    "Cloud Infrastructure",
    "Customer Success",
]


# One compensation band for each job level.
COMPENSATION_DATA = [
    (f"BAND-{level:03d}", f"L{level}", level,
     Decimal(str(level * 300000)),
     Decimal(str(level * 300000 + 200000)))
    for level in range(1, 11)
]


def random_hire_date():
    """Generate a hire date within the historical window."""
    total_days = (DATA_END - DATA_START).days
    return DATA_START + timedelta(days=rng.randint(0, total_days))


# --------------------------------------------------
# GENERATOR
# --------------------------------------------------


def generate_master_data():

    with SessionLocal() as session:

        # Check whether master data already exists.
        existing_count = session.scalar(
            select(Employee.employee_id).limit(1)
        )

        if existing_count is not None:
            raise RuntimeError(
                "Employees already exist. "
                "Refusing to generate duplicate master data."
            )

        # The SELECT above triggered autobegin.
        # Use the existing transaction instead of starting another one.

        # 1. Create roles
        roles = [
            Role(
                role_id=role_id,
                role_title=title,
                department=department,
                job_level=level,
            )
            for role_id, title, department, level in ROLE_DATA
        ]

        session.add_all(roles)

        # 2. Create teams
        teams = [
            Team(
                team_id=f"TEAM-{i:03d}",
                team_name=name,
                created_at=CREATED_AT,
            )
            for i, name in enumerate(TEAM_NAMES, start=1)
        ]

        session.add_all(teams)

        # 3. Create compensation bands
        bands = [
            CompensationBand(
                band_id=band_id,
                band_code=band_code,
                job_level=level,
                currency="INR",
                min_annual_salary=minimum,
                max_annual_salary=maximum,
            )
            for (
                band_id,
                band_code,
                level,
                minimum,
                maximum,
            ) in COMPENSATION_DATA
        ]

        session.add_all(bands)
        session.flush()

        band_by_level = {
            band.job_level: band
            for band in bands
        }

        employee_records = []
        assignment_records = []
        compensation_records = []

        # 4. Generate employees and dependent records
        for i in range(1, TOTAL_EMPLOYEES + 1):

            employee_id = f"EMP-{i:06d}"
            hire_date = random_hire_date()

            selected_role = rng.choice(roles)
            selected_team = rng.choice(teams)
            selected_band = band_by_level[selected_role.job_level]

            employee_records.append(
                Employee(
                    employee_id=employee_id,
                    hire_date=hire_date,
                    created_at=CREATED_AT,
                )
            )

            assignment_records.append(
                EmployeeAssignmentHistory(
                    assignment_id=f"ASG-{employee_id}-001",
                    employee_id=employee_id,
                    role_id=selected_role.role_id,
                    team_id=selected_team.team_id,
                    effective_start=hire_date,
                    effective_end=None,
                )
            )

            compensation_records.append(
                EmployeeCompensationHistory(
                    compensation_history_id=f"COMP-{employee_id}-001",
                    employee_id=employee_id,
                    band_id=selected_band.band_id,
                    effective_start=hire_date,
                    effective_end=None,
                )
            )

        session.add_all(employee_records)
        session.flush()

        session.add_all(assignment_records)
        session.add_all(compensation_records)

        # Commit everything together.
        session.commit()

        print("\nMaster data generated successfully!")
        print(f"Employees: {TOTAL_EMPLOYEES}")
        print(f"Roles: {len(ROLE_DATA)}")
        print(f"Teams: {len(TEAM_NAMES)}")
        print(f"Compensation bands: {len(COMPENSATION_DATA)}")
        print(f"Assignments: {len(assignment_records)}")
        print(f"Compensation histories: {len(compensation_records)}")


if __name__ == "__main__":
    generate_master_data()
