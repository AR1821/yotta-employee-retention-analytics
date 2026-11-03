"""Generate, score, validate and evaluate the full dataset in one run.

Run from the repository root with the backend virtual environment, after
`docker compose up -d db`, on an empty database:
    backend/venv/Scripts/python scripts/run_pipeline.py      (Windows)
    backend/venv/bin/python scripts/run_pipeline.py          (macOS/Linux)

The generators refuse to run twice on the same database. To start over,
remove the volume first: `docker compose down -v`.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"

STEPS = [
    ("Create tables", ["create_tables.py"]),
    ("Master data (10,000 employees)", ["-m", "app.generator.master_data"]),
    ("24-month history", ["-m", "app.generator.historical_data"]),
    ("Attrition outcomes + ground truth", ["-m", "app.generator.attrition_outcomes"]),
    ("Validate dataset", ["validate_data.py"]),
    ("Point-in-time features", ["-m", "app.analytics.feature_engineering"]),
    ("Validate features", ["validate_features.py"]),
    ("Support scoring", ["-m", "app.analytics.support_scoring"]),
    ("Validate assessments", ["validate_support_assessments.py"]),
    ("Edge-case detection", ["test_edge_cases.py"]),
    ("Evaluate against ground truth", ["evaluate_support_scores.py"]),
]


def main():
    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    started = time.time()

    for number, (name, args) in enumerate(STEPS, start=1):
        print(f"\n[{number}/{len(STEPS)}] {name}", flush=True)

        result = subprocess.run(
            [sys.executable, *args], cwd=BACKEND, env=env
        )

        if result.returncode != 0:
            print(f"\nPipeline stopped: '{name}' failed.")
            sys.exit(result.returncode)

    print(f"\nPipeline finished in {time.time() - started:.0f}s.")


if __name__ == "__main__":
    main()
