"""
ReadWise Desktop — entry point.
"""
import os
import sys

from PySide6.QtWidgets import QApplication

from readwise.db.database import Database
from readwise.ui.main_window import MainWindow


def main() -> None:
    Database.init()

    # QtWebEngine (Chromium) sandbox can block file:// and setHtml on Windows.
    # This must be set before QApplication is created.
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

    app = QApplication(sys.argv)
    app.setApplicationName("ReadWise")
    app.setOrganizationName("ReadWise")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
