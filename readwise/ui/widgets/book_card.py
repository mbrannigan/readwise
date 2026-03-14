"""
BookCard widget: cover art, title, author, progress bar, status badge.

Interactions:
  - Click cover        → BookDetailDialog (summary / metadata)
  - Click title        → open reader
  - Click author       → filter library by this author
  - Click series line  → open series drill-down
  - Click status badge → open reader
  - Shift+click status → reset progress (with confirmation)
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
)

from readwise.db.models.book import Book, update_book_status
from readwise.db.models.reading_plan import (
    delete_plan_for_book,
    get_chunks_for_plan,
    get_plan_for_book,
)

STATUS_COLORS = {
    "NOT_STARTED": "#aaa",
    "IN_PROGRESS": "#4dabf7",
    "COMPLETE": "#51cf66",
}


class _CoverLabel(QLabel):
    """Cover image — click opens the detail dialog."""
    clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _HoverArea(QFrame):
    """Container that highlights on hover; individual children handle clicks."""

    def enterEvent(self, event: QEnterEvent) -> None:
        self.setStyleSheet("background: #e8f4ff; border-radius: 0 0 4px 4px;")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet("")
        super().leaveEvent(event)


class BookCard(QFrame):
    open_requested = Signal(str)   # emits book_id
    progress_reset = Signal(str)   # emits book_id — library should refresh
    series_clicked = Signal(str)   # emits series name
    author_clicked = Signal(str)   # emits author name

    CARD_WIDTH = 180
    COVER_HEIGHT = 240
    CARD_HEIGHT = 375   # fixed so all cards align in the grid

    def __init__(self, book: Book, total_in_series: int = 0, parent=None):
        super().__init__(parent)
        self.book = book
        self._total_in_series = total_in_series
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setFrameShape(QFrame.StyledPanel)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(0)

        # ── Cover (click → detail dialog) ───────────────────────────
        self._cover = _CoverLabel()
        self._cover.setFixedSize(self.CARD_WIDTH - 16, self.COVER_HEIGHT)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setStyleSheet("background: #2a2a2a; border-radius: 4px;")
        self._cover.setCursor(Qt.PointingHandCursor)
        self._cover.clicked.connect(self._open_detail)

        if self.book.cover_path and Path(self.book.cover_path).exists():
            pixmap = QPixmap(self.book.cover_path).scaled(
                self.CARD_WIDTH - 16, self.COVER_HEIGHT,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            self._cover.setPixmap(pixmap)
        else:
            self._cover.setText("No Cover")
            self._cover.setStyleSheet(
                "background: #333; color: #888; border-radius: 4px;"
            )

        layout.addWidget(self._cover)

        # ── Info area ────────────────────────────────────────────────
        area = _HoverArea()
        from PySide6.QtWidgets import QHBoxLayout
        ra_layout = QVBoxLayout(area)
        ra_layout.setContentsMargins(0, 6, 0, 8)
        ra_layout.setSpacing(4)

        # Title → open reader (2-line cap)
        title_label = QLabel(self.book.title)
        title_label.setWordWrap(True)
        title_label.setFixedWidth(self.CARD_WIDTH - 16)
        title_label.setFixedHeight(38)   # ~2 lines at 12px bold
        title_label.setCursor(Qt.PointingHandCursor)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        title_label.mousePressEvent = self._title_clicked
        ra_layout.addWidget(title_label)

        # Author → filter by author (1 line, elided)
        author_text = self._elide(self.book.author, self.CARD_WIDTH - 16, 11)
        author_label = QLabel(author_text)
        author_label.setFixedWidth(self.CARD_WIDTH - 16)
        author_label.setCursor(Qt.PointingHandCursor)
        author_label.setStyleSheet(
            "color: #888; font-size: 11px; text-decoration: underline;"
        )
        author_label.mousePressEvent = self._author_label_clicked
        ra_layout.addWidget(author_label)

        # Series → drill-down (1 line, elided)
        if self.book.series:
            idx_str = (
                f"{self.book.series_index:g}"
                if self.book.series_index is not None else "?"
            )
            series_text = f"{self.book.series} ({idx_str} of {self._total_in_series})"
            series_text = self._elide(series_text, self.CARD_WIDTH - 16, 10)
            series_label = QLabel(series_text)
            series_label.setFixedWidth(self.CARD_WIDTH - 16)
            series_label.setCursor(Qt.PointingHandCursor)
            series_label.setStyleSheet(
                "color: #4dabf7; font-size: 10px; text-decoration: underline;"
            )
            series_label.mousePressEvent = self._series_label_clicked
            ra_layout.addWidget(series_label)

        # Progress bar / percentage (controlled by settings)
        from readwise.config.settings import Settings
        from PySide6.QtWidgets import QHBoxLayout as _QHBoxLayout
        progress = self._compute_progress()
        style = Settings.get().get_value("card_progress_style", "bar")

        if style in ("bar", "bar_pct"):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(progress)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            if style == "bar_pct":
                pct_row = _QHBoxLayout()
                pct_row.setContentsMargins(0, 0, 0, 0)
                pct_row.addWidget(bar)
                pct_lbl = QLabel(f"{progress}%")
                pct_lbl.setStyleSheet("color: #888; font-size: 10px;")
                pct_row.addWidget(pct_lbl)
                ra_layout.addLayout(pct_row)
            else:
                ra_layout.addWidget(bar)
        else:  # "pct"
            pct_lbl = QLabel(f"{progress}%")
            pct_lbl.setStyleSheet("color: #888; font-size: 11px;")
            ra_layout.addWidget(pct_lbl)

        # Bottom row: status badge + year
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(4)

        color = STATUS_COLORS.get(self.book.status, "#aaa")
        status_label = QLabel(self.book.status.replace("_", " ").title())
        status_label.setCursor(Qt.PointingHandCursor)
        status_label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: bold;"
            f"text-decoration: underline;"
        )
        status_label.setToolTip("Click to read · Shift+click to reset progress")
        status_label.mousePressEvent = self._status_clicked
        bottom_row.addWidget(status_label)

        if self.book.pub_date:
            year_label = QLabel(self.book.pub_date[:4])
            year_label.setStyleSheet("color: #bbb; font-size: 10px;")
            bottom_row.addStretch()
            bottom_row.addWidget(year_label)

        ra_layout.addLayout(bottom_row)
        layout.addWidget(area)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _elide(text: str, max_px: int, font_px: int) -> str:
        """Return text elided with '…' to fit within max_px at the given font size."""
        from PySide6.QtGui import QFont, QFontMetrics
        f = QFont()
        f.setPixelSize(font_px)
        fm = QFontMetrics(f)
        return fm.elidedText(text, Qt.ElideRight, max_px)

    # ------------------------------------------------------------------
    # Click handlers
    # ------------------------------------------------------------------

    def _title_clicked(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.open_requested.emit(self.book.id)

    def _author_label_clicked(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.author_clicked.emit(self.book.author)

    def _series_label_clicked(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.series_clicked.emit(self.book.series)

    def _status_clicked(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        if event.modifiers() & Qt.ShiftModifier:
            self._confirm_reset()
        else:
            self.open_requested.emit(self.book.id)

    # ------------------------------------------------------------------

    def _confirm_reset(self) -> None:
        has_plan = get_plan_for_book(self.book.id) is not None
        if not has_plan:
            return
        reply = QMessageBox.warning(
            self,
            "Reset Progress",
            f"This will delete all reading progress and the reading plan for "
            f"\"{self.book.title}\".\n\nYou'll be asked to set up a new plan "
            f"when you reopen the book.\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Ok:
            delete_plan_for_book(self.book.id)
            update_book_status(self.book.id, "NOT_STARTED")
            self.progress_reset.emit(self.book.id)

    def _open_detail(self) -> None:
        from readwise.ui.dialogs.book_detail_dialog import BookDetailDialog
        dialog = BookDetailDialog(self.book, parent=self)
        dialog.read_requested.connect(self.open_requested)
        dialog.exec()

    def _compute_progress(self) -> int:
        plan = get_plan_for_book(self.book.id)
        if plan is None:
            return 0
        chunks = get_chunks_for_plan(plan.id)
        if not chunks:
            return 0
        done = sum(1 for c in chunks if c.is_complete)
        return int(done / len(chunks) * 100)
