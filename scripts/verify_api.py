"""End-to-end API checks against the real PostgreSQL database.

Every request runs inside one transaction that is rolled back at the end,
so no reviews or interventions are left behind.

Run from the repository root after the data pipeline:
    backend/venv/Scripts/python scripts/verify_api.py      (Windows)
    backend/venv/bin/python scripts/verify_api.py          (macOS/Linux)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

results = []


def check(name, ok, info=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} | {name}{' | ' + info if info else ''}")


def intervention(employee_id):
    return {
        "employee_id": employee_id,
        "intervention_type": "WORKLOAD_SUPPORT",
        "assigned_to_role": "MANAGER",
        "actor_role": "HR_PARTNER",
        "recommended_action": "Review task allocation in a supportive one-to-one.",
        "notes": "verify_api.py",
    }


def main():
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        check("Health", client.get("/api/health").json()["status"] == "healthy")

        summary = client.get("/api/dashboard/summary").json()
        check("Dashboard summary", summary["total_assessed"] > 0,
              f"{summary['total_assessed']} assessed, {summary['priority_counts']}")

        page = client.get("/api/employees", params={"limit": 5}).json()
        first = page["employees"][0]
        check("Employee list includes role and team",
              page["returned"] == 5 and first.get("team_name") is not None,
              f"{first['employee_id']}: {first.get('role_title')} / {first.get('team_name')}")

        detail = client.get(f"/api/employees/{first['employee_id']}/assessment").json()
        check("Employee assessment", "reason_codes" in detail["assessment"])

        pending = client.get("/api/reviews/pending", params={"limit": 4}).json()
        ids = [item["employee_id"] for item in pending["employees"]]
        scores = [int(item["assessment"]["support_priority_score"]) for item in pending["employees"]]
        check("Pending queue sorted by score", scores == sorted(scores, reverse=True))
        unreviewed, no_action, support, follow_up = ids

        # Human-review gate
        r = client.post("/api/interventions", json=intervention(unreviewed))
        check("Intervention without review is rejected", r.status_code == 409)

        for employee_id, decision in [
            (no_action, "NO_ACTION"),
            (support, "SUPPORT_NEEDED"),
            (follow_up, "FOLLOW_UP"),
        ]:
            r = client.post(f"/api/employees/{employee_id}/review",
                            json={"decision": decision, "reviewed_by_role": "HR_PARTNER"})
            check(f"Save {decision} review", r.status_code == 201)

        r = client.post(f"/api/employees/{support}/review",
                        json={"decision": "FOLLOW_UP", "reviewed_by_role": "MANAGER"})
        check("Duplicate review is rejected", r.status_code == 409)

        eligible = {item["employee_id"] for item in client.get("/api/reviews/eligible").json()["reviews"]}
        check("Only approving reviews are eligible",
              {support, follow_up} <= eligible and no_action not in eligible)

        r = client.post("/api/interventions", json=intervention(no_action))
        check("NO_ACTION blocks intervention", r.status_code == 400)

        r = client.post("/api/interventions", json=intervention(follow_up))
        check("FOLLOW_UP allows intervention", r.status_code == 201)

        r = client.post("/api/interventions", json=intervention(support))
        check("SUPPORT_NEEDED allows intervention",
              r.status_code == 201 and r.json()["intervention"]["human_reviewed"] is True)
        intervention_id = r.json()["intervention"]["intervention_id"]

        # Status lifecycle
        for status in ["IN_PROGRESS", "COMPLETED"]:
            r = client.patch(f"/api/interventions/{intervention_id}/status",
                             json={"status": status, "actor_role": "MANAGER"})
            check(f"Status -> {status}", r.status_code == 200)

        r = client.patch(f"/api/interventions/{intervention_id}/status",
                         json={"status": "CANCELLED", "actor_role": "MANAGER"})
        check("Completed intervention cannot be cancelled", r.status_code == 400)

        events = client.get(f"/api/interventions/{intervention_id}").json()["events"]
        check("Event history recorded",
              [event["event_type"] for event in events]
              == ["INTERVENTION_CREATED", "STATUS_CHANGED", "STATUS_CHANGED"])

        after = client.get("/api/dashboard/summary").json()
        check("Pending count drops by 3 reviews",
              after["pending_reviews"] == summary["pending_reviews"] - 3)

        quality = client.get("/api/data-quality/summary").json()
        check("Data-quality reports pass", quality["passed"],
              f"{len(quality['reports'])} reports, {len(quality['edge_cases'])} edge cases")
    finally:
        session.close()
        outer.rollback()
        connection.close()

    print(f"\n{sum(results)}/{len(results)} checks passed "
          "(transaction rolled back; database unchanged)")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
