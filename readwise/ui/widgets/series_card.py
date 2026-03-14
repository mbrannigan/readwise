"""
SeriesCard: shows a series as a stacked-cover tile in the library grid.
Click opens a drill-down view of that series.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QEnterEvent, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout

from readwise.db.models.book import Book
from readwise.db.models.reading_plan import get_chunks_for_plan, get_plan_for_book


class SeriesCard(QFrame):
    series_selected = Signal(str)   # emits series name

    CARD_WIDTH   = 180
    COVER_HEIGHT = 240

    def __init__(self, series_name: str, books: list[Book], parent=None):
        super().__init__(parent)
        self.series_name = series_name
        self.books = sorted(books, key=lambda b: (b.series_index or 0, b.title))
        self.setFixedWidth(self.CARD_WIDTH)
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        cover_w = self.CARD_WIDTH - 16
        cover_h = self.COVER_HEIGHT

        cover_label = QLabel()
        cover_label.setFixedSize(cover_w, cover_h)
        cover_label.setAlignment(Qt.AlignCenter)

        pixmap = _make_stacked_pixmap(
            [b.cover_path for b in self.books[:3]],
            cover_w, cover_h,
        )
        cover_label.setPixmap(pixmap)
        layout.addWidget(cover_label)

        name_label = QLabel(self.series_name)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        name_label.setMaximumWidth(cover_w)
        layout.addWidget(name_label)

        count_label = QLabel(f"{len(self.books)} book{'s' if len(self.books) != 1 else ''}")
        count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(count_label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(self._series_progress())
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        layout.addWidget(bar)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.setStyleSheet("QFrame { background: #e8f4ff; }")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet("")
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.series_selected.emit(self.series_name)
        super().mousePressEvent(event)

    def _series_progress(self) -> int:
        total_chunks = done_chunks = 0
        for book in self.books:
            plan = get_plan_for_book(book.id)
            if not plan:
                continue
            chunks = get_chunks_for_plan(plan.id)
            total_chunks += len(chunks)
            done_chunks += sum(1 for c in chunks if c.is_complete)
        if not total_chunks:
            return 0
        return int(done_chunks / total_chunks * 100)


# ---------------------------------------------------------------------------
# Stacked-cover compositor
# ---------------------------------------------------------------------------

_SLOT_OFFSET = 7   # px each layer shifts right+down


def _make_stacked_pixmap(cover_paths: list[str | None], w: int, h: int) -> QPixmap:
    """
    Render up to 3 covers as a stacked deck.
    Back covers peek out from the bottom-right; front cover sits on top.
    """
    n = min(len(cover_paths), 3)
    total_offset = _SLOT_OFFSET * (n - 1)
    slot_w = w - total_offset
    slot_h = h - total_offset

    canvas = QPixmap(w, h)
    canvas.fill(QColor(0, 0, 0, 0))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw back → front
    for i, path in enumerate(reversed(cover_paths[:n])):
        layer = n - 1 - i          # 0 = back, n-1 = front
        ox = total_offset - layer * _SLOT_OFFSET
        oy = total_offset - layer * _SLOT_OFFSET

        cover_pixmap = _load_cover(path, slot_w, slot_h)

        # Drop shadow for depth
        painter.fillRect(ox + 3, oy + 3, slot_w, slot_h, QColor(0, 0, 0, 40))
        painter.drawPixmap(ox, oy, cover_pixmap)

    painter.end()
    return canvas


def _load_cover(path: str | None, w: int, h: int) -> QPixmap:
    if path and Path(path).exists():
        pix = QPixmap(path).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Pad to exact slot size so all layers align
        result = QPixmap(w, h)
        result.fill(QColor("#2a2a2a"))
        p = QPainter(result)
        x = (w - pix.width()) // 2
        y = (h - pix.height()) // 2
        p.drawPixmap(x, y, pix)
        p.end()
        return result

    # Placeholder
    pix = QPixmap(w, h)
    pix.fill(QColor("#333333"))
    p = QPainter(pix)
    p.setPen(QColor("#888888"))
    p.drawText(pix.rect(), Qt.AlignCenter, "No Cover")
    p.end()
    return pix
