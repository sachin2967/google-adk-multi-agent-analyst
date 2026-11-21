"""Model Context Protocol (MCP) standardized tools for analytical data operations."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from src.sandbox.executor import SandboxedPythonExecutor


class SafeSQLQueryTool:
    """Executes read-only SQL queries against the analytical database."""

    DISALLOWED_KEYWORDS = {"drop", "delete", "insert", "update", "alter", "truncate", "create", "grant"}

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Validates and executes read-only SQL."""
        query_clean = sql_query.strip().lower()

        # Check for forbidden mutation commands
        tokens = query_clean.split()
        if any(keyword in tokens for keyword in self.DISALLOWED_KEYWORDS):
            return {
                "success": False,
                "error": "Security Error: Mutating SQL queries (INSERT, UPDATE, DELETE, DROP) are strictly forbidden.",
                "data": None,
            }

        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()

            return {
                "success": True,
                "row_count": len(df),
                "columns": list(df.columns),
                "data": df.head(50).to_dict(orient="records"),
                "dataframe": df,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SQL Execution Error: {e}",
                "data": None,
            }


class SchemaInspectionTool:
    """Inspects database schema, table structures, and foreign key relationships."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_full_schema(self) -> Dict[str, Any]:
        """Returns schemas for all tables with column types and primary/foreign keys."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]

        schema_info = {}
        for t in tables:
            cur.execute(f"PRAGMA table_info({t});")
            cols = [{"cid": r[0], "name": r[1], "type": r[2], "notnull": bool(r[3]), "pk": bool(r[5])} for r in cur.fetchall()]

            cur.execute(f"PRAGMA foreign_key_list({t});")
            fks = [{"table": r[2], "from": r[3], "to": r[4]} for r in cur.fetchall()]

            # Sample 2 rows
            sample_df = pd.read_sql_query(f"SELECT * FROM {t} LIMIT 2;", conn)

            schema_info[t] = {
                "columns": cols,
                "foreign_keys": fks,
                "sample_records": sample_df.to_dict(orient="records"),
            }

        conn.close()
        return schema_info


class MCPToolRegistry:
    """Standardized tool registry exposing JSON-schema compliant tools."""

    def __init__(self, db_path: Path):
        self.sql_tool = SafeSQLQueryTool(db_path)
        self.schema_tool = SchemaInspectionTool(db_path)
        self.sandbox = SandboxedPythonExecutor()

    def get_tools_description(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool signatures."""
        return [
            {
                "name": "inspect_database_schema",
                "description": "Inspects relational database tables, columns, data types, and foreign key relationships.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "execute_safe_sql",
                "description": "Executes read-only SQL queries to retrieve tabular data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The SELECT SQL query string to run."}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "execute_sandboxed_pandas",
                "description": "Runs sandboxed Python/Pandas code for data transformations, percentage changes, or rolling metrics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Safe Python code snippet operating on DataFrame 'df'."}
                    },
                    "required": ["code"],
                },
            },
        ]
