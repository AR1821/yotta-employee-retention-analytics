# Data dictionary

All dates are ISO `YYYY-MM-DD`. The history window is 2024-11-01 to
2026-10-31; the feature cutoff is 2026-10-31; the outcome horizon is
2026-11-01 to 2027-10-31.

## Database tables

| Table | Key | Main columns and rules |
|---|---|---|
| `employees` | `employee_id` (`EMP-000001`) | `hire_date` |
| `roles` | `role_id` | `role_title`, `department`, `job_level` (1–10) |
| `teams` | `team_id` | `team_name` (unique) |
| `employee_assignment_history` | `assignment_id` | `employee_id`, `role_id`, `team_id`, `effective_start`, `effective_end` (NULL = current; end ≥ start) |
| `tenure_snapshots` | `snapshot_id` | `as_of_date`, `tenure_days`, `tenure_months` (≥ 0; unique per employee and date) |
| `engagement_surveys` | `survey_id` | `survey_date`, `engagement_score` 1–10, `response_status` `COMPLETED` (score required) or `MISSING` (score must be NULL) |
| `workload_snapshots` | `workload_id` | `period_start`, `period_end`, `avg_weekly_hours`, `task_count`, `capacity_utilization_pct` (all ≥ 0) |
| `compensation_bands` | `band_id` | `band_code`, `job_level`, `currency` (INR), `min_annual_salary` ≤ `max_annual_salary` |
| `employee_compensation_history` | `compensation_history_id` | `employee_id`, `band_id`, effective dates |
| `promotion_history` | `promotion_id` | `from_role_id`, `to_role_id`, `effective_date`, `promotion_type` `PROMOTION` or `LATERAL_MOVE` |
| `attrition_outcomes` | `outcome_id` | One per employee: `horizon_start/end`, `outcome_label`, `separation_type`, `outcome_date`. Constraint: VOLUNTARY ⇒ label TRUE and a date; INVOLUNTARY ⇒ FALSE and a date; NO_EXIT ⇒ FALSE and no date |
| `assessment_reviews` | `review_id` | `employee_id`, `rule_version`, `feature_cutoff_date`, `reviewed_score`, `reviewed_priority`, `decision` (`SUPPORT_NEEDED`, `FOLLOW_UP`, `NO_ACTION`), `reviewed_by_role`, `review_notes`, `reviewed_at`. Unique per employee and rule version |
| `interventions` | `intervention_id` | `employee_id`, `intervention_type`, `assigned_to_role`, `recommended_action`, `status` (`OPEN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), `human_reviewed`, `created_at` |
| `intervention_events` | `event_id` | `intervention_id`, `event_type`, `actor_role`, `event_at`, `notes` |

## `employee_features.csv`

One row per employee, built only from records dated on or before the
cutoff.

| Column | Meaning |
|---|---|
| `employee_id`, `feature_cutoff_date`, `hire_date` | Identity and point in time |
| `tenure_days`, `tenure_months` | Tenure at the cutoff |
| `department`, `role_title`, `job_level`, `team_name` | Assignment in effect at the cutoff |
| `total_surveys`, `completed_surveys`, `missing_surveys`, `survey_response_rate_pct` | Survey participation |
| `average_engagement`, `latest_engagement`, `previous_engagement` | Completed-survey scores only (missing surveys excluded) |
| `engagement_change`, `engagement_decline` | Latest minus previous, and the positive drop |
| `latest_survey_date` | Date of the latest completed survey |
| `average_weekly_hours`, `latest_weekly_hours`, `weekly_hours_change` | Working hours |
| `average_capacity_utilization_pct`, `latest_capacity_utilization_pct`, `average_task_count` | Workload |
| `high_hours_periods`, `high_utilization_periods` | Number of periods above the high thresholds |
| `promotion_count`, `last_promotion_date`, `days_since_last_promotion` | Career progression (empty when there is none) |

## `support_assessments.csv`

| Column | Meaning |
|---|---|
| `employee_id`, `feature_cutoff_date`, `rule_version` | What was scored, from which data, with which rules |
| `engagement_component_score` | 0–40 |
| `workload_component_score` | 0–40 |
| `career_component_score` | 0–20 |
| `support_priority_score` | Sum of the three components, 0–100 |
| `priority_level` | `HIGH` (≥ 60), `MODERATE` (≥ 30), `ROUTINE` |
| `reason_codes` | `|`-separated rule names that added points |
| `data_limitations` | `|`-separated missing-data notes (for example `NO_COMPLETED_ENGAGEMENT_SURVEY`) |
| `human_review_required`, `human_reviewed`, `assessment_status` | Always `True`, `False`, `PENDING_HUMAN_REVIEW` at generation; saved reviews live in `assessment_reviews` |

## `data/ground_truth/attrition_ground_truth.csv`

`outcome_id`, `employee_id`, `horizon_start`, `horizon_end`,
`outcome_label` (`True` only for voluntary exits), `separation_type`
(`VOLUNTARY`, `INVOLUNTARY`, `NO_EXIT`), `outcome_date`. This file is used
only by `evaluate_support_scores.py`.
