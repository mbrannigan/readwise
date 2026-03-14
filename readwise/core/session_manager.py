"""
Session manager: orchestrates start/end of a reading session,
updates stats and streak, marks chunk complete.
"""
from __future__ import annotations

from datetime import date

from readwise.db.models.reading_plan import get_todays_chunk, mark_chunk_complete
from readwise.db.models.session import (
    ReadingSession,
    end_session,
    get_session,
    start_session,
)
from readwise.db.models.stats import get_stats, save_stats
from readwise.core.streak_engine import update_streak


def begin_session(book_id: str) -> ReadingSession:
    """Start a reading session for a book, using today's chunk if one exists."""
    chunk = get_todays_chunk(book_id)
    chunk_id = chunk.id if chunk else None
    return start_session(book_id, chunk_id)


def finish_session(
    session_id: str,
    pages_read: int,
    words_read: int,
    mark_chunk_done: bool = True,
) -> ReadingSession:
    """
    End a reading session:
    1. Record end time + pages/words.
    2. Mark the chunk complete (if applicable and requested).
    3. Update global stats (totals, streak).
    """
    end_session(session_id, pages_read, words_read)
    session = get_session(session_id)

    if session and mark_chunk_done and session.chunk_id:
        mark_chunk_complete(session.chunk_id)

    # Update running totals
    stats = get_stats()
    stats.total_pages_read += pages_read
    stats.total_words_read += words_read
    save_stats(stats)

    # Update streak
    update_streak()

    return session
