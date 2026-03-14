"""
UserStats model + DB queries. Single-row table.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from readwise.db.database import Database


@dataclass
class UserStats:
    current_streak: int
    longest_streak: int
    last_read_date: date | None
    total_books_complete: int
    total_pages_read: int
    total_words_read: int
    badges: list[str]       # list of badge IDs

    @classmethod
    def _from_row(cls, row) -> "UserStats":
        return cls(
            current_streak=row["current_streak"],
            longest_streak=row["longest_streak"],
            last_read_date=(
                date.fromisoformat(row["last_read_date"])
                if row["last_read_date"] else None
            ),
            total_books_complete=row["total_books_complete"],
            total_pages_read=row["total_pages_read"],
            total_words_read=row["total_words_read"],
            badges=json.loads(row["badges"]),
        )


def get_stats() -> UserStats:
    db = Database.get()
    row = db.execute(
        "SELECT * FROM user_stats WHERE id = 'singleton'"
    ).fetchone()
    return UserStats._from_row(row)


def save_stats(stats: UserStats) -> None:
    db = Database.get()
    db.execute("""
        UPDATE user_stats SET
            current_streak       = ?,
            longest_streak       = ?,
            last_read_date       = ?,
            total_books_complete = ?,
            total_pages_read     = ?,
            total_words_read     = ?,
            badges               = ?
        WHERE id = 'singleton'
    """, (
        stats.current_streak,
        stats.longest_streak,
        stats.last_read_date.isoformat() if stats.last_read_date else None,
        stats.total_books_complete,
        stats.total_pages_read,
        stats.total_words_read,
        json.dumps(stats.badges),
    ))
    db.commit()


def add_badge(badge_id: str) -> list[str]:
    """Add a badge if not already earned. Returns full badge list."""
    stats = get_stats()
    if badge_id not in stats.badges:
        stats.badges.append(badge_id)
        save_stats(stats)
    return stats.badges
