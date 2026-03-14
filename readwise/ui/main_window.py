"""
MainWindow: app shell with a left nav sidebar and a central view switcher.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from readwise.ui.views.library_view import LibraryView
from readwise.ui.views.stats_view import StatsView
from readwise.ui.views.settings_view import SettingsView


class NavButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        title = QLabel("ReadWise")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(title)
        layout.addSpacing(16)

        self.btn_library = NavButton("Library")
        self.btn_stats   = NavButton("Progress")

        for btn in (self.btn_library, self.btn_stats):
            layout.addWidget(btn)

        layout.addStretch()

        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setStyleSheet(
            "QToolButton { font-size: 20px; border: none; border-radius: 4px; color: #555; }"
            "QToolButton:hover { background: #e8e8e8; }"
            "QToolButton:checked { color: #2a9d8f; }"
        )
        layout.addWidget(self.btn_settings)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ReadWise")
        self.resize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # View stack
        self.stack = QStackedWidget()
        self.library_view  = LibraryView()
        self.stats_view    = StatsView()
        self.settings_view = SettingsView()

        self.stack.addWidget(self.library_view)   # index 0
        self.stack.addWidget(self.stats_view)     # index 1
        self.stack.addWidget(self.settings_view)  # index 2

        root_layout.addWidget(self.stack)

        # Wire nav buttons
        self.sidebar.btn_library.clicked.connect(self._go_library)
        self.sidebar.btn_stats.clicked.connect(lambda: self._switch(1))
        self.sidebar.btn_settings.clicked.connect(lambda: self._switch(2))
        self.settings_view.library_scanned.connect(self.library_view.refresh)

        self._switch(0)

    def _go_library(self) -> None:
        self.library_view.go_home()
        self._switch(0)

    def _switch(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.sidebar.btn_library.setChecked(index == 0)
        self.sidebar.btn_stats.setChecked(index == 1)
        self.sidebar.btn_settings.setChecked(index == 2)

    def open_reader(self, book_id: str) -> None:
        """Open the reader view for a book (called from LibraryView)."""
        from readwise.ui.views.reader_view import ReaderView

        # Safely remove existing reader view if present
        if hasattr(self, "reader_view") and self.reader_view is not None:
            try:
                self.stack.removeWidget(self.reader_view)
                self.reader_view.hide()
                self.reader_view.setParent(None)
            except RuntimeError:
                pass  # already deleted
            self.reader_view = None

        self.reader_view = ReaderView(book_id, parent=self)
        self.reader_view.session_ended.connect(self._on_session_ended)
        idx = self.stack.addWidget(self.reader_view)
        self._switch(idx)

    def _on_session_ended(self) -> None:
        """Return to library after a session ends."""
        self._switch(0)
        self.library_view.refresh()
