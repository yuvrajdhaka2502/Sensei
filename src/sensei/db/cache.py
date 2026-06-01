from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date as Date, datetime
from pathlib import Path
from typing import Iterator, Literal

Slot = Literal["morning", "evening"]
CheckinState = Literal["NONE", "SENT", "IN_PROGRESS", "DONE", "SKIPPED", "MISSED"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkin_state (
    user_id     TEXT NOT NULL,
    date        TEXT NOT NULL,
    slot        TEXT NOT NULL,
    state       TEXT NOT NULL,
    sent_at     TEXT,
    completed_at TEXT,
    PRIMARY KEY (user_id, date, slot)
);

CREATE INDEX IF NOT EXISTS idx_checkin_state_lookup
    ON checkin_state(user_id, date);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _conn(db_path) as c:
        c.executescript(_SCHEMA)


@contextmanager
def _conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_checkin_state(db_path: Path, user_id: str, d: Date, slot: Slot) -> CheckinState:
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT state FROM checkin_state WHERE user_id=? AND date=? AND slot=?",
            (user_id, d.isoformat(), slot),
        ).fetchone()
        return row["state"] if row else "NONE"


def set_checkin_state(
    db_path: Path,
    user_id: str,
    d: Date,
    slot: Slot,
    state: CheckinState,
) -> None:
    now = datetime.utcnow().isoformat()
    sent_at = now if state == "SENT" else None
    completed_at = now if state in ("DONE", "SKIPPED", "MISSED") else None
    with _conn(db_path) as c:
        c.execute(
            """
            INSERT INTO checkin_state(user_id, date, slot, state, sent_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date, slot) DO UPDATE SET
                state = excluded.state,
                sent_at = COALESCE(excluded.sent_at, checkin_state.sent_at),
                completed_at = COALESCE(excluded.completed_at, checkin_state.completed_at)
            """,
            (user_id, d.isoformat(), slot, state, sent_at, completed_at),
        )
