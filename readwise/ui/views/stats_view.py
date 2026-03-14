"""
Stats / Progress view — Phase 3 placeholder.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from readwise.db.models.stats import get_stats


class StatsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Progress & Stats", styleSheet="font-size:22px;font-weight:bold;"))

        self.streak_label  = QLabel()
        self.longest_label = QLabel()
        self.pages_label   = QLabel()
        self.books_label   = QLabel()

        for lbl in (self.streak_label, self.longest_label, self.pages_label, self.books_label):
            lbl.setStyleSheet("font-size: 15px;")
            layout.addWidget(lbl)

        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        stats = get_stats()
        self.streak_label.setText(f"Current streak: {stats.current_streak} day(s)")
        self.longest_label.setText(f"Longest streak: {stats.longest_streak} day(s)")
        self.pages_label.setText(f"Total pages read: {stats.total_pages_read:,}")
        self.books_label.setText(f"Books completed: {stats.total_books_complete}")
