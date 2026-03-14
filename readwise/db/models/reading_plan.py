"""
ReadingPlan and Chunk models + DB queries.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from readwise.db.database import Database


@dataclass
class ReadingPlan:
    id: str
    book_id: str
    chunk_strategy: str     # PAGES | CHAPTERS | SECTIONS | TIME
    chunk_size: int
    start_date: date
    target_end_date: date
    daily_goal_time: str | None   # "HH:MM" or None
    created_at: str

    @classmethod
    def _from_row(cls, row) -> "ReadingPlan":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            chunk_strategy=row["chunk_strategy"],
            chunk_size=row["chunk_size"],
            start_date=date.fromisoformat(row["start_date"]),
            target_end_date=date.fromisoformat(row["target_end_date"]),
            daily_goal_time=row["daily_goal_time"],
            created_at=row["created_at"],
        )


@dataclass
class Chunk:
    id: str
    plan_id: str
    book_id: str
    sequence: int
    label: str
    start_location: str
    end_location: str
    scheduled_date: date
    completed_date: date | None

    @property
    def is_complete(self) -> bool:
        return self.completed_date is not None

    @classmethod
    def _from_row(cls, row) -> "Chunk":
        return cls(
            id=row["id"],
            plan_id=row["plan_id"],
            book_id=row["book_id"],
            sequence=row["sequence"],
            label=row["label"],
            start_location=row["start_location"],
            end_location=row["end_location"],
            scheduled_date=date.fromisoformat(row["scheduled_date"]),
            completed_date=(
                date.fromisoformat(row["completed_date"])
                if row["completed_date"] else None
            ),
        )


# ---------------------------------------------------------------------------
# ReadingPlan queries
# ---------------------------------------------------------------------------

def get_plan_for_book(book_id: str) -> ReadingPlan | None:
    db = Database.get()
    row = db.execute(
        "SELECT * FROM reading_plans WHERE book_id = ? ORDER BY created_at DESC LIMIT 1",
        (book_id,),
    ).fetchone()
    return ReadingPlan._from_row(row) if row else None


def insert_plan(plan: ReadingPlan) -> None:
    db = Database.get()
    db.execute("""
        INSERT INTO reading_plans
            (id, book_id, chunk_strategy, chunk_size, start_date,
             target_end_date, daily_goal_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plan.id, plan.book_id, plan.chunk_strategy, plan.chunk_size,
        plan.start_date.isoformat(), plan.target_end_date.isoformat(),
        plan.daily_goal_time, plan.created_at,
    ))
    db.commit()


def new_plan_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Chunk queries
# ---------------------------------------------------------------------------

def get_chunks_for_plan(plan_id: str) -> list[Chunk]:
    db = Database.get()
    rows = db.execute(
        "SELECT * FROM chunks WHERE plan_id = ? ORDER BY sequence",
        (plan_id,),
    ).fetchall()
    return [Chunk._from_row(r) for r in rows]


def get_todays_chunk(book_id: str) -> Chunk | None:
    """Return the first incomplete chunk scheduled on or before today."""
    db = Database.get()
    today = date.today().isoformat()
    row = db.execute("""
        SELECT c.* FROM chunks c
        JOIN reading_plans p ON c.plan_id = p.id
        WHERE c.book_id = ?
          AND c.completed_date IS NULL
          AND c.scheduled_date <= ?
        ORDER BY c.sequence
        LIMIT 1
    """, (book_id, today)).fetchone()
    return Chunk._from_row(row) if row else None


def insert_chunks(chunks: list[Chunk]) -> None:
    db = Database.get()
    db.executemany("""
        INSERT INTO chunks
            (id, plan_id, book_id, sequence, label, start_location,
             end_location, scheduled_date, completed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (c.id, c.plan_id, c.book_id, c.sequence, c.label,
         c.start_location, c.end_location,
         c.scheduled_date.isoformat(), None)
        for c in chunks
    ])
    db.commit()


def mark_chunk_complete(chunk_id: str, completed_date: date | None = None) -> None:
    db = Database.get()
    completed = (completed_date or date.today()).isoformat()
    db.execute(
        "UPDATE chunks SET completed_date = ? WHERE id = ?",
        (completed, chunk_id),
    )
    db.commit()


def new_chunk_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Last-position helpers
# ---------------------------------------------------------------------------

def get_last_chunk_index(plan_id: str) -> int:
    db = Database.get()
    row = db.execute(
        "SELECT last_chunk_index FROM reading_plans WHERE id = ?", (plan_id,)
    ).fetchone()
    return row["last_chunk_index"] if row else 0


def save_last_chunk_index(plan_id: str, index: int) -> None:
    db = Database.get()
    db.execute(
        "UPDATE reading_plans SET last_chunk_index = ? WHERE id = ?",
        (index, plan_id),
    )
    db.commit()


def get_last_scroll_pct(plan_id: str) -> int:
    db = Database.get()
    row = db.execute(
        "SELECT last_scroll_pct FROM reading_plans WHERE id = ?", (plan_id,)
    ).fetchone()
    return row["last_scroll_pct"] if row else 0


def save_last_scroll_pct(plan_id: str, pct: int) -> None:
    db = Database.get()
    db.execute(
        "UPDATE reading_plans SET last_scroll_pct = ? WHERE id = ?",
        (pct, plan_id),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------

def delete_plan_for_book(book_id: str) -> None:
    """Delete all reading plans and their chunks for a book."""
    db = Database.get()
    rows = db.execute(
        "SELECT id FROM reading_plans WHERE book_id = ?", (book_id,)
    ).fetchall()
    for row in rows:
        db.execute("DELETE FROM chunks WHERE plan_id = ?", (row["id"],))
    db.execute("DELETE FROM reading_plans WHERE book_id = ?", (book_id,))
    db.commit()
