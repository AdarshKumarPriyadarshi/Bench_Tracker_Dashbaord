import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bench_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bench_status (
            bench_id INTEGER NOT NULL,
            pc_type TEXT NOT NULL CHECK(pc_type IN ('windows', 'linux')),
            status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'occupied')),
            short_id TEXT,
            purpose TEXT,
            access_method TEXT CHECK(access_method IN ('rdp', 'nomachine', 'physical', NULL)),
            start_time TEXT,
            PRIMARY KEY (bench_id, pc_type)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bench_id INTEGER NOT NULL,
            pc_type TEXT NOT NULL,
            short_id TEXT NOT NULL,
            purpose TEXT NOT NULL,
            access_method TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_min REAL
        )
    """)

    for bench_id in range(1, 6):
        for pc_type in ("windows", "linux"):
            cursor.execute(
                "INSERT OR IGNORE INTO bench_status (bench_id, pc_type) VALUES (?, ?)",
                (bench_id, pc_type),
            )

    conn.commit()
    conn.close()


def checkin(bench_id: int, pc_type: str, short_id: str, purpose: str, access_method: str):
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute(
        """UPDATE bench_status
           SET status='occupied', short_id=?, purpose=?, access_method=?, start_time=?
           WHERE bench_id=? AND pc_type=?""",
        (short_id, purpose, access_method, now, bench_id, pc_type),
    )
    conn.commit()
    conn.close()
    return now


def checkout(bench_id: int, pc_type: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM bench_status WHERE bench_id=? AND pc_type=?",
        (bench_id, pc_type),
    ).fetchone()

    if not row or row["status"] == "available":
        conn.close()
        return None

    now = datetime.now().isoformat()
    start = row["start_time"]
    duration = 0.0
    if start:
        start_dt = datetime.fromisoformat(start)
        duration = round((datetime.now() - start_dt).total_seconds() / 60, 2)

    conn.execute(
        """INSERT INTO usage_history
           (bench_id, pc_type, short_id, purpose, access_method, start_time, end_time, duration_min)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (bench_id, pc_type, row["short_id"], row["purpose"], row["access_method"], start, now, duration),
    )

    conn.execute(
        """UPDATE bench_status
           SET status='available', short_id=NULL, purpose=NULL, access_method=NULL, start_time=NULL
           WHERE bench_id=? AND pc_type=?""",
        (bench_id, pc_type),
    )
    conn.commit()
    conn.close()
    return {"end_time": now, "duration_min": duration}


def get_all_benches():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM bench_status ORDER BY bench_id, pc_type").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history(bench_id: int = None, short_id: str = None, limit: int = 100,
                 date_from: str = None, date_to: str = None):
    conn = get_connection()
    query = "SELECT * FROM usage_history WHERE 1=1"
    params = []

    if bench_id:
        query += " AND bench_id=?"
        params.append(bench_id)
    if short_id:
        query += " AND short_id=?"
        params.append(short_id)
    if date_from:
        query += " AND start_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND start_time <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
