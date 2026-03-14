"""
EPUB reader.

Strategy:
  - Parse the EPUB with ebooklib to get spine order, TOC, and item content.
  - Extract the full EPUB (it's a zip) to a persistent cache directory so
    QtWebEngine can load chapter files via file:// URLs — this handles all
    relative asset paths (images, CSS) automatically.
  - Cache dir: {app_data}/epub_cache/{book_id}/
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import ebooklib
from ebooklib import epub

from readwise.db.database import get_app_data_dir
from readwise.readers.base_reader import BaseReader, Chapter


class EpubReader(BaseReader):

    def __init__(self, epub_path: str, book_id: str):
        self.epub_path = Path(epub_path)
        self.book_id = book_id
        self._book: epub.EpubBook | None = None
        self._chapters: list[Chapter] | None = None
        self._extract_dir: Path | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_chapters(self) -> list[Chapter]:
        if self._chapters is not None:
            return self._chapters
        book = self._load()
        self._chapters = self._build_chapter_list(book)
        return self._chapters

    def get_chapter_html(self, chapter: Chapter) -> str:
        """Return styled, self-contained HTML for a chapter."""
        book = self._load()
        item = book.get_item_with_href(chapter.href)
        if item is None:
            return f"<html><body><p>Chapter not found: {chapter.href}</p></body></html>"
        raw = item.get_content().decode("utf-8", errors="replace")
        return self._inject_styles(raw)

    def extract(self) -> Path:
        """Extract EPUB zip to cache dir; return the root path."""
        if self._extract_dir and self._extract_dir.exists():
            return self._extract_dir

        cache_root = get_app_data_dir() / "epub_cache" / self.book_id
        if cache_root.exists():
            self._extract_dir = cache_root
            return cache_root

        cache_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.epub_path, "r") as zf:
            zf.extractall(cache_root)

        self._extract_dir = cache_root
        return cache_root

    def get_chapter_path(self, chapter: Chapter) -> Path:
        """Return the absolute path to a chapter's extracted file."""
        if not self._extract_dir:
            raise RuntimeError("Call extract() before get_chapter_path()")
        return self._extract_dir / self._opf_dir() / chapter.href

    def _opf_dir(self) -> Path:
        """Return the directory containing the OPF, relative to extract root."""
        if not self._extract_dir:
            return Path(".")
        container_xml = self._extract_dir / "META-INF" / "container.xml"
        if container_xml.exists():
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(container_xml)
                for el in tree.iter():
                    if el.tag.endswith("rootfile"):
                        opf_path = el.get("full-path", "")
                        if opf_path:
                            return Path(opf_path).parent
            except Exception:
                pass
        return Path(".")

    def estimate_word_count(self) -> int:
        total = 0
        for ch in self.get_chapters():
            total += ch.word_count
        return total

    # ------------------------------------------------------------------
    # Chapter list building
    # ------------------------------------------------------------------

    def _build_chapter_list(self, book: epub.EpubBook) -> list[Chapter]:
        """
        Build an ordered chapter list from the spine, enriched with TOC labels.
        Falls back to item filenames if TOC is missing or incomplete.
        """
        # Build label map from TOC: href (without fragment) → label
        toc_labels: dict[str, str] = {}
        self._walk_toc(book.toc, toc_labels)

        chapters: list[Chapter] = []
        index = 0

        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            href = item.get_name()
            # Strip fragment for label lookup
            href_base = href.split("#")[0]

            label = (
                toc_labels.get(href_base)
                or toc_labels.get(href)
                or _humanize(href)
            )

            content = item.get_content().decode("utf-8", errors="replace")
            word_count = _count_words(content)

            chapters.append(Chapter(
                index=index,
                label=label,
                href=href,
                word_count=word_count,
                start_location=str(index),
                end_location=str(index),
            ))
            index += 1

        return chapters

    def _walk_toc(self, toc_items, label_map: dict[str, str]) -> None:
        """Recursively walk epub TOC to build href → label map."""
        for item in toc_items:
            if isinstance(item, epub.Link):
                href = item.href.split("#")[0]
                if href and item.title:
                    label_map.setdefault(href, item.title.strip())
            elif isinstance(item, tuple) and len(item) == 2:
                section, children = item
                if isinstance(section, epub.Section) and section.href:
                    href = section.href.split("#")[0]
                    if section.title:
                        label_map.setdefault(href, section.title.strip())
                self._walk_toc(children, label_map)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> epub.EpubBook:
        if self._book is None:
            self._book = epub.read_epub(str(self.epub_path), options={"ignore_ncx": False})
        return self._book

    def _inject_styles(self, html: str) -> str:
        """Inject a reader stylesheet into chapter HTML."""
        style = """
        <style>
          body {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 18px;
            line-height: 1.75;
            max-width: 720px;
            margin: 40px auto;
            padding: 0 32px 80px;
            color: #1a1a1a;
            background: #fafafa;
          }
          h1, h2, h3, h4 {
            font-family: 'Segoe UI', system-ui, sans-serif;
            margin-top: 2em;
            color: #111;
          }
          p { margin: 0 0 1.2em; }
          blockquote {
            border-left: 4px solid #ccc;
            margin: 1.5em 0;
            padding: 0.5em 1.2em;
            color: #555;
            font-style: italic;
          }
          img { max-width: 100%; height: auto; }
          a { color: #1971c2; }
        </style>
        """
        if "</head>" in html:
            return html.replace("</head>", f"{style}</head>", 1)
        return style + html


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html)
    return len(text.split())


def _humanize(href: str) -> str:
    """Turn a filename like 'chapter_03.xhtml' into 'Chapter 03'."""
    name = Path(href).stem
    name = re.sub(r"[_\-]", " ", name)
    return name.title()
