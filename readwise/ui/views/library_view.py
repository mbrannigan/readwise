"""
Library view: grid of book cards sourced from the Calibre scanner.
Supports sort (Title / Author / Series) and a Series grouped view with drill-down.
"""
from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from readwise.db.models.book import Book, get_all_books
from readwise.ui.widgets.book_card import BookCard
from readwise.ui.widgets.series_card import SeriesCard

_COLS = 4

# Sort keys ---------------------------------------------------------------
_SORT_TITLE = "title"
_SORT_AUTHOR = "author"
_SORT_SERIES = "series"
_SORT_DATE = "date"


def _sort_key(sort: str):
    if sort == _SORT_AUTHOR:
        return lambda b: (b.author.lower(), b.title.lower())
    if sort == _SORT_SERIES:
        return lambda b: (b.series.lower() if b.series else "zzz", b.series_index or 0, b.title.lower())
    if sort == _SORT_DATE:
        return lambda b: (b.pub_date or "0000", b.title.lower())
    return lambda b: b.title.lower()   # default: title


_SEARCH_FIELDS = ("author:", "series:", "tag:", "publisher:")


def _parse_search(query: str) -> tuple[str, str]:
    """Return (field, value) from a search query.

    Recognises prefixes like 'author:', 'series:', 'tag:', 'publisher:'.
    Plain text defaults to title search.
    """
    q = query.strip()
    for prefix in _SEARCH_FIELDS:
        if q.lower().startswith(prefix):
            return prefix[:-1], q[len(prefix):].strip().lower()
    return "title", q.lower()


def _main_book_count(books: list[Book]) -> int:
    """Return the count of 'main' books in a series (whole-numbered series_index).

    e.g. Stormlight 1, 2, 2.5, 3, 3.5, 4, 5 → 5 (not 7).
    Falls back to total book count if none have whole indices.
    """
    whole = [
        b for b in books
        if b.series_index is not None and b.series_index == int(b.series_index)
    ]
    return len(whole) if whole else len(books)


class LibraryView(QWidget):
    open_book = Signal(str)  # emits book_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort: str = _SORT_TITLE
        self._sort_asc: bool = True
        self._series_view: bool = False
        self._series_filter: str | None = None
        self._status_filter: str | None = None
        self._author_filter: str | None = None
        self._search_query: str = ""
        self._series_counts: dict[str, int] = {}
        self._cols: int = 4
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self._on_resize_settled)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._render)
        self._setup_ui()
        self._update_sort_labels()
        self.refresh()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── Header bar ────────────────────────────────────────────────
        header = QHBoxLayout()
        self.title_label = QLabel("My Library")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        header.addWidget(self.title_label)
        header.addStretch()

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search…  (author:, series:, tag:)")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setFixedWidth(280)
        self._search_box.setStyleSheet("font-size: 13px; padding: 4px 8px;")
        self._search_box.textChanged.connect(self._on_search_changed)
        header.addWidget(self._search_box)
        layout.addLayout(header)

        # ── Toolbar: sort + view mode ─────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet("color: #666; font-size: 12px;")
        toolbar.addWidget(sort_label)

        self._sort_group = QButtonGroup(self)
        self._sort_group.setExclusive(True)
        for label, key in [("Title", _SORT_TITLE), ("Author", _SORT_AUTHOR), ("Series", _SORT_SERIES), ("Pub Date", _SORT_DATE)]:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setChecked(key == self._sort)
            btn.setProperty("sort_key", key)
            btn.clicked.connect(self._on_sort_clicked)
            btn.setStyleSheet(
                "QToolButton { border: 1px solid #ccc; border-radius: 3px; padding: 3px 10px; font-size: 12px; }"
                "QToolButton:checked { background: #4dabf7; color: white; border-color: #4dabf7; }"
            )
            self._sort_group.addButton(btn)
            toolbar.addWidget(btn)

        toolbar.addSpacing(16)

        view_label = QLabel("View:")
        view_label.setStyleSheet("color: #666; font-size: 12px;")
        toolbar.addWidget(view_label)

        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        for label, series_mode in [("All Books", False), ("By Series", True)]:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setChecked(series_mode == self._series_view)
            btn.setProperty("series_mode", series_mode)
            btn.clicked.connect(self._on_view_clicked)
            btn.setStyleSheet(
                "QToolButton { border: 1px solid #ccc; border-radius: 3px; padding: 3px 10px; font-size: 12px; }"
                "QToolButton:checked { background: #4dabf7; color: white; border-color: #4dabf7; }"
            )
            self._view_group.addButton(btn)
            toolbar.addWidget(btn)

        toolbar.addSpacing(16)

        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: #666; font-size: 12px;")
        toolbar.addWidget(filter_label)

        self.reading_filter_btn = QToolButton()
        self.reading_filter_btn.setText("Currently Reading")
        self.reading_filter_btn.setCheckable(True)
        self.reading_filter_btn.setChecked(False)
        self.reading_filter_btn.clicked.connect(self._on_filter_clicked)
        self.reading_filter_btn.setStyleSheet(
            "QToolButton { border: 1px solid #ccc; border-radius: 3px; padding: 3px 10px; font-size: 12px; }"
            "QToolButton:checked { background: #51cf66; color: white; border-color: #51cf66; }"
        )
        toolbar.addWidget(self.reading_filter_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ── Author filter bar (shown when an author filter is active) ─
        self._author_bar = QWidget()
        author_bar_layout = QHBoxLayout(self._author_bar)
        author_bar_layout.setContentsMargins(0, 0, 0, 0)
        author_bar_layout.setSpacing(8)
        self._author_filter_label = QLabel()
        self._author_filter_label.setStyleSheet("color: #444; font-size: 12px;")
        author_clear_btn = QPushButton("× Clear")
        author_clear_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        author_clear_btn.clicked.connect(self._clear_author_filter)
        author_bar_layout.addWidget(self._author_filter_label)
        author_bar_layout.addWidget(author_clear_btn)
        author_bar_layout.addStretch()
        self._author_bar.setVisible(False)
        layout.addWidget(self._author_bar)

        # ── Back button (shown only when drilled into a series) ───────
        self.back_bar = QWidget()
        back_layout = QHBoxLayout(self.back_bar)
        back_layout.setContentsMargins(0, 0, 0, 0)
        self.back_btn = QPushButton("← All Books")
        self.back_btn.setStyleSheet("font-size: 13px; padding: 4px 12px;")
        self.back_btn.clicked.connect(self._on_back)
        back_layout.addWidget(self.back_btn)
        back_layout.addStretch()
        self.back_bar.setVisible(False)
        layout.addWidget(self.back_bar)

        # ── Book grid ─────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(16)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

        # ── Empty state ────────────────────────────────────────────────
        self.empty_label = QLabel(
            'No books yet.\nClick "Set / Scan Library" to point to your Calibre library.'
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #888; font-size: 15px;")
        layout.addWidget(self.empty_label)

    # ------------------------------------------------------------------
    # Refresh / render
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._render()

    def go_home(self) -> None:
        """Reset all filters/drill-downs and return to the top-level grid."""
        self._series_filter = None
        self._series_view = False
        self._author_filter = None
        self._status_filter = None
        self._search_query = ""
        self.back_bar.setVisible(False)
        self._author_bar.setVisible(False)
        self.reading_filter_btn.setChecked(False)
        self._search_box.blockSignals(True)
        self._search_box.clear()
        self._search_box.blockSignals(False)
        self.title_label.setText("My Library")
        for btn in self._view_group.buttons():
            btn.setChecked(not btn.property("series_mode"))
        self._render()

    def _render(self) -> None:
        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Compute series counts from the FULL library so "X of N" is always
        # correct even when a status or author filter is active.
        all_books_full = get_all_books()
        series_groups: dict[str, list[Book]] = defaultdict(list)
        for b in all_books_full:
            if b.series:
                series_groups[b.series].append(b)
        self._series_counts = {
            name: _main_book_count(books)
            for name, books in series_groups.items()
        }

        all_books = sorted(all_books_full, key=_sort_key(self._sort), reverse=not self._sort_asc)
        if self._status_filter:
            all_books = [b for b in all_books if b.status == self._status_filter]
        if self._author_filter:
            all_books = [b for b in all_books if b.author == self._author_filter]
        if self._search_query:
            field, value = _parse_search(self._search_query)
            if value:
                if field == "author":
                    all_books = [b for b in all_books if value in b.author.lower()]
                elif field == "series":
                    all_books = [b for b in all_books if value in (b.series or "").lower()]
                elif field == "tag":
                    all_books = [b for b in all_books if any(value in t.lower() for t in b.tags)]
                elif field == "publisher":
                    all_books = [b for b in all_books if value in (b.publisher or "").lower()]
                else:
                    all_books = [b for b in all_books if value in b.title.lower()]

        has_books = bool(all_books)
        self.empty_label.setVisible(not has_books)
        self.scroll.setVisible(has_books)

        if not has_books:
            return

        if self._series_filter is not None:
            self._render_series_drill(all_books)
        elif self._series_view:
            self._render_series_grouped(all_books)
        else:
            self._render_flat(all_books)

    def _render_flat(self, books: list[Book]) -> None:
        for i, book in enumerate(books):
            self.grid.addWidget(self._make_book_card(book), i // self._cols, i % self._cols)

    def _render_series_grouped(self, books: list[Book]) -> None:
        series_map: dict[str, list[Book]] = defaultdict(list)
        standalone: list[Book] = []
        for book in books:
            if book.series:
                series_map[book.series].append(book)
            else:
                standalone.append(book)

        items: list[QWidget] = []

        for series_name in sorted(series_map, key=str.lower):
            card = SeriesCard(series_name, series_map[series_name])
            card.series_selected.connect(self._on_series_selected)
            items.append(card)

        for book in standalone:
            items.append(self._make_book_card(book))

        for i, widget in enumerate(items):
            self.grid.addWidget(widget, i // self._cols, i % self._cols)

    def _render_series_drill(self, books: list[Book]) -> None:
        filtered = sorted(
            (b for b in books if b.series == self._series_filter),
            key=lambda b: (b.series_index or 0, b.title.lower()),
        )
        for i, book in enumerate(filtered):
            self.grid.addWidget(self._make_book_card(book), i // self._cols, i % self._cols)

    def _make_book_card(self, book: Book) -> BookCard:
        total = self._series_counts.get(book.series, 0) if book.series else 0
        card = BookCard(book, total_in_series=total)
        card.open_requested.connect(self._on_open_book)
        card.progress_reset.connect(lambda _: self.refresh())
        card.series_clicked.connect(self._on_series_selected)
        card.author_clicked.connect(self._on_author_filter)
        return card

    # ------------------------------------------------------------------
    # Toolbar handlers
    # ------------------------------------------------------------------

    def _on_sort_clicked(self) -> None:
        btn = self.sender()
        key = btn.property("sort_key")
        if key == self._sort:
            self._sort_asc = not self._sort_asc
        else:
            self._sort = key
        self._update_sort_labels()
        self._render()

    def _update_sort_labels(self) -> None:
        arrow = " ↑" if self._sort_asc else " ↓"
        for btn in self._sort_group.buttons():
            key = btn.property("sort_key")
            base = {_SORT_TITLE: "Title", _SORT_AUTHOR: "Author",
                    _SORT_SERIES: "Series", _SORT_DATE: "Pub Date"}[key]
            btn.setText(base + arrow if key == self._sort else base)

    def _on_filter_clicked(self) -> None:
        self._status_filter = "IN_PROGRESS" if self.reading_filter_btn.isChecked() else None
        self._render()

    def _on_view_clicked(self) -> None:
        btn = self.sender()
        self._series_view = btn.property("series_mode")
        self._series_filter = None
        if self._series_view:
            self.back_btn.setText("← All Books")
            self.back_bar.setVisible(True)
            self.title_label.setText("My Library")
        else:
            self.back_bar.setVisible(False)
            self.title_label.setText("My Library")
        self._render()

    def _on_series_selected(self, series_name: str) -> None:
        self._series_filter = series_name
        self.back_btn.setText("← All Series")
        self.back_bar.setVisible(True)
        self.title_label.setText(series_name)
        self._render()

    def _on_back(self) -> None:
        if self._series_filter is not None:
            self._series_filter = None
            self.back_btn.setText("← All Books")
            self.title_label.setText("My Library")
        else:
            self._series_view = False
            self.back_bar.setVisible(False)
            self.title_label.setText("My Library")
            for btn in self._view_group.buttons():
                btn.setChecked(not btn.property("series_mode"))
        self._render()

    def _on_author_filter(self, author: str) -> None:
        self._author_filter = author
        self._author_filter_label.setText(f"Author: {author}")
        self._author_bar.setVisible(True)
        self._render()

    def _clear_author_filter(self) -> None:
        self._author_filter = None
        self._author_bar.setVisible(False)
        self._render()

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text
        self._search_timer.start()

    # ------------------------------------------------------------------
    # Other handlers
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()

    def _on_resize_settled(self) -> None:
        from readwise.ui.widgets.book_card import BookCard
        available = self.scroll.width() - 32
        new_cols = max(1, available // (BookCard.CARD_WIDTH + self.grid.spacing()))
        if new_cols != self._cols:
            self._cols = new_cols
            self._render()

    def _on_open_book(self, book_id: str) -> None:
        main = self.window()
        if hasattr(main, "open_reader"):
            main.open_reader(book_id)
