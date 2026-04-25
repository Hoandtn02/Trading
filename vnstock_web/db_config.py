"""
SQLite Database Configuration with WAL Mode
Enables Write-Ahead Logging for better concurrency
"""
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db.sqlite3"

def configure_sqlite_wal():
    """
    Configure SQLite to use WAL mode for better concurrency.
    This allows multiple readers while a write is in progress.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Enable WAL mode (Write-Ahead Logging)
        cursor.execute("PRAGMA journal_mode=WAL;")

        # Increase busy timeout to wait longer for locks
        cursor.execute("PRAGMA busy_timeout=30000;")  # 30 seconds

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON;")

        # Set synchronous to NORMAL for better performance
        cursor.execute("PRAGMA synchronous=NORMAL;")

        conn.commit()
        conn.close()

        print(f"[DB Config] SQLite WAL mode enabled at {DB_PATH}")
        return True
    except Exception as e:
        print(f"[DB Config] Error configuring SQLite: {e}")
        return False

# Run on module import
configure_sqlite_wal()
