"""DuckDB connection management for the hoops-lab analytical database."""

from __future__ import annotations

import logging
import threading
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
        #: Serialises every use of the single connection. A DuckDB connection is not
        #: thread-safe, and the dashboard shares one Database between all sessions, each
        #: running in its own thread: without the lock some queries return None. Hold it
        #: (re-entrant) around any multi-step use, e.g. register() followed by a query.
        self.lock = threading.RLock()

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Open (or reuse) the connection to the database file."""
        with self.lock:
            return self._connect()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            try:
                self._conn = duckdb.connect(self.path, read_only=self.read_only)
            except duckdb.IOException as exc:
                # The file is a cache rebuilt from parquet by ensure_db_ready(): one this
                # DuckDB cannot read (written by another version, truncated) is replaced.
                # A lock held by another process is a real conflict and still raises.
                if self.read_only or self.path == ":memory:" or "lock" in str(exc).lower():
                    raise
                logger.warning("Unreadable DuckDB file %s, rebuilding it: %s", self.path, exc)
                for stale in (Path(self.path), Path(f"{self.path}.wal")):
                    stale.unlink(missing_ok=True)
                self._conn = duckdb.connect(self.path)
            logger.info("Connected to DuckDB at %s", self.path)
        return self._conn

    def close(self) -> None:
        """Close the connection if open."""
        with self.lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> Database:
        self.connect()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def execute(self, sql: str, params: list[Any] | None = None) -> duckdb.DuckDBPyConnection:
        """Execute a SQL statement, optionally with positional parameters.

        For statements; read results through :meth:`query_df` / :meth:`fetchone`, which
        fetch while still holding the lock (or hold ``self.lock`` yourself).
        """
        with self.lock:
            return self.connect().execute(sql, params or [])

    def query_df(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        """Run a query and return the result as a pandas DataFrame."""
        with self.lock:
            return self.connect().execute(sql, params or []).df()

    def fetchone(self, sql: str, params: list[Any] | None = None) -> tuple | None:
        """Run a query and return its first row (None when there is none)."""
        with self.lock:
            return self.connect().execute(sql, params or []).fetchone()

    def has_table(self, name: str) -> bool:
        """Return True if a table with this name exists in the main schema."""
        row = self.fetchone(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
        )
        return bool(row and row[0])

    def table_rows(self, name: str) -> int:
        """Return the row count of a table (0 if the table does not exist)."""
        if not self.has_table(name):
            return 0
        row = self.fetchone(f'SELECT count(*) FROM "{name}"')
        return int(row[0]) if row else 0

    def run_migrations(self) -> list[str]:
        """Apply pending SQL migrations from ``storage/migrations``, in order.

        Applied file names are tracked in the ``schema_migrations`` table, so
        the operation is idempotent.

        Returns
        -------
        The list of migration file names applied by this call.
        """
        with self.lock:
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
        versioned Parquet files on every boot. It is also rebuilt when the
        parquet changed since the last seed (a data push updates the hosted
        repo in place, without a restart).

        Parameters
        ----------
        raw_dir:
            Parquet source; see ``seed.source_dir`` (default: the versioned
            ``data/processed``).
        force:
            Reseed even if the database already contains data.

        Returns
        -------
        True if a (re)seed was performed, False if the DB was already ready.
        """
        from hoops_lab.storage.seed import (  # local import: avoid cycle
            seed_database,
            source_dir,
            source_fingerprint,
        )

        with self.lock:  # the seed registers frames on the connection between statements
            self.run_migrations()
            ready = self.table_rows("games") > 0 and all(self.has_table(t) for t in DERIVED_TABLES)
            # Hosts update the repo in place after a data push without restarting the app:
            # a database built from other parquet than the current ones is stale.
            fingerprint = source_fingerprint(source_dir(raw_dir, fallback_dir))
            ready = (
                ready
                and self.has_table("seed_source")
                and self.fetchone("SELECT fingerprint FROM seed_source") == (fingerprint,)
            )
            if not force and ready:
                return False
            seed_database(self, raw_dir=raw_dir, fallback_dir=fallback_dir)
            return True
