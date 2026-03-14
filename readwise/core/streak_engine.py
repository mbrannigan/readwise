"""
Streak calculation. Called after every completed reading session.
"""
from __future__ import annotations

from datetime import date, timedelta

from readwise.db.models.stats import UserStats, get_stats, save_stats


def update_streak(session_date: date | None = None) -> UserStats:
    """
    Update streak after a reading session. Returns updated stats.
    - Streak increments if user read today or yesterday (grace: same-day multi-sessions don't double-count).
    - Streak resets to 1 if more than 1 day was missed.
    """
    stats = get_stats()
    today = session_date or date.today()

    if stats.last_read_date is None:
        # First ever session
        stats.current_streak = 1
    elif stats.last_read_date == today:
        # Already read today — no change to streak count
        pass
    elif stats.last_read_date == today - timedelta(days=1):
        # Read yesterday — extend streak
        stats.current_streak += 1
    else:
        # Gap of 2+ days — reset
        stats.current_streak = 1

    stats.last_read_date = today
    stats.longest_streak = max(stats.longest_streak, stats.current_streak)

    save_stats(stats)
    return stats
