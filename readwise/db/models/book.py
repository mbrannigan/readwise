"""
Book model: dataclass + DB queries.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date

from readwise.db.database import Database


@dataclass
class BookFormat:
    format: str          # "EPUB" | "PDF" | "MOBI"
    path: str            # absolute path to file


@dataclass
class Book:
    id: str
    calibre_id: str
    title: str
    author: str
    cover_path: str
    available_formats: list[BookFormat]
    active_format: str
    total_pages: int
    total_words: int
    total_chapters: int
    added_date: date
    status: str                          # NOT_STARTED | IN_PROGRESS | COMPLETE
    # Extended Calibre metadata
    publisher: str = ""
    series: str = ""
    series_index: float = 0.0
    description: str = ""
    tags: list[str] = field(default_factory=list)
    rating: float = 0.0                  # 0–10 (Calibre scale)
    pub_date: str = ""
    language: str = ""

    @property
    def active_file_path(self) -> str | None:
        for f in self.available_formats:
            if f.format == self.active_format:
                return f.path
        return self.available_formats[0].path if self.available_formats else None

    @property
    def star_rating(self) -> str:
        """Return a 0–5 star string from Calibre's 0–10 rating."""
        stars = round(self.rating / 2)
        return "★" * stars + "☆" * (5 - stars) if self.rating else ""

    @classmethod
    def _from_row(cls, row) -> "Book":
        formats = [
            BookFormat(**f) for f in json.loads(row["available_formats"])
        ]
        keys = row.keys()
        return cls(
            id=row["id"],
            calibre_id=row["calibre_id"],
            title=row["title"],
            author=row["author"],
            cover_path=row["cover_path"],
            available_formats=formats,
            active_format=row["active_format"],
            total_pages=row["total_pages"],
            total_words=row["total_words"],
            total_chapters=row["total_chapters"],
            added_date=date.fromisoformat(row["added_date"]),
            status=row["status"],
            publisher=row["publisher"] if "publisher" in keys else "",
            series=row["series"] if "series" in keys else "",
            series_index=row["series_index"] if "series_index" in keys else 0.0,
            description=row["description"] if "description" in keys else "",
            tags=json.loads(row["tags"]) if "tags" in keys else [],
            rating=row["rating"] if "rating" in keys else 0.0,
            pub_date=row["pub_date"] if "pub_date" in keys else "",
            language=row["language"] if "language" in keys else "",
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_all_books() -> list[Book]:
    db = Database.get()
    rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    return [Book._from_row(r) for r in rows]


def get_book(book_id: str) -> Book | None:
    db = Database.get()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return Book._from_row(row) if row else None


def get_book_by_calibre_id(calibre_id: str) -> Book | None:
    db = Database.get()
    row = db.execute(
        "SELECT * FROM books WHERE calibre_id = ?", (calibre_id,)
    ).fetchone()
    return Book._from_row(row) if row else None


def upsert_book(book: Book) -> None:
    """Insert or update a book record (keyed on calibre_id)."""
    db = Database.get()
    formats_json = json.dumps([
        {"format": f.format, "path": f.path} for f in book.available_formats
    ])
    db.execute("""
        INSERT INTO books
            (id, calibre_id, title, author, cover_path, available_formats,
             active_format, total_pages, total_words, total_chapters,
             added_date, status, publisher, series, series_index,
             description, tags, rating, pub_date, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(calibre_id) DO UPDATE SET
            title             = excluded.title,
            author            = excluded.author,
            cover_path        = excluded.cover_path,
            available_formats = excluded.available_formats,
            total_pages       = excluded.total_pages,
            total_words       = excluded.total_words,
            total_chapters    = excluded.total_chapters,
            publisher         = excluded.publisher,
            series            = excluded.series,
            series_index      = excluded.series_index,
            description       = excluded.description,
            tags              = excluded.tags,
            rating            = excluded.rating,
            pub_date          = excluded.pub_date,
            language          = excluded.language
    """, (
        book.id, book.calibre_id, book.title, book.author, book.cover_path,
        formats_json, book.active_format, book.total_pages, book.total_words,
        book.total_chapters, book.added_date.isoformat(), book.status,
        book.publisher, book.series, book.series_index, book.description,
        json.dumps(book.tags), book.rating, book.pub_date, book.language,
    ))
    db.commit()


def update_book_status(book_id: str, status: str) -> None:
    db = Database.get()
    db.execute("UPDATE books SET status = ? WHERE id = ?", (status, book_id))
    db.commit()


def update_active_format(book_id: str, fmt: str) -> None:
    db = Database.get()
    db.execute(
        "UPDATE books SET active_format = ? WHERE id = ?", (fmt, book_id)
    )
    db.commit()


def new_book_id() -> str:
    return str(uuid.uuid4())
