"""
Abstract base reader. All format readers implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chapter:
    index: int
    label: str           # e.g. "Chapter 3 — The Call"
    href: str            # relative path within the book package
    word_count: int = 0
    start_location: str = ""   # populated after extraction (abs file path or page num)
    end_location: str = ""


class BaseReader(ABC):

    @abstractmethod
    def get_chapters(self) -> list[Chapter]:
        """Return ordered chapter list."""

    @abstractmethod
    def get_chapter_html(self, chapter: Chapter) -> str:
        """Return a self-contained HTML string for a single chapter."""

    @abstractmethod
    def extract(self) -> Path:
        """
        Extract/prepare book content so it can be served via file:// URLs.
        Returns the root directory of extracted content.
        Idempotent — safe to call multiple times.
        """

    @abstractmethod
    def estimate_word_count(self) -> int:
        """Return estimated total word count."""

    def estimate_page_count(self, words_per_page: int = 275) -> int:
        return max(1, self.estimate_word_count() // words_per_page)
