"""
BookDetailDialog: click a book card to see full metadata before reading.
Amazon/Goodreads-style layout: cover left, details right, action buttons bottom.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from readwise.db.models.book import Book
from readwise.db.models.reading_plan import get_plan_for_book, get_chunks_for_plan


class BookDetailDialog(QDialog):
    read_requested = Signal(str)   # emits book_id

    COVER_W = 220
    COVER_H = 320

    def __init__(self, book: Book, parent=None):
        super().__init__(parent)
        self.book = book
        self.setWindowTitle(book.title)
        self.setMinimumSize(780, 500)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)

        # ── Left column: cover ──────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        cover_label = QLabel()
        cover_label.setFixedSize(self.COVER_W, self.COVER_H)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet("background: #2a2a2a; border-radius: 6px;")

        if self.book.cover_path and Path(self.book.cover_path).exists():
            pixmap = QPixmap(self.book.cover_path).scaled(
                self.COVER_W, self.COVER_H,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            cover_label.setPixmap(pixmap)
        else:
            cover_label.setText("No Cover")
            cover_label.setStyleSheet(
                "background: #333; color: #888; border-radius: 6px; font-size: 14px;"
            )

        left.addWidget(cover_label)

        # Format badges
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(6)
        for f in self.book.available_formats:
            badge = QLabel(f.format)
            badge.setStyleSheet(
                "background: #e7f5ff; color: #1864ab; border-radius: 4px;"
                " padding: 2px 8px; font-size: 11px; font-weight: bold;"
            )
            fmt_row.addWidget(badge)
        fmt_row.addStretch()
        left.addLayout(fmt_row)
        left.addStretch()

        root.addLayout(left)

        # ── Right column: metadata + actions ────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        # Title
        title_lbl = QLabel(self.book.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold;")
        right.addWidget(title_lbl)

        # Author
        author_lbl = QLabel(self.book.author)
        author_lbl.setStyleSheet("font-size: 15px; color: #555;")
        right.addWidget(author_lbl)

        # Series
        if self.book.series:
            idx = f" #{self.book.series_index:g}" if self.book.series_index else ""
            series_lbl = QLabel(f"{self.book.series}{idx}")
            series_lbl.setStyleSheet("font-size: 13px; color: #1971c2; font-style: italic;")
            right.addWidget(series_lbl)

        # Rating
        if self.book.rating:
            rating_lbl = QLabel(f"{self.book.star_rating}  ({self.book.rating / 2:.1f}/5)")
            rating_lbl.setStyleSheet("font-size: 14px; color: #e67700;")
            right.addWidget(rating_lbl)

        right.addSpacing(4)

        # Metadata grid
        meta_pairs = [
            ("Publisher",  self.book.publisher),
            ("Published",  self.book.pub_date[:4] if self.book.pub_date else ""),
            ("Language",   self.book.language.upper() if self.book.language else ""),
            ("Status",     self.book.status.replace("_", " ").title()),
            ("Progress",   self._progress_text()),
        ]
        for label, value in meta_pairs:
            if not value:
                continue
            row = QHBoxLayout()
            key_lbl = QLabel(f"{label}:")
            key_lbl.setStyleSheet("color: #666; font-size: 12px;")
            key_lbl.setFixedWidth(80)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet("font-size: 12px;")
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            right.addLayout(row)

        # Tags
        if self.book.tags:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(6)
            for tag in self.book.tags[:8]:  # cap at 8 tags
                t = QLabel(tag)
                t.setStyleSheet(
                    "background: #d3f9d8; color: #2b8a3e; border-radius: 4px;"
                    " padding: 2px 8px; font-size: 11px;"
                )
                tags_row.addWidget(t)
            tags_row.addStretch()
            right.addLayout(tags_row)

        right.addSpacing(8)

        # Description (scrollable)
        if self.book.description:
            desc_scroll = QScrollArea()
            desc_scroll.setFrameShape(QScrollArea.NoFrame)
            desc_scroll.setWidgetResizable(True)
            desc_scroll.setMaximumHeight(160)

            desc_lbl = QLabel(self.book.description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 13px; color: #333; line-height: 1.5;")
            desc_lbl.setAlignment(Qt.AlignTop)
            desc_scroll.setWidget(desc_lbl)
            right.addWidget(desc_scroll)

        right.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)

        read_btn = QPushButton(
            "Continue Reading" if self.book.status == "IN_PROGRESS" else "Start Reading"
        )
        read_btn.setDefault(True)
        read_btn.setStyleSheet(
            "QPushButton { background: #4dabf7; color: #000; font-weight: bold;"
            " padding: 8px 20px; border-radius: 6px; }"
            "QPushButton:hover { background: #74c0fc; }"
        )
        read_btn.clicked.connect(self._on_read)
        btn_row.addWidget(read_btn)

        right.addLayout(btn_row)
        root.addLayout(right)

    def _progress_text(self) -> str:
        plan = get_plan_for_book(self.book.id)
        if not plan:
            return ""
        chunks = get_chunks_for_plan(plan.id)
        if not chunks:
            return ""
        done = sum(1 for c in chunks if c.is_complete)
        return f"{done} / {len(chunks)} chunks complete"

    def _on_read(self) -> None:
        self.accept()
        self.read_requested.emit(self.book.id)
