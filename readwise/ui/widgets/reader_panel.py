"""
ReaderPanel: QtWebEngineView wrapper that renders EPUB/PDF chapter content.
Loads chapters via file:// URLs from the extracted EPUB cache so all
relative assets (images, CSS) resolve correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWidgets import QWidget, QVBoxLayout

from readwise.readers.epub_reader import EpubReader
from readwise.readers.base_reader import Chapter


class _ReadwisePage(QWebEnginePage):
    """Blocks link-click navigation so TOC/internal links don't redirect away."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            return False   # swallow the click
        return True


class ReaderPanel(QWidget):
    """Wraps QWebEngineView; loads one or more chapters as a single page."""

    scroll_changed = Signal(int)   # emits 0-100 scroll percentage

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader: EpubReader | None = None
        self._extract_dir: Path | None = None
        self._setup_ui()

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(500)
        self._scroll_timer.timeout.connect(self._poll_scroll)
        self._restore_pct: int = 0   # non-zero → scroll here after next load

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web = QWebEngineView()
        self.web.setPage(_ReadwisePage(self.web))
        self.web.loadFinished.connect(self._on_load_finished)
        settings = self.web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)

        layout.addWidget(self.web)

    def _on_load_finished(self, success: bool) -> None:
        if not success:
            print(f"[ReaderPanel] WARNING: page load failed: {self.web.url().toString()}",
                  file=sys.stderr)
            return
        if self._restore_pct > 0:
            pct = self._restore_pct
            self._restore_pct = 0
            self.web.page().runJavaScript(
                f"(function(){{"
                f"  var h = document.body.scrollHeight - window.innerHeight;"
                f"  if (h > 0) window.scrollTo(0, h * {pct / 100});"
                f"}})()"
            )
        self._scroll_timer.start()
        self._poll_scroll()

    def _poll_scroll(self) -> None:
        self.web.page().runJavaScript(
            "(function(){"
            "  var h = document.body.scrollHeight - window.innerHeight;"
            "  return h > 0 ? window.scrollY / h : 0;"
            "})()",
            self._on_scroll_ratio,
        )

    def _on_scroll_ratio(self, ratio) -> None:
        if ratio is None:
            return
        pct = int(min(max(ratio, 0), 1) * 100)
        self.scroll_changed.emit(pct)

    def load_epub(self, epub_path: str, book_id: str) -> EpubReader:
        """Initialise the reader for this EPUB. Call before load_chapters()."""
        self._reader = EpubReader(epub_path, book_id)
        self._extract_dir = self._reader.extract()
        return self._reader

    def load_chapters(self, chapters: list[Chapter]) -> None:
        """
        Render one or more chapters as a single scrollable page.
        Writes combined HTML to a temp file inside the EPUB cache dir and
        loads it via file:// URL so all relative asset paths resolve correctly.
        """
        if not self._reader or not self._extract_dir:
            self._show_inline_error("No content loaded.")
            return

        if not chapters:
            self._show_inline_error("No chapters to display.")
            return

        self._scroll_timer.stop()

        try:
            parts: list[str] = []
            for ch in chapters:
                html = self._reader.get_chapter_html(ch)
                body = _extract_body(html)
                parts.append(f'<section class="rw-chapter" id="ch-{ch.index}">{body}</section>')

            combined = _wrap_html("\n<hr class='rw-chapter-break'>\n".join(parts))

            # Write the temp file alongside the first chapter's actual extracted
            # file so relative image/asset paths resolve correctly.
            try:
                chapter_dir = self._reader.get_chapter_path(chapters[0]).parent
            except Exception:
                chapter_dir = self._extract_dir
            chapter_dir.mkdir(parents=True, exist_ok=True)
            tmp = chapter_dir / "_readwise_chunk.html"
            tmp.write_text(combined, encoding="utf-8")
            self.web.load(QUrl.fromLocalFile(str(tmp)))

        except Exception as exc:
            import traceback
            traceback.print_exc(file=sys.stderr)
            self._show_inline_error(f"Error loading chapter content: {exc}")

    def load_single_chapter(self, chapter: Chapter) -> None:
        self.load_chapters([chapter])

    def show_message(self, text: str) -> None:
        """Display a plain informational message in the reader area."""
        self.web.setHtml(
            f"<body style='font-family:sans-serif;padding:40px;color:#888'>"
            f"<p>{text}</p></body>"
        )

    def _show_inline_error(self, text: str) -> None:
        self.web.setHtml(
            f"<body style='font-family:sans-serif;padding:40px;color:#c00'>"
            f"<p>{text}</p></body>"
        )

    def set_font_size(self, px: int) -> None:
        self.web.settings().setFontSize(
            QWebEngineSettings.FontSize.DefaultFontSize, px
        )

    def scroll_to_pct(self, pct: int) -> None:
        """Queue a scroll-to-percentage restore on the next page load."""
        self._restore_pct = max(0, min(pct, 100))

    def scroll_to_top(self) -> None:
        self._restore_pct = 0
        self.web.page().runJavaScript("window.scrollTo(0, 0);")

    def scroll_by(self, dx: int, dy: int) -> None:
        self.web.page().runJavaScript(f"window.scrollBy({dx}, {dy});")


# ------------------------------------------------------------------
# HTML helpers
# ------------------------------------------------------------------

def _extract_body(html: str) -> str:
    """Extract content between <body> tags, or return full html if no tags."""
    import re
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else html


def _wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 18px;
    line-height: 1.75;
    max-width: 720px;
    margin: 40px auto;
    padding: 0 32px 80px;
    color: #1a1a1a;
    background: #fafafa;
  }}
  h1, h2, h3, h4 {{
    font-family: 'Segoe UI', system-ui, sans-serif;
    margin-top: 2em;
    color: #111;
  }}
  p {{ margin: 0 0 1.2em; }}
  blockquote {{
    border-left: 4px solid #ccc;
    margin: 1.5em 0;
    padding: 0.5em 1.2em;
    color: #555;
    font-style: italic;
  }}
  img {{ max-width: 100%; height: auto; }}
  a {{ color: #1971c2; text-decoration: none; }}
  hr.rw-chapter-break {{
    border: none;
    border-top: 2px solid #e0e0e0;
    margin: 3em 0;
  }}
  section.rw-chapter {{ margin-bottom: 2em; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
