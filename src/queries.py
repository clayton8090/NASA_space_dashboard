"""Phase 4: read-only queries the dashboard uses. Kept separate from the UI so they can be tested."""
from datetime import date

import pandas as pd

FLARE_ORDER = ["A", "B", "C", "M", "X"]  # weakest to strongest


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def date_bounds(conn):
    """Earliest and latest dates across asteroids and flares, or (None, None) if empty."""
    low, high = conn.execute(
        """
        SELECT MIN(d), MAX(d) FROM (
            SELECT approach_date AS d FROM asteroid_approaches
            UNION ALL
            SELECT substr(begin_time, 1, 10) FROM solar_flares
        )
        """
    ).fetchone()
    if low is None or high is None:
        return None, None
    return date.fromisoformat(low), date.fromisoformat(high)


def load_asteroids(conn, start, end, hazardous_only=False):
    sql = "SELECT * FROM asteroid_approaches WHERE approach_date BETWEEN ? AND ?"
    if hazardous_only:
        sql += " AND is_hazardous = 1"
    sql += " ORDER BY approach_date, miss_distance_km"
    df = pd.read_sql_query(sql, conn, params=[_iso(start), _iso(end)])
    df["is_hazardous"] = df["is_hazardous"].fillna(0).astype(bool)
    return df


def load_flares(conn, start, end, min_class="A"):
    """Flares in a date range at or above a minimum class letter (A < B < C < M < X)."""
    sql = "SELECT * FROM solar_flares WHERE substr(begin_time, 1, 10) BETWEEN ? AND ?"
    params = [_iso(start), _iso(end)]
    if min_class != "A":
        allowed = FLARE_ORDER[FLARE_ORDER.index(min_class):]
        sql += f" AND class_letter IN ({', '.join('?' for _ in allowed)})"
        params += allowed
    sql += " ORDER BY begin_time"
    return pd.read_sql_query(sql, conn, params=params)


def latest_apod(conn):
    """The most recent APOD row as a dict, or None."""
    df = pd.read_sql_query("SELECT * FROM apod ORDER BY apod_date DESC LIMIT 1", conn)
    if df.empty:
        return None
    return {k: (None if pd.isna(v) else v) for k, v in df.iloc[0].to_dict().items()}
