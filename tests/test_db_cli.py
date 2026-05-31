"""
Test that `python -m src.utils.database` actually initializes the database.

The README documents this command for first-time setup and as the fix for
"Database errors on startup". Previously the module had no __main__ entry
point, so the command silently did nothing.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_database_module_main_creates_db(tmp_path):
    """Running the module as a script should create a SQLite DB with tables."""
    db_file = tmp_path / "cli_init.db"

    result = subprocess.run(
        [sys.executable, "-m", "src.utils.database", "--db-path", str(db_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert db_file.exists(), "database file was not created"

    # Verify the core tables exist.
    import sqlite3

    conn = sqlite3.connect(db_file)
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()

    for expected in ("positions", "trade_logs", "markets", "llm_queries"):
        assert expected in names, f"missing table {expected}; got {names}"
