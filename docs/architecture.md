# Architecture

## Components

| Component | Location | Responsibility |
|---|---|---|
| Schema | `backend/app/models.py` | 14 SQLAlchemy tables with keys, check constraints and unique constraints |
| Generator | `backend/app/generator/` | Seeded synthetic data: master data, 24-month history, 12-month outcomes |
| Validation | `backend/app/validation/data_quality.py`, `backend/validate_*.py` | 45 database rules (FK, DATE, HIST, TEN, SURV, WORK, PROM, OUT, LEAK) and feature/assessment checks |
| Feature engineering | `backend/app/analytics/feature_engineering.py` | One point-in-time feature row per employee; filters every source to `<= 2026-10-31`; never reads outcomes |
| Scoring | `backend/app/analytics/support_scoring.py` | Rule-based score (0–100), priority band, reason codes, data limitations |
| Evaluation | `backend/evaluate_support_scores.py` | Compares scores with held-out ground truth |
| API | `backend/app/api/` | FastAPI routers for employees, reviews, interventions, dashboard and data quality |
| Frontend | `frontend/src/` | React pages: Dashboard, Employee Explorer, Human Reviews, Interventions, Data Quality |

## Leakage boundary

```text
            on or before 2026-10-31          |   2026-11-01 .. 2027-10-31
 surveys, workload, tenure, promotions       |   attrition outcomes
        │                                    |         │
        ▼                                    |         ▼
 feature_engineering ──► support_scoring     |   data/ground_truth/
        │                                    |         │
        └────────────► evaluate_support_scores ◄───────┘   (only reader of labels)
```

The attrition generator does read pre-cutoff signals, because it needs
them to make the synthetic outcomes realistic. Analytics code never reads
outcomes.

## Human-review workflow

```text
assessment (CSV, rule v1.0)
   │  POST /api/employees/{id}/review   decision ∈ {SUPPORT_NEEDED, FOLLOW_UP, NO_ACTION}
   ▼
assessment_reviews  (unique per employee + rule_version)
   │  POST /api/interventions
   │     409 if no review for the current rule version
   │     400 if the review is NO_ACTION
   ▼
interventions (human_reviewed = TRUE) ──► intervention_events (INTERVENTION_CREATED)
   │  PATCH /api/interventions/{id}/status
   │     OPEN → IN_PROGRESS | CANCELLED
   │     IN_PROGRESS → COMPLETED | CANCELLED
   ▼
intervention_events (STATUS_CHANGED, with actor role and notes)
```

## API reference

Interactive documentation is at `http://127.0.0.1:8000/docs` while the
API is running.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/dashboard/summary` | Totals, priority counts, averages, pending reviews |
| GET | `/api/employees?limit&offset&priority` | Employees with role, team, review decision and assessment (limit ≤ 1000) |
| GET | `/api/employees/{id}/assessment` | One assessment with the assignment at the cutoff |
| POST | `/api/employees/{id}/review` | Record a human review (409 if one already exists) |
| GET | `/api/employees/{id}/review` | Latest review for an employee |
| GET | `/api/reviews/pending?search&priority&limit&offset` | Unreviewed assessments, highest score first |
| GET | `/api/reviews/eligible` | Reviews that allow an intervention, with an active-intervention flag |
| POST | `/api/interventions` | Create an intervention (passes through the human-review gate) |
| GET | `/api/interventions?status&limit&offset` | List interventions |
| GET | `/api/interventions/{id}` | Intervention with its event history |
| PATCH | `/api/interventions/{id}/status` | Change status (allowed transitions only) |
| GET | `/api/data-quality/summary` | Saved validation reports and the edge-case catalog |

## Design decisions

- **Assignment and compensation history tables** keep internal transfers
  and band changes as dated rows instead of overwriting the employee
  record.
- **Assessments are versioned** (`rule_version`), and reviews are tied to
  the version they saw. Changing the rules later puts every employee back
  in the review queue.
- **Interventions keep an append-only event log**, so the full history of
  who changed what, and when, is preserved.
- **Server-side aggregation.** The dashboard and review queue call
  summary and paged endpoints instead of downloading 10,000 records.
