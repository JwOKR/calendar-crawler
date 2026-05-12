"""
SQLite 数据库操作
"""
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent.parent / "data" / "calendar.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            name TEXT,
            last_crawled TEXT,
            crawl_interval_hours INTEGER NOT NULL DEFAULT 24,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            sub_id TEXT NOT NULL,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            location TEXT,
            description TEXT,
            uid TEXT NOT NULL,
            FOREIGN KEY (sub_id) REFERENCES subscriptions(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_events_sub_id ON events(sub_id);
        CREATE INDEX IF NOT EXISTS idx_events_uid ON events(uid);
    """)
    conn.commit()
    conn.close()


def create_subscription(url: str, name: Optional[str] = None, crawl_interval_hours: int = 24) -> str:
    """创建订阅记录，返回订阅 ID"""
    sub_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO subscriptions (id, url, name, last_crawled, crawl_interval_hours, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (sub_id, url, name, None, crawl_interval_hours, now)
    )
    conn.commit()
    conn.close()
    return sub_id


def get_subscription(sub_id: str) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_subscriptions() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, COUNT(e.id) as event_count
        FROM subscriptions s
        LEFT JOIN events e ON s.id = e.sub_id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_subscription(sub_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()


def update_last_crawled(sub_id: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("UPDATE subscriptions SET last_crawled = ? WHERE id = ?", (now, sub_id))
    conn.commit()
    conn.close()


def replace_events(sub_id: str, events: List[Dict]):
    """替换某个订阅下的所有事件"""
    conn = get_conn()
    conn.execute("DELETE FROM events WHERE sub_id = ?", (sub_id,))
    for ev in events:
        uid = ev.get("uid") or uuid.uuid4().hex
        conn.execute(
            "INSERT OR REPLACE INTO events (id, sub_id, title, start_time, end_time, location, description, uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex[:12], sub_id, ev["title"], ev["start_time"],
             ev.get("end_time"), ev.get("location"), ev.get("description"), uid)
        )
    conn.commit()
    conn.close()


def get_events_for_ics(sub_id: str) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM events WHERE sub_id = ?", (sub_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_subscriptions_for_scheduler() -> List[Dict]:
    """获取所有订阅，供调度器使用"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    conn.close()
    return [dict(r) for r in rows]
