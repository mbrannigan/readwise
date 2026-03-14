"""
SQLite connection and migration runner.
Database file lives in the platform-appropriate app data directory.
"""
import sqlite3
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """Return the platform-appropriate directory for app data."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    app_dir = base / "readwise"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_migrations_dir() -> Path:
    return Path(__file__).parent / "migrations"


class Database:
    _instance: "Database | None" = None

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = get_app_data_dir() / "readwise.db"
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._run_migrations()

    @classmethod
    def get(cls) -> "Database":
        """Return the singleton database instance."""
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    @classmethod
    def init(cls, db_path: Path | None = None) -> "Database":
        """Initialize the singleton (call once at startup)."""
        cls._instance = Database(db_path)
        return cls._instance

    def _run_migrations(self) -> None:
        """Run all SQL migration files in order, skipping already-applied ones."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()

        migrations_dir = get_migrations_dir()
        migration_files = sorted(migrations_dir.glob("*.sql"))

        applied = {
            row[0] for row in self.conn.execute("SELECT filename FROM _migrations")
        }

        for migration_file in migration_files:
            if migration_file.name in applied:
                continue
            sql = migration_file.read_text(encoding="utf-8")
            self.conn.executescript(sql)
            self.conn.execute(
                "INSERT INTO _migrations (filename) VALUES (?)",
                (migration_file.name,),
            )
            self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_seq)

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
