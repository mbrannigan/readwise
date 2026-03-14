"""
Settings view.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from readwise.config.settings import Settings
from readwise.core.calibre_scanner import scan_library

_PROGRESS_STYLES = [
    ("bar",     "Bar only",    "===------"),
    ("bar_pct", "Bar + %",     "===------ 42%"),
    ("pct",     "% only",      "42%"),
]

_BTN_SS = (
    "QToolButton { border: 1px solid #ccc; border-radius: 3px;"
    " padding: 3px 10px; font-size: 12px; }"
    "QToolButton:checked { background: #4dabf7; color: white; border-color: #4dabf7; }"
)


class SettingsView(QWidget):
    library_scanned = Signal()   # emitted after a successful scan

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Settings", styleSheet="font-size:22px;font-weight:bold;"))

        form = QFormLayout()
        form.setSpacing(12)

        # Calibre library path
        calibre_row = QHBoxLayout()
        self.calibre_edit = QLineEdit()
        self.calibre_edit.setReadOnly(True)
        calibre_browse = QPushButton("Browse…")
        calibre_browse.clicked.connect(self._browse_calibre)
        calibre_scan = QPushButton("Scan Now")
        calibre_scan.clicked.connect(self._scan_library)
        calibre_row.addWidget(self.calibre_edit)
        calibre_row.addWidget(calibre_browse)
        calibre_row.addWidget(calibre_scan)
        form.addRow("Calibre Library:", calibre_row)

        # Obsidian vault path
        obsidian_row = QHBoxLayout()
        self.obsidian_edit = QLineEdit()
        self.obsidian_edit.setReadOnly(True)
        obsidian_browse = QPushButton("Browse…")
        obsidian_browse.clicked.connect(self._browse_obsidian)
        obsidian_row.addWidget(self.obsidian_edit)
        obsidian_row.addWidget(obsidian_browse)
        form.addRow("Obsidian Vault:", obsidian_row)

        # Book card progress display
        progress_row = QHBoxLayout()
        progress_row.setSpacing(4)
        self._progress_group = QButtonGroup(self)
        self._progress_group.setExclusive(True)
        for value, label, example in _PROGRESS_STYLES:
            btn = QToolButton()
            btn.setText(f"{label}  ({example})")
            btn.setCheckable(True)
            btn.setProperty("style_value", value)
            btn.setStyleSheet(_BTN_SS)
            btn.clicked.connect(self._on_progress_style_clicked)
            self._progress_group.addButton(btn)
            progress_row.addWidget(btn)
        progress_row.addStretch()
        form.addRow("Card Progress:", progress_row)

        layout.addLayout(form)
        layout.addStretch()

    def _load(self) -> None:
        s = Settings.get()
        self.calibre_edit.setText(s.calibre_library_path)
        self.obsidian_edit.setText(s.obsidian_vault_path)
        current = s.get_value("card_progress_style", "bar")
        for btn in self._progress_group.buttons():
            btn.setChecked(btn.property("style_value") == current)

    def _on_progress_style_clicked(self) -> None:
        btn = self.sender()
        Settings.get().card_progress_style = btn.property("style_value")

    def _browse_calibre(self) -> None:
        s = Settings.get()
        folder = QFileDialog.getExistingDirectory(
            self, "Select Calibre Library", s.calibre_library_path or str(Path.home())
        )
        if folder:
            s.calibre_library_path = folder
            self.calibre_edit.setText(folder)

    def _scan_library(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        s = Settings.get()
        if not s.calibre_library_path:
            QMessageBox.warning(self, "No Library Set", "Set a Calibre library path first.")
            return
        try:
            books = scan_library(s.calibre_library_path)
            self.library_scanned.emit()
            QMessageBox.information(self, "Scan Complete", f"Found {len(books)} book(s).")
        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))

    def _browse_obsidian(self) -> None:
        s = Settings.get()
        folder = QFileDialog.getExistingDirectory(
            self, "Select Obsidian Vault", s.obsidian_vault_path or str(Path.home())
        )
        if folder:
            s.obsidian_vault_path = folder
            self.obsidian_edit.setText(folder)
