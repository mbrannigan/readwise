"""
ReadingSession model + DB queries.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from readwise.db.database import Database


@dataclass
class ReadingSession:
    id: str
    book_id: str
    chunk_id: str | None
    started_at: datetime
    ended_at: datetime | None
    pages_read: int
    words_read: int
    synced_to_obsidian: bool

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @classmethod
    def _from_row(cls, row) -> "ReadingSession":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            chunk_id=row["chunk_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=(
                datetime.fromisoformat(row["ended_at"])
                if row["ended_at"] else None
            ),
            pages_read=row["pages_read"],
            words_read=row["words_read"],
            synced_to_obsidian=bool(row["synced_to_obsidian"]),
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def start_session(book_id: str, chunk_id: str | None) -> ReadingSession:
    db = Database.get()
    session = ReadingSession(
        id=str(uuid.uuid4()),
        book_id=book_id,
        chunk_id=chunk_id,
        started_at=datetime.now(),
        ended_at=None,
        pages_read=0,
        words_read=0,
        synced_to_obsidian=False,
    )
    db.execute("""
        INSERT INTO reading_sessions
            (id, book_id, chunk_id, started_at, ended_at,
             pages_read, words_read, synced_to_obsidian)
        VALUES (?, ?, ?, ?, NULL, 0, 0, 0)
    """, (session.id, session.book_id, session.chunk_id,
          session.started_at.isoformat()))
    db.commit()
    return session


def end_session(session_id: str, pages_read: int, words_read: int) -> None:
    db = Database.get()
    db.execute("""
        UPDATE reading_sessions
        SET ended_at = datetime('now'), pages_read = ?, words_read = ?
        WHERE id = ?
    """, (pages_read, words_read, session_id))
    db.commit()


def mark_session_synced(session_id: str) -> None:
    db = Database.get()
    db.execute(
        "UPDATE reading_sessions SET synced_to_obsidian = 1 WHERE id = ?",
        (session_id,),
    )
    db.commit()


def get_unsynced_sessions(book_id: str) -> list[ReadingSession]:
    db = Database.get()
    rows = db.execute("""
        SELECT * FROM reading_sessions
        WHERE book_id = ? AND synced_to_obsidian = 0 AND ended_at IS NOT NULL
        ORDER BY started_at
    """, (book_id,)).fetchall()
    return [ReadingSession._from_row(r) for r in rows]


def get_session(session_id: str) -> ReadingSession | None:
    db = Database.get()
    row = db.execute(
        "SELECT * FROM reading_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    return ReadingSession._from_row(row) if row else None
