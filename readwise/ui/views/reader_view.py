"""
ReaderView — full reading experience.

Flow:
  1. Load book + EPUB reader.
  2. If no reading plan → open BookSetupDialog.
  3. Open at saved position (or session 1).
  4. Session mode (default): nav bar shows sessions, loads session chapters.
     Full Book mode (toggle): nav bar shows individual chapters.
  5. End Session → finish_session(), emit session_ended.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtTextToSpeech import QTextToSpeech
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from readwise.core.session_manager import begin_session, finish_session
from readwise.db.models.book import get_book, update_book_status
from readwise.db.models.reading_plan import (
    get_chunks_for_plan,
    get_last_chunk_index,
    get_last_scroll_pct,
    get_plan_for_book,
    mark_chunk_complete,
    save_last_chunk_index,
    save_last_scroll_pct,
)
from readwise.readers.epub_reader import EpubReader
from readwise.ui.widgets.reader_panel import ReaderPanel


class ReaderView(QWidget):
    session_ended = Signal()

    def __init__(self, book_id: str, parent=None):
        super().__init__(parent)
        self.book_id = book_id
        self.book = get_book(book_id)
        self.session = None
        self._epub_reader: EpubReader | None = None
        self._all_chapters = []
        self._current_chunk_index = 0    # index into chunks list (session mode)
        self._current_chapter_index = 0  # index into _all_chapters (chapter mode)
        self._session_mode = True        # True = session nav, False = chapter nav
        self._current_scroll_pct = 0     # last known scroll position (0-100)

        self._tts: QTextToSpeech | None = None
        self._setup_ui()
        self._setup_tts()
        QTimer.singleShot(0, self._load_book)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setStyleSheet("background: #f0f0f0; border-bottom: 1px solid #ddd;")
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        self.mode_btn = QToolButton()
        self.mode_btn.setText("Full Book")
        self.mode_btn.setCheckable(True)
        self.mode_btn.setToolTip("Toggle between session view and full chapter-by-chapter view")
        self.mode_btn.clicked.connect(self._toggle_mode)
        top_layout.addWidget(self.mode_btn)

        end_btn = QPushButton("End Session")
        end_btn.setStyleSheet(
            "QPushButton { background: #e03131; color: white; border-radius: 4px;"
            " padding: 6px 14px; font-weight: bold; margin-left: 8px; }"
            "QPushButton:hover { background: #c92a2a; }"
        )
        end_btn.clicked.connect(self._end_session)
        top_layout.addWidget(end_btn)

        layout.addWidget(top_bar)

        # ── Navigation bar ────────────────────────────────────────────
        nav_bar = QWidget()
        nav_bar.setStyleSheet("background: #fafafa; border-bottom: 1px solid #eee;")
        nav_bar.setFixedHeight(44)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(8)

        self.prev_btn = QPushButton("←")
        self.prev_btn.setFixedWidth(36)
        self.prev_btn.clicked.connect(self._prev)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("→")
        self.next_btn.setFixedWidth(36)
        self.next_btn.clicked.connect(self._next)
        nav_layout.addWidget(self.next_btn)

        self.nav_combo = QComboBox()
        self.nav_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.nav_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.nav_combo.setStyleSheet("font-size: 13px;")
        # activated fires only on user interaction, never on programmatic setCurrentIndex
        self.nav_combo.activated.connect(self._on_combo_selected)
        nav_layout.addWidget(self.nav_combo)
        nav_layout.addStretch()

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(
            "color: #888; font-size: 12px; min-width: 90px; text-align: right;"
        )
        nav_layout.addWidget(self.progress_label)

        layout.addWidget(nav_bar)

        # ── TTS bar ───────────────────────────────────────────────────
        self.tts_bar = QWidget()
        self.tts_bar.setStyleSheet(
            "background: #f5f5f5; border-bottom: 1px solid #e0e0e0;"
        )
        self.tts_bar.setFixedHeight(40)
        tts_layout = QHBoxLayout(self.tts_bar)
        tts_layout.setContentsMargins(12, 0, 12, 0)
        tts_layout.setSpacing(8)

        tts_label = QLabel("🔊")
        tts_layout.addWidget(tts_label)

        self.tts_play_btn = QToolButton()
        self.tts_play_btn.setText("▶ Read")
        self.tts_play_btn.setCheckable(True)
        self.tts_play_btn.setToolTip("Read page aloud (Space)")
        self.tts_play_btn.clicked.connect(self._tts_play_pause)
        tts_layout.addWidget(self.tts_play_btn)

        tts_stop_btn = QToolButton()
        tts_stop_btn.setText("■")
        tts_stop_btn.setToolTip("Stop reading")
        tts_stop_btn.clicked.connect(self._tts_stop)
        tts_layout.addWidget(tts_stop_btn)

        tts_layout.addWidget(QLabel("Rate:"))
        self.tts_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_rate_slider.setRange(-10, 10)   # maps to -1.0 … 1.0
        self.tts_rate_slider.setValue(0)
        self.tts_rate_slider.setFixedWidth(100)
        self.tts_rate_slider.setToolTip("Speech rate (centre = normal)")
        self.tts_rate_slider.valueChanged.connect(self._tts_set_rate)
        tts_layout.addWidget(self.tts_rate_slider)

        tts_layout.addStretch()
        layout.addWidget(self.tts_bar)

        # ── Reader panel ─────────────────────────────────────────────
        self.reader_panel = ReaderPanel()
        self.reader_panel.scroll_changed.connect(self._on_scroll_changed)
        layout.addWidget(self.reader_panel, stretch=1)

        # ── Keyboard shortcuts ────────────────────────────────────────
        # WidgetWithChildrenShortcut fires when this widget or any child
        # (including the inner Chromium widget) has focus.
        for key, slot in [
            (Qt.Key.Key_Left, self._prev),
            (Qt.Key.Key_Right, self._next),
            (Qt.Key.Key_Up, self._scroll_up),
            (Qt.Key.Key_Down, self._scroll_down),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)

    # ------------------------------------------------------------------
    # Book loading
    # ------------------------------------------------------------------

    def _load_book(self) -> None:
        if not self.book:
            self._show_error("Book not found.")
            return

        self.title_label.setText(self.book.title)

        file_path = self.book.active_file_path
        if not file_path:
            self._show_error("No readable file found for this book.")
            return

        if self.book.active_format == "EPUB":
            self._load_epub(file_path)
        elif self.book.active_format == "PDF":
            self.reader_panel.show_message("PDF reader coming soon.")
        else:
            self.reader_panel.show_message(
                f"Format '{self.book.active_format}' is not yet supported."
            )

    def _load_epub(self, file_path: str) -> None:
        try:
            self._epub_reader = self.reader_panel.load_epub(file_path, self.book_id)
            self._all_chapters = self._epub_reader.get_chapters()
        except Exception as exc:
            self._show_error(f"Could not open EPUB:\n{exc}")
            return

        if not self._all_chapters:
            self._show_error("No chapters found in this EPUB.")
            return

        # Persist discovered counts back to DB
        from readwise.db.models.book import upsert_book
        self.book.total_chapters = len(self._all_chapters)
        self.book.total_words = self._epub_reader.estimate_word_count()
        self.book.total_pages = self._epub_reader.estimate_page_count()
        upsert_book(self.book)

        # Setup wizard if no plan exists
        plan = get_plan_for_book(self.book_id)
        if plan is None:
            if not self._run_setup_wizard():
                self.session_ended.emit()
                return

        self.session = begin_session(self.book_id)
        update_book_status(self.book_id, "IN_PROGRESS")
        self._current_chunk_index = self._get_starting_chunk_index()
        self._sync_chapter_to_chunk()

        # Restore scroll position from last session
        plan = get_plan_for_book(self.book_id)
        if plan:
            saved_pct = get_last_scroll_pct(plan.id)
            if saved_pct > 0:
                self.reader_panel.scroll_to_pct(saved_pct)
                self._current_scroll_pct = saved_pct

        self._render()

    def _run_setup_wizard(self) -> bool:
        from readwise.ui.dialogs.book_setup_dialog import BookSetupDialog
        dlg = BookSetupDialog(
            book=self.book,
            chapters=self._all_chapters,
            total_pages=self.book.total_pages,
            parent=self,
        )
        return dlg.exec() == QDialog.DialogCode.Accepted

    # ------------------------------------------------------------------
    # Rendering — dispatches to session or chapter mode
    # ------------------------------------------------------------------

    def _render(self) -> None:
        self._tts_stop()
        if self._session_mode:
            self._render_session()
        else:
            self._render_chapter()
        self._update_progress(0)

    def _render_session(self) -> None:
        plan = get_plan_for_book(self.book_id)
        if not plan:
            return
        chunks = get_chunks_for_plan(plan.id)
        if not chunks:
            self.reader_panel.show_message("No sessions found for this reading plan.")
            return

        idx = max(0, min(self._current_chunk_index, len(chunks) - 1))
        self._current_chunk_index = idx
        chunk = chunks[idx]

        # Rebuild combo if stale, otherwise just refresh labels (activated signal
        # won't fire from programmatic setCurrentIndex since we use .activated)
        if self.nav_combo.count() != len(chunks):
            self.nav_combo.clear()
            for c in chunks:
                self.nav_combo.addItem(self._session_label(c, len(chunks)))
        else:
            for i, c in enumerate(chunks):
                self.nav_combo.setItemText(i, self._session_label(c, len(chunks)))
        self.nav_combo.setCurrentIndex(idx)

        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(idx < len(chunks) - 1)

        chapters = self._chapters_for_chunk(chunk)
        if chapters:
            self.reader_panel.load_chapters(chapters)
        else:
            self.reader_panel.show_message(
                f"No chapter content found for session {chunk.sequence}."
            )

    def _render_chapter(self) -> None:
        if not self._all_chapters:
            return

        idx = max(0, min(self._current_chapter_index, len(self._all_chapters) - 1))
        self._current_chapter_index = idx
        ch = self._all_chapters[idx]

        if self.nav_combo.count() != len(self._all_chapters):
            self.nav_combo.clear()
            for c in self._all_chapters:
                self.nav_combo.addItem(c.label)
        self.nav_combo.setCurrentIndex(idx)

        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(idx < len(self._all_chapters) - 1)

        self.reader_panel.load_chapters([ch])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_starting_chunk_index(self) -> int:
        plan = get_plan_for_book(self.book_id)
        if not plan:
            return 0
        chunks = get_chunks_for_plan(plan.id)
        if not chunks:
            return 0
        saved = get_last_chunk_index(plan.id)
        return max(0, min(saved, len(chunks) - 1))

    def _sync_chapter_to_chunk(self) -> None:
        """Set chapter index to the first chapter of the current session."""
        plan = get_plan_for_book(self.book_id)
        if not plan:
            return
        chunks = get_chunks_for_plan(plan.id)
        if not chunks or self._current_chunk_index >= len(chunks):
            return
        chunk = chunks[self._current_chunk_index]
        try:
            self._current_chapter_index = int(chunk.start_location)
        except ValueError:
            self._current_chapter_index = 0

    def _chapters_for_chunk(self, chunk) -> list:
        try:
            start = int(chunk.start_location)
            end = int(chunk.end_location)
            result = self._all_chapters[start:end + 1]
            return result if result else self._all_chapters[:1]
        except (ValueError, IndexError):
            return self._all_chapters[:1]

    @staticmethod
    def _session_label(chunk, total: int) -> str:
        status = "✓" if chunk.is_complete else " "
        return f"{status}  Session {chunk.sequence} of {total}  —  {chunk.label}"

    def _save_position(self) -> None:
        plan = get_plan_for_book(self.book_id)
        if plan:
            save_last_chunk_index(plan.id, self._current_chunk_index)
            save_last_scroll_pct(plan.id, self._current_scroll_pct)

    def _on_scroll_changed(self, session_pct: int) -> None:
        self._current_scroll_pct = session_pct
        self._update_progress(session_pct)

    def _update_progress(self, session_pct: int | None = None) -> None:
        if session_pct is None:
            session_pct = 0

        if not self._session_mode:
            # Chapter mode: use chapter index against total chapters
            total = len(self._all_chapters)
            if not total:
                return
            book_pct = int((self._current_chapter_index + session_pct / 100) / total * 100)
        else:
            plan = get_plan_for_book(self.book_id)
            if not plan:
                return
            chunks = get_chunks_for_plan(plan.id)
            total = len(chunks)
            if not total:
                return
            book_pct = int((self._current_chunk_index + session_pct / 100) / total * 100)

        book_pct = min(max(book_pct, 0), 100)
        self.progress_label.setText(f"{session_pct}%  |  {book_pct}%")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_combo_selected(self, idx: int) -> None:
        if idx < 0:
            return
        if self._session_mode:
            if idx == self._current_chunk_index:
                return
            self._current_scroll_pct = 0
            self._current_chunk_index = idx
            self._save_position()
            self._sync_chapter_to_chunk()
            self._render_session()
        else:
            if idx == self._current_chapter_index:
                return
            self._current_scroll_pct = 0
            self._current_chapter_index = idx
            self._render_chapter()
        self.reader_panel.scroll_to_top()

    def _prev(self) -> None:
        if self._session_mode:
            if self._current_chunk_index > 0:
                self._current_scroll_pct = 0
                self._current_chunk_index -= 1
                self._save_position()
                self._sync_chapter_to_chunk()
                self._render_session()
                self.reader_panel.scroll_to_top()
        else:
            if self._current_chapter_index > 0:
                self._current_scroll_pct = 0
                self._current_chapter_index -= 1
                self._render_chapter()
                self.reader_panel.scroll_to_top()

    def _next(self) -> None:
        if self._session_mode:
            plan = get_plan_for_book(self.book_id)
            if not plan:
                return
            chunks = get_chunks_for_plan(plan.id)
            if self._current_chunk_index < len(chunks) - 1:
                current = chunks[self._current_chunk_index]
                if not current.is_complete:
                    mark_chunk_complete(current.id)
                self._current_scroll_pct = 0
                self._current_chunk_index += 1
                self._save_position()
                self._sync_chapter_to_chunk()
                self._render_session()
                self.reader_panel.scroll_to_top()
        else:
            if self._current_chapter_index < len(self._all_chapters) - 1:
                self._current_scroll_pct = 0
                self._current_chapter_index += 1
                self._render_chapter()
                self.reader_panel.scroll_to_top()

    def _toggle_mode(self) -> None:
        self._session_mode = not self.mode_btn.isChecked()
        if self.mode_btn.isChecked():
            # Switched to Full Book / chapter mode
            self.mode_btn.setText("Session Only")
            # Force combo repopulation by setting wrong count sentinel
            self.nav_combo.blockSignals(True)
            self.nav_combo.clear()
            self.nav_combo.blockSignals(False)
        else:
            # Switched back to Session mode
            self.mode_btn.setText("Full Book")
            self.nav_combo.blockSignals(True)
            self.nav_combo.clear()
            self.nav_combo.blockSignals(False)
        self._render()

    # ------------------------------------------------------------------
    # Session end
    # ------------------------------------------------------------------

    def _end_session(self) -> None:
        self._tts_stop()
        if self.session:
            plan = get_plan_for_book(self.book_id)
            if plan:
                chunks = get_chunks_for_plan(plan.id)
                if chunks and self._current_chunk_index < len(chunks):
                    current = chunks[self._current_chunk_index]
                    if not current.is_complete:
                        mark_chunk_complete(current.id)
                save_last_chunk_index(plan.id, self._current_chunk_index)
                save_last_scroll_pct(plan.id, self._current_scroll_pct)

            finish_session(
                self.session.id,
                pages_read=0,
                words_read=0,
                mark_chunk_done=False,
            )
            self.session = None

        self.session_ended.emit()

    def _scroll_up(self) -> None:
        self.reader_panel.scroll_by(0, -120)

    def _scroll_down(self) -> None:
        self.reader_panel.scroll_by(0, 120)

    def _show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Reader Error", msg)

    # ------------------------------------------------------------------
    # Text-to-speech (spike)
    # ------------------------------------------------------------------

    def _setup_tts(self) -> None:
        self._tts = QTextToSpeech(self)
        self._tts.stateChanged.connect(self._on_tts_state_changed)

    def _tts_play_pause(self) -> None:
        if self._tts is None:
            return
        if self._tts.state() == QTextToSpeech.State.Speaking:
            self._tts.pause()
        elif self._tts.state() == QTextToSpeech.State.Paused:
            self._tts.resume()
        else:
            # Extract visible text from page then speak
            self.reader_panel.web.page().runJavaScript(
                "document.body.innerText",
                self._tts_speak,
            )

    def _tts_speak(self, text: str | None) -> None:
        if not text or self._tts is None:
            return
        self._tts.say(text)

    def _tts_stop(self) -> None:
        if self._tts is not None:
            self._tts.stop()

    def _tts_set_rate(self, value: int) -> None:
        if self._tts is not None:
            self._tts.setRate(value / 10.0)   # -1.0 … 1.0

    def _on_tts_state_changed(self, state: QTextToSpeech.State) -> None:
        speaking = state == QTextToSpeech.State.Speaking
        paused   = state == QTextToSpeech.State.Paused
        self.tts_play_btn.setChecked(speaking or paused)
        if speaking or paused:
            self.tts_play_btn.setText("⏸ Pause" if speaking else "▶ Resume")
        else:
            self.tts_play_btn.setText("▶ Read")
