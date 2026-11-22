"""Run tool-level aggregate cross-checks (not an LLM benchmark)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.benchmark import run_tool_regression


def main() -> int:
    from data.create_db import create_sample_database

    db_path = ROOT / "data" / "ecommerce.db"
    if not db_path.exists():
        create_sample_database(db_path)
    report = run_tool_regression(db_path)
    output = ROOT / "tool_regression_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved tool regression report to {output}")
    return 0 if report["checks_passed"] == report["checks_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
