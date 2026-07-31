"""DuckDB connection management for the hoops-lab analytical database."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from hoops_lab.config import DB_PATH
from hoops_lab.storage.models import DERIVED_TABLES

logger = logging.getLogger(__name__)

#: Directory holding the ordered SQL migration scripts.
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """Thin wrapper around a DuckDB database file.

    Parameters
    ----------
    path:
        Database file location (default from ``DB_PATH``); parent directories
        are created on first connection. Use ``":memory:"`` for throwaway DBs.
    read_only:
        Open the file in read-only mode (requires the file to exist).
    """

    def __init__(self, path: str | Path = DB_PATH, read_only: bool = False) -> None:
        self.path = str(path)
        self.read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Open (or reuse) the connection to the database file."""
        if self._conn is None:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self.path, read_only=self.read_only)
            logger.info("Connected to DuckDB at %s", self.path)
        return self._conn

    def close(self) -> None:
        """Close the connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> Database:
        self.connect()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def execute(self, sql: str, params: list[Any] | None = None) -> duckdb.DuckDBPyConnection:
        """Execute a SQL statement, optionally with positional parameters."""
        return self.connect().execute(sql, params or [])

    def query_df(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        """Run a query and return the result as a pandas DataFrame."""
        return self.execute(sql, params).df()

    def has_table(self, name: str) -> bool:
        """Return True if a table with this name exists in the main schema."""
        row = self.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [name],
        ).fetchone()
        return bool(row and row[0])

    def table_rows(self, name: str) -> int:
        """Return the row count of a table (0 if the table does not exist)."""
        if not self.has_table(name):
            return 0
        row = self.execute(f'SELECT count(*) FROM "{name}"').fetchone()
        return int(row[0]) if row else 0

    def run_migrations(self) -> list[str]:
        """Apply pending SQL migrations from ``storage/migrations``, in order.

        Applied file names are tracked in the ``schema_migrations`` table, so
        the operation is idempotent.

        Returns
        -------
        The list of migration file names applied by this call.
        """
        con = self.connect()
        con.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "filename VARCHAR PRIMARY KEY, applied_at TIMESTAMP DEFAULT current_timestamp)"
        )
        applied = {
            row[0] for row in con.execute("SELECT filename FROM schema_migrations").fetchall()
        }

        newly_applied: list[str] = []
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name in applied:
                continue
            con.execute(sql_file.read_text(encoding="utf-8"))
            con.execute("INSERT INTO schema_migrations (filename) VALUES (?)", [sql_file.name])
            newly_applied.append(sql_file.name)
            logger.info("Applied migration %s", sql_file.name)
        return newly_applied

    def ensure_db_ready(
        self,
        raw_dir: str | Path | None = None,
        force: bool = False,
        fallback_dir: str | Path | None = None,
    ) -> bool:
        """Make sure the database exists and is seeded; rebuild it if not.

        Called at dashboard startup: the hosted demo has an ephemeral
        filesystem, so the DuckDB file may need to be rebuilt from the
        versioned Parquet files on every boot.

        Parameters
        ----------
        raw_dir:
            Directory with the raw Parquet files (default: the ingestion
            layer's ``RAW_DATA_DIR``).
        force:
            Reseed even if the database already contains data.

        Returns
        -------
        True if a (re)seed was performed, False if the DB was already ready.
        """
        from hoops_lab.storage.seed import seed_database  # local import: avoid cycle

        self.run_migrations()
        ready = self.table_rows("games") > 0 and all(self.has_table(t) for t in DERIVED_TABLES)
        if not force and ready:
            return False
        seed_database(self, raw_dir=raw_dir, fallback_dir=fallback_dir)
        return True
