"""
Calibre library scanner.

Walks a Calibre library directory. Each book folder contains:
  - metadata.opf  (OPF/XML with title, author, tags, series, etc.)
  - cover.jpg     (cover image)
  - One or more format files: Book.epub, Book.pdf, Book.mobi, etc.

One Book record is produced per folder regardless of how many
format files exist inside it.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from lxml import etree

from readwise.db.models.book import (
    Book,
    BookFormat,
    get_book_by_calibre_id,
    new_book_id,
    upsert_book,
)

# Prefer epub, then pdf, then mobi when multiple formats exist
FORMAT_PRIORITY = ["epub", "pdf", "mobi", "azw3", "azw"]

# Namespaces used in OPF files
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


def scan_library(library_path: str | Path) -> list[Book]:
    """
    Scan a Calibre library directory and upsert all books into the DB.
    Returns the full list of Book objects after scanning.
    """
    library_path = Path(library_path)
    if not library_path.is_dir():
        raise ValueError(f"Library path does not exist: {library_path}")

    books: list[Book] = []
    for opf_file in library_path.rglob("metadata.opf"):
        book_folder = opf_file.parent
        try:
            book = _process_book_folder(book_folder)
            if book is not None:
                upsert_book(book)
                books.append(book)
        except Exception as exc:
            # Log and skip malformed folders without crashing the scan
            print(f"[scanner] Skipping {book_folder.name}: {exc}")

    return books


def _process_book_folder(folder: Path) -> Book | None:
    """Parse one Calibre book folder into a Book dataclass."""
    opf_path = folder / "metadata.opf"
    if not opf_path.exists():
        return None

    # Parse OPF
    try:
        tree = etree.parse(str(opf_path))
    except etree.XMLSyntaxError:
        return None

    root = tree.getroot()

    title = _opf_text(root, f"{{{DC_NS}}}title") or folder.name
    author = _opf_author(root)
    calibre_id = _opf_calibre_id(root) or folder.name

    # Cover image
    cover_path = folder / "cover.jpg"
    cover_str = str(cover_path) if cover_path.exists() else ""

    # Collect all readable format files
    available_formats = _collect_formats(folder)
    if not available_formats:
        return None  # No readable files — skip

    # Choose active format based on priority
    active_format = _pick_active_format(available_formats)

    # Check if already in DB (preserve user-chosen active_format)
    existing = get_book_by_calibre_id(calibre_id)
    if existing:
        active_format = existing.active_format
        book_id = existing.id
    else:
        book_id = new_book_id()

    return Book(
        id=book_id,
        calibre_id=calibre_id,
        title=title,
        author=author,
        cover_path=cover_str,
        available_formats=available_formats,
        active_format=active_format,
        total_pages=0,       # filled in lazily when book is opened
        total_words=0,
        total_chapters=0,
        added_date=date.today(),
        status=existing.status if existing else "NOT_STARTED",
        publisher=_opf_text(root, f"{{{DC_NS}}}publisher"),
        series=_opf_series(root),
        series_index=_opf_series_index(root),
        description=_opf_description(root),
        tags=_opf_tags(root),
        rating=_opf_rating(root),
        pub_date=_opf_text(root, f"{{{DC_NS}}}date"),
        language=_opf_text(root, f"{{{DC_NS}}}language"),
    )


def _collect_formats(folder: Path) -> list[BookFormat]:
    """Find all supported format files in the folder."""
    formats: list[BookFormat] = []
    for ext in FORMAT_PRIORITY:
        for f in folder.glob(f"*.{ext}"):
            formats.append(BookFormat(format=ext.upper(), path=str(f)))
    return formats


def _pick_active_format(formats: list[BookFormat]) -> str:
    """Return the highest-priority format available."""
    priority_order = [ext.upper() for ext in FORMAT_PRIORITY]
    available = {f.format for f in formats}
    for fmt in priority_order:
        if fmt in available:
            return fmt
    return formats[0].format


def _opf_text(root: etree._Element, tag: str) -> str:
    """Extract text content of the first matching tag."""
    el = root.find(f".//{tag}")
    return el.text.strip() if el is not None and el.text else ""


def _opf_author(root: etree._Element) -> str:
    """Extract author(s); Calibre stores them in dc:creator."""
    creators = root.findall(f".//{{{DC_NS}}}creator")
    names = [c.text.strip() for c in creators if c.text]
    return " & ".join(names) if names else "Unknown"


def _opf_description(root: etree._Element) -> str:
    """Extract description/synopsis, stripping HTML tags."""
    raw = _opf_text(root, f"{{{DC_NS}}}description")
    # Strip basic HTML tags Calibre sometimes includes
    import re
    return re.sub(r"<[^>]+>", "", raw).strip()


def _opf_tags(root: etree._Element) -> list[str]:
    """Extract Calibre tags/genres from dc:subject elements."""
    subjects = root.findall(f".//{{{DC_NS}}}subject")
    return [s.text.strip() for s in subjects if s.text]


def _opf_rating(root: etree._Element) -> float:
    """Extract Calibre rating from meta name='calibre:rating'."""
    for el in root.findall(f".//{{{OPF_NS}}}meta"):
        if el.get("name") == "calibre:rating":
            try:
                return float(el.get("content", 0))
            except (ValueError, TypeError):
                return 0.0
    return 0.0


def _opf_series(root: etree._Element) -> str:
    """Extract series name from meta name='calibre:series'."""
    for el in root.findall(f".//{{{OPF_NS}}}meta"):
        if el.get("name") == "calibre:series":
            return el.get("content", "").strip()
    return ""


def _opf_series_index(root: etree._Element) -> float:
    """Extract series index from meta name='calibre:series_index'."""
    for el in root.findall(f".//{{{OPF_NS}}}meta"):
        if el.get("name") == "calibre:series_index":
            try:
                return float(el.get("content", 0))
            except (ValueError, TypeError):
                return 0.0
    return 0.0


def _opf_calibre_id(root: etree._Element) -> str | None:
    """
    Extract the Calibre book ID from the OPF identifier.
    Calibre uses <dc:identifier opf:scheme="calibre">N</dc:identifier>.
    """
    for el in root.findall(f".//{{{DC_NS}}}identifier"):
        scheme = el.get(f"{{{OPF_NS}}}scheme", "").lower()
        if scheme == "calibre" and el.text:
            return el.text.strip()
    return None
