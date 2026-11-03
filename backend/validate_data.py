
import csv
import json
from pathlib import Path

from app.database import SessionLocal
from app.validation.data_quality import validate_database


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    session = SessionLocal()

    try:
        report = validate_database(session)

        # Save complete validation report
        report_path = output_dir / "validation_report.json"

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)

        # Save detected issues separately
        issues_path = output_dir / "validation_issues.csv"

        with open(issues_path, "w", newline="", encoding="utf-8") as file:
            fieldnames = [
                "rule_id",
                "table",
                "record_id",
                "severity",
                "message",
            ]

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report["issues"])

        print("\n========== DATA VALIDATION REPORT ==========")
        print(f"Employees: {report['total_employees']}")
        print(f"Roles: {report['total_roles']}")
        print(f"Teams: {report['total_teams']}")
        print(f"Assignments: {report['total_assignments']}")
        print(f"Tenure snapshots: {report['total_tenure_snapshots']}")
        print(f"Engagement surveys: {report['total_surveys']}")
        print(f"Workload snapshots: {report['total_workload_snapshots']}")
        print(f"Promotions: {report['total_promotions']}")
        print(f"Attrition outcomes: {report['total_outcomes']}")
        print(
            "Voluntary attrition rate: "
            f"{report['voluntary_attrition_rate_pct']}%"
        )
        print("--------------------------------------------")
        print(f"Errors: {report['error_count']}")
        print(f"Warnings: {report['warning_count']}")
        print(f"Passed: {report['passed']}")
        print("--------------------------------------------")

        if report["issues"]:
            print("\nFirst 20 detected issues:")

            for issue in report["issues"][:20]:
                print(
                    f"[{issue['severity']}] "
                    f"{issue['rule_id']} | "
                    f"{issue['table']} | "
                    f"{issue['record_id']} | "
                    f"{issue['message']}"
                )
        else:
            print("No validation issues detected.")

        print("\nReports saved:")
        print(report_path)
        print(issues_path)

    finally:
        session.close()


if __name__ == "__main__":
    main()
