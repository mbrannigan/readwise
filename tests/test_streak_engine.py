"""Tests for streak_engine.py"""
import pytest
from datetime import date

from readwise.core.streak_engine import update_streak
from readwise.db.models.stats import UserStats, save_stats, get_stats


def reset_stats(last_read: date | None = None, streak: int = 0):
    stats = get_stats()
    stats.current_streak = streak
    stats.longest_streak = streak
    stats.last_read_date = last_read
    save_stats(stats)


def test_first_session_starts_streak(tmp_db):
    reset_stats()
    stats = update_streak(date(2026, 3, 1))
    assert stats.current_streak == 1
    assert stats.last_read_date == date(2026, 3, 1)


def test_consecutive_day_extends_streak(tmp_db):
    reset_stats(last_read=date(2026, 3, 1), streak=1)
    stats = update_streak(date(2026, 3, 2))
    assert stats.current_streak == 2


def test_same_day_does_not_double_count(tmp_db):
    reset_stats(last_read=date(2026, 3, 1), streak=3)
    stats = update_streak(date(2026, 3, 1))
    assert stats.current_streak == 3


def test_gap_resets_streak(tmp_db):
    reset_stats(last_read=date(2026, 3, 1), streak=5)
    stats = update_streak(date(2026, 3, 4))
    assert stats.current_streak == 1


def test_longest_streak_tracked(tmp_db):
    reset_stats(last_read=date(2026, 3, 1), streak=10)
    stats = update_streak(date(2026, 3, 2))
    assert stats.longest_streak == 11
