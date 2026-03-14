"""
BookSetupDialog: first-open wizard for a book.
Lets the user choose chunking strategy, size, and start date,
then previews the resulting schedule before confirming.
"""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from readwise.core.chunk_generator import ChapterInfo, generate_chunks
from readwise.db.models.book import Book
from readwise.db.models.reading_plan import (
    ReadingPlan,
    insert_plan,
    insert_chunks,
    new_plan_id,
)
from readwise.readers.base_reader import Chapter


STRATEGIES = [
    ("By Chapters", "CHAPTERS"),
    ("By Pages",    "PAGES"),
    ("By Time (minutes/day)", "TIME"),
]

STRATEGY_HINTS = {
    "CHAPTERS": "chapters per day",
    "PAGES":    "pages per day",
    "TIME":     "minutes per day",
}


class BookSetupDialog(QDialog):

    def __init__(self, book: Book, chapters: list[Chapter], total_pages: int, parent=None):
        super().__init__(parent)
        self.book = book
        self.chapters = chapters
        self.total_pages = total_pages
        self.plan: ReadingPlan | None = None

        self.setWindowTitle(f"Set Up Reading Plan — {book.title}")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._setup_ui()
        self._update_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel(f"<b>{self.book.title}</b>")
        title.setStyleSheet("font-size: 16px;")
        layout.addWidget(title)

        sub = QLabel(f"{len(self.chapters)} chapters detected · {self.total_pages} pages estimated")
        sub.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(sub)

        layout.addSpacing(8)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        # Strategy selector
        self.strategy_combo = QComboBox()
        for label, _ in STRATEGIES:
            self.strategy_combo.addItem(label)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        form.addRow("Chunking strategy:", self.strategy_combo)

        # Chunk size
        size_row = QHBoxLayout()
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 500)
        self.size_spin.setValue(1)
        self.size_spin.valueChanged.connect(self._update_preview)
        self.size_unit_label = QLabel("chapters per day")
        size_row.addWidget(self.size_spin)
        size_row.addWidget(self.size_unit_label)
        size_row.addStretch()
        form.addRow("Daily goal:", size_row)

        layout.addLayout(form)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "background: #f0f4ff; border-radius: 6px; padding: 12px;"
            " font-size: 13px; color: #333;"
        )
        layout.addWidget(self.preview_label)

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Reading")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_strategy_changed(self) -> None:
        _, code = STRATEGIES[self.strategy_combo.currentIndex()]
        self.size_unit_label.setText(STRATEGY_HINTS.get(code, ""))
        # Sensible defaults per strategy
        defaults = {"CHAPTERS": 1, "PAGES": 20, "TIME": 30}
        self.size_spin.setValue(defaults.get(code, 1))
        self._update_preview()

    def _update_preview(self) -> None:
        _, strategy = STRATEGIES[self.strategy_combo.currentIndex()]
        size = self.size_spin.value()

        chapter_infos = [
            ChapterInfo(
                index=ch.index,
                label=ch.label,
                start_location=ch.start_location,
                end_location=ch.end_location,
                word_count=ch.word_count,
            )
            for ch in self.chapters
        ]

        # Build a dummy plan to count chunks
        dummy_plan = ReadingPlan(
            id="preview",
            book_id=self.book.id,
            chunk_strategy=strategy,
            chunk_size=size,
            start_date=date.today(),
            target_end_date=date.today(),
            daily_goal_time=None,
            created_at="",
        )

        try:
            chunks = generate_chunks(
                dummy_plan,
                total_pages=self.total_pages,
                chapters=chapter_infos,
                words_per_minute=250,
            )
        except Exception:
            chunks = []

        if not chunks:
            self.preview_label.setText("Could not generate a preview with these settings.")
            return

        n = len(chunks)
        finish = date.today() + timedelta(days=n - 1)
        self.preview_label.setText(
            f"📅  <b>{n} reading sessions</b> — finishing around <b>{finish.strftime('%B %d, %Y')}</b><br>"
            f"First session: {chunks[0].label}"
        )

    def _on_accept(self) -> None:
        _, strategy = STRATEGIES[self.strategy_combo.currentIndex()]
        size = self.size_spin.value()

        chapter_infos = [
            ChapterInfo(
                index=ch.index,
                label=ch.label,
                start_location=ch.start_location,
                end_location=ch.end_location,
                word_count=ch.word_count,
            )
            for ch in self.chapters
        ]

        plan_id = new_plan_id()
        chunks = generate_chunks(
            ReadingPlan(
                id=plan_id,
                book_id=self.book.id,
                chunk_strategy=strategy,
                chunk_size=size,
                start_date=date.today(),
                target_end_date=date.today(),
                daily_goal_time=None,
                created_at=date.today().isoformat(),
            ),
            total_pages=self.total_pages,
            chapters=chapter_infos,
            words_per_minute=250,
        )

        finish = date.today() + timedelta(days=len(chunks) - 1)
        self.plan = ReadingPlan(
            id=plan_id,
            book_id=self.book.id,
            chunk_strategy=strategy,
            chunk_size=size,
            start_date=date.today(),
            target_end_date=finish,
            daily_goal_time=None,
            created_at=date.today().isoformat(),
        )

        insert_plan(self.plan)
        insert_chunks(chunks)
        self.accept()
