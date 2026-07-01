import os
import random
import sqlite3
from datetime import datetime, timezone

from config import DATA_DIR, DB_PATH


def utcnow_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_id TEXT,
                creator_id TEXT NOT NULL,
                prize TEXT NOT NULL,
                prize_image_filename TEXT,
                winner_count INTEGER NOT NULL DEFAULT 1,
                requirements_text TEXT,
                ends_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS drop_entries (
                drop_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                removed_at TEXT,
                removed_by TEXT,
                remove_reason TEXT,
                PRIMARY KEY (drop_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS drop_blocked (
                drop_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT,
                blocked_by TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (drop_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS drop_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drop_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                reroll_index INTEGER NOT NULL DEFAULT 0,
                drawn_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drop_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drop_id INTEGER NOT NULL,
                actor_id TEXT,
                target_user_id TEXT,
                action TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        c = conn.cursor()
        c.execute("PRAGMA table_info(drops)")
        drop_cols = {row[1] for row in c.fetchall()}
        if "prize_image_filename" not in drop_cols:
            c.execute("ALTER TABLE drops ADD COLUMN prize_image_filename TEXT")
        conn.commit()
    print(f"[DROPS] Base de datos lista: {os.path.abspath(DB_PATH)}")


def log_action(conn, drop_id: int, action: str, actor_id=None, target_user_id=None, reason=None):
    conn.execute(
        """
        INSERT INTO drop_logs (drop_id, actor_id, target_user_id, action, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (drop_id, str(actor_id) if actor_id else None, str(target_user_id) if target_user_id else None, action, reason, utcnow_text()),
    )


def create_drop(guild_id, channel_id, creator_id, prize: str, winner_count: int, ends_at, requirements_text: str = "") -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO drops (
                guild_id, channel_id, creator_id, prize, winner_count,
                requirements_text, ends_at, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                str(guild_id),
                str(channel_id),
                str(creator_id),
                prize.strip(),
                max(1, int(winner_count)),
                (requirements_text or "").strip(),
                ends_at.isoformat(),
                utcnow_text(),
            ),
        )
        drop_id = int(cursor.lastrowid)
        log_action(conn, drop_id, "created", actor_id=creator_id)
        conn.commit()
    return drop_id


def set_drop_message(drop_id: int, message_id):
    with get_conn() as conn:
        conn.execute("UPDATE drops SET message_id=? WHERE id=?", (str(message_id), int(drop_id)))
        conn.commit()


def set_drop_image(drop_id: int, filename: str, actor_id=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE drops SET prize_image_filename=? WHERE id=?",
            (filename, int(drop_id)),
        )
        log_action(conn, drop_id, "photo_updated", actor_id=actor_id, reason=filename)
        conn.commit()


def get_drop(drop_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM drops WHERE id=?", (int(drop_id),)).fetchone()


def get_active_drops():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM drops WHERE status='active'").fetchall()


def get_due_drops():
    now = utcnow_text()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM drops WHERE status='active' AND ends_at <= ?",
            (now,),
        ).fetchall()


def count_entries(drop_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM drop_entries WHERE drop_id=? AND active=1",
            (int(drop_id),),
        ).fetchone()
    return int(row["total"] if row else 0)


def list_entries(drop_id: int, limit: int = 10, offset: int = 0):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT user_id, username, joined_at
            FROM drop_entries
            WHERE drop_id=? AND active=1
            ORDER BY joined_at ASC
            LIMIT ? OFFSET ?
            """,
            (int(drop_id), int(limit), int(offset)),
        ).fetchall()


def is_blocked(drop_id: int, user_id) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM drop_blocked WHERE drop_id=? AND user_id=?",
            (int(drop_id), str(user_id)),
        ).fetchone()
    return bool(row)


def add_entry(drop_id: int, user_id, username: str):
    if is_blocked(drop_id, user_id):
        return "blocked"

    with get_conn() as conn:
        drop = conn.execute("SELECT status FROM drops WHERE id=?", (int(drop_id),)).fetchone()
        if not drop or drop["status"] != "active":
            return "closed"

        existing = conn.execute(
            "SELECT active FROM drop_entries WHERE drop_id=? AND user_id=?",
            (int(drop_id), str(user_id)),
        ).fetchone()
        if existing and int(existing["active"]) == 1:
            return "already"

        conn.execute(
            """
            INSERT INTO drop_entries (
                drop_id, user_id, username, joined_at, active,
                removed_at, removed_by, remove_reason
            )
            VALUES (?, ?, ?, ?, 1, NULL, NULL, NULL)
            ON CONFLICT(drop_id, user_id) DO UPDATE SET
                username=excluded.username,
                joined_at=excluded.joined_at,
                active=1,
                removed_at=NULL,
                removed_by=NULL,
                remove_reason=NULL
            """,
            (int(drop_id), str(user_id), username, utcnow_text()),
        )
        log_action(conn, drop_id, "joined", actor_id=user_id, target_user_id=user_id)
        conn.commit()
    return "joined"


def remove_entry(drop_id: int, user_id, actor_id=None, reason: str = "") -> bool:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE drop_entries
            SET active=0, removed_at=?, removed_by=?, remove_reason=?
            WHERE drop_id=? AND user_id=? AND active=1
            """,
            (utcnow_text(), str(actor_id) if actor_id else None, reason or "", int(drop_id), str(user_id)),
        )
        if cursor.rowcount:
            log_action(conn, drop_id, "removed", actor_id=actor_id, target_user_id=user_id, reason=reason)
        conn.commit()
    return cursor.rowcount > 0


def block_entry(drop_id: int, user_id, username: str, actor_id, reason: str = ""):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO drop_blocked (
                drop_id, user_id, username, blocked_by, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(drop_id), str(user_id), username, str(actor_id), reason or "", utcnow_text()),
        )
        conn.execute(
            """
            UPDATE drop_entries
            SET active=0, removed_at=?, removed_by=?, remove_reason=?
            WHERE drop_id=? AND user_id=? AND active=1
            """,
            (utcnow_text(), str(actor_id), reason or "blocked", int(drop_id), str(user_id)),
        )
        log_action(conn, drop_id, "blocked", actor_id=actor_id, target_user_id=user_id, reason=reason)
        conn.commit()


def mark_drop_status(drop_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE drops SET status=?, ended_at=? WHERE id=?",
            (status, utcnow_text(), int(drop_id)),
        )
        log_action(conn, drop_id, status)
        conn.commit()


def draw_winners(drop_id: int, winner_count: int, reroll_index: int = 0, exclude_user_ids=None):
    exclude = {str(user_id) for user_id in (exclude_user_ids or [])}
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT user_id, username
            FROM drop_entries
            WHERE drop_id=? AND active=1
            """,
            (int(drop_id),),
        ).fetchall()

        candidates = [row for row in rows if str(row["user_id"]) not in exclude]
        random.SystemRandom().shuffle(candidates)
        winners = candidates[: max(1, int(winner_count))]

        for winner in winners:
            conn.execute(
                """
                INSERT INTO drop_winners (drop_id, user_id, username, reroll_index, drawn_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (int(drop_id), winner["user_id"], winner["username"], int(reroll_index), utcnow_text()),
            )
        conn.commit()
    return winners


def get_winners(drop_id: int):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT user_id, username, reroll_index, drawn_at
            FROM drop_winners
            WHERE drop_id=?
            ORDER BY id ASC
            """,
            (int(drop_id),),
        ).fetchall()


def latest_reroll_index(drop_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(reroll_index), 0) AS value FROM drop_winners WHERE drop_id=?",
            (int(drop_id),),
        ).fetchone()
    return int(row["value"] if row else 0)
