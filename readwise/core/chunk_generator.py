"""
Chunk generator. Produces a list of Chunk records from a ReadingPlan
and the book's structure (chapter list, page count).

Each strategy produces chunks differently:
  PAGES    — fixed page ranges, one per day
  CHAPTERS — one or more chapters per day
  SECTIONS — sub-chapter sections per day (same logic as CHAPTERS, finer grain)
  TIME     — estimated by WPM, produces page ranges sized to fill chunk_size minutes
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from readwise.db.models.reading_plan import Chunk, ReadingPlan, new_chunk_id


@dataclass
class ChapterInfo:
    """Minimal structure info needed to generate chapter/section chunks."""
    index: int
    label: str           # e.g. "Chapter 3 — The Call"
    start_location: str  # page number or epub CFI
    end_location: str
    word_count: int = 0


def generate_chunks(
    plan: ReadingPlan,
    total_pages: int = 0,
    chapters: Sequence[ChapterInfo] = (),
    words_per_minute: int = 250,
) -> list[Chunk]:
    """
    Generate Chunk records for the given plan.

    Args:
        plan:              The ReadingPlan driving chunk generation.
        total_pages:       Total pages in the book (used for PAGES strategy).
        chapters:          Ordered list of chapter/section info (used for CHAPTERS/SECTIONS/TIME).
        words_per_minute:  User's reading speed (used for TIME strategy).

    Returns:
        List of Chunk objects ready to be inserted via insert_chunks().
    """
    match plan.chunk_strategy:
        case "PAGES":
            return _by_pages(plan, total_pages)
        case "CHAPTERS" | "SECTIONS":
            return _by_chapters(plan, chapters)
        case "TIME":
            return _by_time(plan, chapters, words_per_minute)
        case _:
            raise ValueError(f"Unknown chunk strategy: {plan.chunk_strategy}")


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

def _by_pages(plan: ReadingPlan, total_pages: int) -> list[Chunk]:
    if total_pages <= 0:
        return []

    chunks: list[Chunk] = []
    pages_per_chunk = plan.chunk_size
    current_page = 1
    sequence = 1
    current_date = plan.start_date

    while current_page <= total_pages:
        end_page = min(current_page + pages_per_chunk - 1, total_pages)
        chunks.append(Chunk(
            id=new_chunk_id(),
            plan_id=plan.id,
            book_id=plan.book_id,
            sequence=sequence,
            label=f"Pages {current_page}–{end_page}",
            start_location=str(current_page),
            end_location=str(end_page),
            scheduled_date=current_date,
            completed_date=None,
        ))
        current_page = end_page + 1
        sequence += 1
        current_date += timedelta(days=1)

    return chunks


def _by_chapters(plan: ReadingPlan, chapters: Sequence[ChapterInfo]) -> list[Chunk]:
    if not chapters:
        return []

    chunks: list[Chunk] = []
    chapters_per_chunk = plan.chunk_size
    sequence = 1
    current_date = plan.start_date

    # Group chapters into batches of chunk_size
    for i in range(0, len(chapters), chapters_per_chunk):
        batch = chapters[i : i + chapters_per_chunk]
        first, last = batch[0], batch[-1]

        if len(batch) == 1:
            label = first.label
        else:
            label = f"{first.label} – {last.label}"

        chunks.append(Chunk(
            id=new_chunk_id(),
            plan_id=plan.id,
            book_id=plan.book_id,
            sequence=sequence,
            label=label,
            start_location=first.start_location,
            end_location=last.end_location,
            scheduled_date=current_date,
            completed_date=None,
        ))
        sequence += 1
        current_date += timedelta(days=1)

    return chunks


def _by_time(
    plan: ReadingPlan,
    chapters: Sequence[ChapterInfo],
    words_per_minute: int,
) -> list[Chunk]:
    """
    Group chapters into chunks where total estimated reading time
    fits within plan.chunk_size minutes.
    """
    if not chapters or words_per_minute <= 0:
        return []

    target_words = plan.chunk_size * words_per_minute
    chunks: list[Chunk] = []
    sequence = 1
    current_date = plan.start_date
    batch: list[ChapterInfo] = []
    batch_words = 0

    for chapter in chapters:
        # If this single chapter exceeds target, it becomes its own chunk
        if batch and batch_words + chapter.word_count > target_words:
            chunks.append(_make_chunk(plan, batch, sequence, current_date))
            sequence += 1
            current_date += timedelta(days=1)
            batch = []
            batch_words = 0

        batch.append(chapter)
        batch_words += chapter.word_count

    # Flush remaining
    if batch:
        chunks.append(_make_chunk(plan, batch, sequence, current_date))

    return chunks


def _make_chunk(
    plan: ReadingPlan,
    batch: list[ChapterInfo],
    sequence: int,
    scheduled_date: date,
) -> Chunk:
    first, last = batch[0], batch[-1]
    label = first.label if len(batch) == 1 else f"{first.label} – {last.label}"
    return Chunk(
        id=new_chunk_id(),
        plan_id=plan.id,
        book_id=plan.book_id,
        sequence=sequence,
        label=label,
        start_location=first.start_location,
        end_location=last.end_location,
        scheduled_date=scheduled_date,
        completed_date=None,
    )
