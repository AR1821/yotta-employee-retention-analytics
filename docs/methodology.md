# Methodology

## 1. Synthetic data

- **Seed:** `20261022`. Each generator owns a `random.Random(SEED)`, and
  record timestamps are fixed constants, so repeated runs on an empty
  database give identical output (verified byte for byte).
- **Population:** 10,000 employees hired across the 24-month window, each
  assigned one of 10 roles (5 departments, job levels 1–6) and one of
  10 teams, with a compensation band matching their job level.
- **History:** quarterly engagement surveys (about 18% `MISSING`, which
  keeps a NULL score), workload snapshots (hours, tasks, utilisation), tenure
  snapshots, and 379 promotions or lateral moves. Each move closes the
  previous assignment and opens a new one.
- **Outcomes:** exactly 10% voluntary and 4% involuntary exits within
  12 months of the cutoff. Voluntary leavers are drawn by weighted
  sampling without replacement. The weight starts at 1.0 and rises with
  lower latest engagement (+0.12 per point below 10), utilisation above
  80% (+0.02 per point) and hours above 45 (+0.03 per hour). It falls by
  15% after a promotion in the last 180 days. Missing surveys add
  nothing.

## 2. Features

Every source table is filtered to records dated on or before
2026-10-31, and outcomes are never queried. See the data dictionary for
the 30 columns.

## 3. Support-priority score (rule version 1.0)

| Component | Rule | Points | Reason code |
|---|---|---|---|
| Engagement (max 40) | Latest engagement ≤ 4 / ≤ 5.5 / ≤ 6.5 | 20 / 12 / 6 | `LOW_LATEST_ENGAGEMENT` / `BELOW_EXPECTED_ENGAGEMENT` / `MODERATE_ENGAGEMENT_SIGNAL` |
| | Decline since previous survey ≥ 2 / ≥ 1 / ≥ 0.5 | 20 / 12 / 6 | `SIGNIFICANT_ENGAGEMENT_DECLINE` / `ENGAGEMENT_DECLINE` / `SLIGHT_ENGAGEMENT_DECLINE` |
| Workload (max 40) | Average weekly hours ≥ 50 / ≥ 45 / ≥ 40 | 20 / 12 / 5 | `VERY_HIGH_…` / `HIGH_…` / `ELEVATED_AVERAGE_WORKING_HOURS` |
| | Average utilisation ≥ 110% / ≥ 100% / ≥ 90% | 20 / 14 / 8 | `VERY_HIGH_…` / `HIGH_…` / `ELEVATED_CAPACITY_UTILIZATION` |
| Career (max 20) | Days since last recorded promotion ≥ 730 / ≥ 540 / ≥ 365 / ≥ 180 | 20 / 15 / 10 / 5 | `LONG_TIME_SINCE_LAST_RECORDED_PROMOTION` … `RECENT_CAREER_PROGRESSION_GAP` |

- **Priority:** HIGH ≥ 60, MODERATE ≥ 30, otherwise ROUTINE.
- **Missing data scores zero and is reported, never penalised.** No
  completed survey, no workload data, or no recorded promotion adds a
  `data_limitations` entry instead of points. This is why the career
  component is rarely triggered: only 379 employees have any promotion
  on record.
- **Explainability is validated:** every assessment with points must
  carry reason codes, and the component scores must sum to the total.

## 4. Human review

Every assessment starts as `PENDING_HUMAN_REVIEW`. A reviewer sees the
components, reason codes and data limitations, then records a decision.
`NO_ACTION` is a valid, respected outcome: the API refuses to create an
intervention after it.

## 5. Evaluation

`evaluate_support_scores.py` joins scores to the held-out labels and
reports the base rate, ROC AUC (rank-based, with ties counted as half),
attrition rate and lift per priority band, precision and recall when
flagging HIGH or HIGH+MODERATE, and top-decile capture.

Results on the generated data: AUC 0.549; attrition 14.4% / 11.4% / 9.0%
for HIGH / MODERATE / ROUTINE. The rules were not tuned to these labels.
Because the labels were sampled from similar signals, the metrics confirm
that the pipeline recovers the planted pattern without leakage. They do
not estimate real-world accuracy.

## 6. Edge cases

There are four labelled fixtures in `data/edge_cases/`: future-information
leakage, a missing survey imputed as negative, a voluntary exit labelled
`false`, and an unexplained, unreviewed score. `test_edge_cases.py` must
detect all four. The same protections apply to the real data through
validation rules (`LEAK001–004`, `SURV004`, `OUT001`), database
constraints, scoring rules and the API's review gate.
