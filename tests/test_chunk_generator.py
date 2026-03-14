"""Tests for chunk_generator.py"""
import pytest
from datetime import date

from readwise.core.chunk_generator import ChapterInfo, generate_chunks
from readwise.db.models.reading_plan import ReadingPlan


def make_plan(strategy: str, chunk_size: int) -> ReadingPlan:
    return ReadingPlan(
        id="plan-1",
        book_id="book-1",
        chunk_strategy=strategy,
        chunk_size=chunk_size,
        start_date=date(2026, 3, 1),
        target_end_date=date(2026, 4, 1),
        daily_goal_time=None,
        created_at="2026-03-01T00:00:00",
    )


CHAPTERS = [
    ChapterInfo(1, "Chapter 1", "1", "20", word_count=2000),
    ChapterInfo(2, "Chapter 2", "21", "40", word_count=2500),
    ChapterInfo(3, "Chapter 3", "41", "60", word_count=1800),
    ChapterInfo(4, "Chapter 4", "61", "80", word_count=3000),
]


def test_by_pages_basic():
    plan = make_plan("PAGES", 20)
    chunks = generate_chunks(plan, total_pages=60)
    assert len(chunks) == 3
    assert chunks[0].label == "Pages 1–20"
    assert chunks[1].label == "Pages 21–40"
    assert chunks[2].label == "Pages 41–60"


def test_by_pages_partial_last():
    plan = make_plan("PAGES", 20)
    chunks = generate_chunks(plan, total_pages=45)
    assert len(chunks) == 3
    assert chunks[2].label == "Pages 41–45"


def test_by_pages_scheduled_dates():
    plan = make_plan("PAGES", 10)
    chunks = generate_chunks(plan, total_pages=30)
    assert chunks[0].scheduled_date == date(2026, 3, 1)
    assert chunks[1].scheduled_date == date(2026, 3, 2)
    assert chunks[2].scheduled_date == date(2026, 3, 3)


def test_by_chapters_one_per_day():
    plan = make_plan("CHAPTERS", 1)
    chunks = generate_chunks(plan, chapters=CHAPTERS)
    assert len(chunks) == 4
    assert chunks[0].label == "Chapter 1"
    assert chunks[0].scheduled_date == date(2026, 3, 1)


def test_by_chapters_two_per_day():
    plan = make_plan("CHAPTERS", 2)
    chunks = generate_chunks(plan, chapters=CHAPTERS)
    assert len(chunks) == 2
    assert "Chapter 1" in chunks[0].label
    assert "Chapter 2" in chunks[0].label


def test_by_time_groups_chapters():
    plan = make_plan("TIME", 10)  # 10 minutes @ 250 wpm = 2500 words
    chunks = generate_chunks(plan, chapters=CHAPTERS, words_per_minute=250)
    # Ch1 (2000) fits; Ch2 (2500) alone fills next chunk; etc.
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.plan_id == "plan-1"


def test_no_pages_returns_empty():
    plan = make_plan("PAGES", 20)
    assert generate_chunks(plan, total_pages=0) == []


def test_no_chapters_returns_empty():
    plan = make_plan("CHAPTERS", 1)
    assert generate_chunks(plan, chapters=[]) == []
