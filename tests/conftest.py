import sys
from pathlib import Path

# Add project root to sys.path
proj_root = Path(__file__).resolve().parent.parent
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

# The SQLite fixture is intentionally generated from source so fresh clones and CI
# receive the same deterministic demo data without checking a binary database in.
from data.create_db import create_sample_database

db_path = proj_root / "data" / "ecommerce.db"
if not db_path.exists():
    create_sample_database(db_path)
