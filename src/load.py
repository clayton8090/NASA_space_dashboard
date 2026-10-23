"""Phase 3: write cleaned tables into SQLite, safe to rerun."""
import os
import sqlite3
from pathlib import Path

LOCAL_DB = Path("data/local.db")   # your own runs; ignored by git
SHARED_DB = Path("data/space.db")  # written by the daily GitHub Actions job; tracked by git

SCHEMA = """
CREATE TABLE IF NOT EXISTS asteroid_approaches (
    asteroid_id TEXT NOT NULL,
    name TEXT,
    approach_date TEXT NOT NULL,
    diameter_min_m REAL,
    diameter_max_m REAL,
    velocity_kps REAL,
    miss_distance_km REAL,
    miss_distance_lunar REAL,
    is_hazardous INTEGER,
    PRIMARY KEY (asteroid_id, approach_date)
);

CREATE TABLE IF NOT EXISTS solar_flares (
    flare_id TEXT PRIMARY KEY,
    begin_time TEXT,
    peak_time TEXT,
    end_time TEXT,
    duration_min REAL,
    class_type TEXT,
    class_letter TEXT,
    class_magnitude REAL,
    source_location TEXT,
    active_region INTEGER
);

CREATE TABLE IF NOT EXISTS apod (
    apod_date TEXT PRIMARY KEY,
    title TEXT,
    media_type TEXT,
    explanation TEXT,
    credit TEXT,
    credit_url TEXT,
    image_url TEXT,
    page_url TEXT
);
"""

KEYS = {
    "asteroid_approaches": ["asteroid_id", "approach_date"],
    "solar_flares": ["flare_id"],
    "apod": ["apod_date"],
}


def write_db_path():
    """Where the pipeline writes: SPACE_DB_PATH if set, otherwise your local database."""
    return Path(os.getenv("SPACE_DB_PATH", str(LOCAL_DB)))


def read_db_path():
    """Where the dashboard reads: SPACE_DB_PATH, else your local database, else the shared one."""
    env = os.getenv("SPACE_DB_PATH")
    if env:
        return Path(env)
    return LOCAL_DB if LOCAL_DB.exists() else SHARED_DB


def connect(db_path=None):
    """Open the database for writing (creating the file and tables if needed)."""
    db_path = write_db_path() if db_path is None else db_path
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def connect_readonly(db_path):
    """Open an existing database read-only (the dashboard can never change data). None if missing."""
    path = Path(db_path)
    if not path.exists():
        return None
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def _rows(df):
    """Convert a DataFrame to plain Python rows, turning NaN/NaT into None (SQL NULL)."""
    return df.astype(object).where(df.notna(), None).values.tolist()


def upsert(conn, table, df):
    """Insert rows, or update them if the primary key already exists."""
    if df is None or df.empty:
        return 0
    columns = list(df.columns)
    keys = KEYS[table]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in keys)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {updates}"
    )
    conn.executemany(sql, _rows(df))
    return len(df)


def load_all(conn, neo=None, flares=None, apod=None):
    """Load whichever tables we have, in one all-or-nothing transaction."""
    with conn:
        return {
            "asteroid_approaches": upsert(conn, "asteroid_approaches", neo),
            "solar_flares": upsert(conn, "solar_flares", flares),
            "apod": upsert(conn, "apod", apod),
        }
