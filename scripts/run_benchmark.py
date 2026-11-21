"""Runs the 30-question comparative benchmark and records metrics."""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.benchmark import run_comparative_benchmark


def main():
    proj_root = Path(__file__).resolve().parent.parent
    db_file = proj_root / "data" / "ecommerce.db"

    if not db_file.exists():
        print("Database not found. Initializing...")
        from data.create_db import create_sample_database
        create_sample_database(db_file)

    print("==================================================")
    print("🚀 RUNNING 30-QUESTION COMPARATIVE BENCHMARK")
    print("Baseline (Single-Agent) vs Google ADK Multi-Agent")
    print("==================================================")

    results = run_comparative_benchmark(db_file)

    out_file = proj_root / "benchmark_report.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    print(f"\n✅ Benchmark results saved to: {out_file}")


if __name__ == "__main__":
    main()
