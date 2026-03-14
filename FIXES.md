# ReadWise — Pending Fixes

Items from code review, performance profiling, and security audit.
Cross-checked for conflicts and ordered by: severity → regression risk → dependency order.

---

## Coordination Notes

Before implementing, note these inter-fix dependencies:

- **#3, #4, #11, #12 all touch `book_card.py`** — implement in a single pass in this order:
  #11 (move imports) → #3 (constructor + batch load) → #4 (pixmap cache) → #12 (optional)
- **#1 reduces but does not eliminate #2** — fix both; #1 stops the timer when idle, #2 removes
  the DB calls while the timer is running.
- **#5 (widget rebuild diff) is lower urgency after #3 + #4** — once N+1 queries are batched and
  pixmaps cached, rebuild cost drops significantly. Defer #5 until the library is noticeably large.
- **#16 (disable JS) would break scroll tracking** — `_poll_scroll`, `scroll_to_pct`, `scroll_by`
  all use `runJavaScript`. Disabling JS requires a new scroll mechanism first. Do not attempt #16
  without a plan for replacing JS-based scroll.
- **#13 is resolved** — `ON DELETE CASCADE` confirmed in migration. Manual chunk delete is
  redundant but harmless; sessions correctly set `chunk_id = NULL`. No action required.

---

## P0 — Security: Fix Now (small, self-contained)

### 1. Zip slip — EPUB extraction — `epub_reader.py:64` — **Medium**
`zipfile.extractall()` on Python 3.11 does not prevent `../` path traversal in zip entry names.
A crafted EPUB could overwrite files outside the epub_cache directory.
**No conflicts. Regression risk: None for valid EPUBs.**
**Fix:**
```python
resolved_root = cache_root.resolve()
for member in zf.infolist():
    dest = (cache_root / member.filename).resolve()
    if not str(dest).startswith(str(resolved_root)):
        raise ValueError(f"Zip slip blocked: {member.filename}")
zf.extractall(cache_root)
```

### 2. Unescaped text in WebView HTML — `reader_panel.py:143,148` — **Low**
`show_message()` and `_show_inline_error()` insert `text` directly into HTML:
```python
f"<p>{text}</p>"
```
Currently only internal strings are passed, but a file path or error message containing
`<` could render as HTML. One-liner fix.
**No conflicts. Regression risk: None.**
**Fix:** `import html` at top of file; wrap inserts as `html.escape(text)`.

---

## P1 — Runtime: Fix Soon

### 3. Scroll timer never stops — `reader_panel.py:72`
`_scroll_timer` starts on every page load and runs at 500ms indefinitely.
Never stopped when the reader is hidden or the session ends.
**No conflicts. Regression risk: Low.**
**Fix:** Call `self._scroll_timer.stop()` from `ReaderPanel` when hiding,
and from `ReaderView._end_session()`.

### 4. DB queried every 500ms during reading — `reader_view.py:358–365`
`_on_scroll_changed` → `_update_progress` → `get_plan_for_book` + `get_chunks_for_plan`
on every scroll tick. Plan and chunk count don't change while reading.
**Partially mitigated by #3 (timer stops when idle) but still fires while reading.**
**No conflicts. Regression risk: Low.**
**Fix:** Cache `_plan` and `_chunk_total` as instance variables when session loads.
Invalidate only on chunk navigation.

---

## P2 — Performance: Coordinate as a Batch (all touch `book_card.py` / `library_view.py`)

### 5. Move inline imports — `book_card.py:109,154`, `reader_view.py:192`, `library_view.py:442`
Prerequisite for #6 and #7 — do this first in the same editing pass.
```
book_card.py:109   from PySide6.QtWidgets import QHBoxLayout
book_card.py:154   from readwise.config.settings import Settings
reader_view.py:192 from readwise.db.models.book import upsert_book
library_view.py:442 from readwise.ui.widgets.book_card import BookCard
```
**No conflicts. Regression risk: None.**

### 6. N+1 query pattern — `library_view.py` + `book_card.py` — **do after #5**
Every `_render()` runs `get_plan_for_book` + `get_chunks_for_plan` × N books.
For 200 books: 400+ DB queries per sort/filter/resize.
**Changes BookCard constructor — coordinate with #7 and #8.**
**Regression risk: Medium** — all BookCard instantiation sites must pass `progress: int`.
Currently only `_make_book_card()` in library_view.py creates cards.
**Fix:** Batch-load in `_render()` before card creation:
```python
# one query for all plans, one for chunk completion counts
# pass progress=computed_pct into BookCard(book, progress=pct, ...)
```
Remove `_compute_progress()` from BookCard entirely.

### 7. Synchronous pixmap loading — `book_card.py:94` — **do alongside #6**
Every card reads and scales cover JPEG from disk during `_render()`.
**Independent of #6's constructor change but touches the same file — batch together.**
**Regression risk: Low.**
**Fix:** Module-level `_PIXMAP_CACHE: dict[str, QPixmap] = {}` in book_card.py.
Check cache before loading; store after first load.

### 8. `mousePressEvent` monkey-patching — `book_card.py:121,132,149,192` — **do alongside #6, #7**
Assigning `label.mousePressEvent = self._method` skips base class event handling.
**Low urgency but same file — clean up while already editing book_card.py for #6 and #7.**
**Regression risk: Medium** — must verify all click interactions still work after change.
**Fix:** One small `_ClickableLabel(QLabel)` subclass; replace inline assignments.

### 9. Defer word count on chapter list build — `epub_reader.py:131`
All chapter HTML decoded and word-counted on first book open, blocking the reader from appearing.
**No conflicts with other fixes. Regression risk: Low.**
**Fix:** Set `word_count=0` in `_build_chapter_list`. Compute lazily in `estimate_word_count()`
only when actually needed (book setup wizard).

### 10. Three passes over OPF meta elements — `calibre_scanner.py:168,181,188`
`_opf_series()`, `_opf_series_index()`, `_opf_rating()` each iterate all `<meta>` elements.
**No conflicts. Regression risk: Low.**
**Fix:** One helper that walks meta elements once and returns `dict[str, str]`.

---

## P3 — Code Quality (safe, low regression risk)

### 11. Dead module-level constant — `library_view.py:26`
`_COLS = 4` is unused (replaced by `self._cols`). Risk: someone uses it in a future
render method and silently breaks dynamic reflow.
**Remove it. Regression risk: None.**

### 12. `finish_session` return type wrong — `session_manager.py:32`
Declared `-> ReadingSession` but `get_session()` can return `None`.
**Fix:** Change to `-> ReadingSession | None`. Annotation only, no behaviour change.**

### 13. `_load_epub` queries plan twice — `reader_view.py:199,211`
`get_plan_for_book` result at line 199 discarded; called again at line 211.
**Fix:** Reuse result. Regression risk: None.**

---

## P4 — Longer Term (higher regression risk or blocked by other work)

### 14. Full widget rebuild on every render — `library_view.py:266–269`
All cards destroyed and recreated on every sort/filter/search/resize.
**Lower urgency once #6 (N+1) and #7 (pixmap cache) are in place.**
**Regression risk: High** — diff logic must handle all view modes (flat, series grouped,
series drill, author filter). Defer until library performance is still noticeably slow
after P2 fixes.

### 15. Disable JavaScript in WebView — `reader_panel.py` — **Blocked by scroll mechanism**
Disabling JS would close the unsanitized EPUB HTML attack surface (#16 below).
**Blocked:** `_poll_scroll`, `scroll_to_pct`, `scroll_by`, and `_on_load_finished` scroll
restore all use `runJavaScript`. Disabling JS breaks all scroll tracking.
**Prerequisite:** Replace JS-based scroll with a Qt-native alternative before attempting.

---

## Accepted / No Action

### 16. Chromium sandbox disabled — `main.py:18` — **Medium (accepted)**
Required on Windows for `file://` URL loading. No Qt-native alternative currently.
Mitigated by remote URL block and link navigation intercept. Revisit if Qt adds a
sandboxed local-file mode.

### 17. Unsanitized EPUB HTML in WebView — `epub_reader.py:50`, `reader_panel.py:117` — **Medium (accepted)**
Raw EPUB HTML rendered with JS enabled. Risk is limited to malicious EPUBs in the
user's own Calibre library. Mitigated by no remote access and link navigation blocked.
Fully addressable only after #15 (disable JS) is resolved.

### 18. Unpinned dependency versions — `pyproject.toml` — **Low**
All deps use `>=`. Fine for a personal desktop app. Revisit if distributing to others.

---

## Confirm / Verify

### 19. `delete_plan_for_book` manual cascade — `reading_plan.py:205–213` — **RESOLVED**
`ON DELETE CASCADE` confirmed in `001_initial.sql`. Manual chunk delete is redundant
but harmless. Sessions correctly null `chunk_id` via `ON DELETE SET NULL` — correct behaviour.
No code change needed.

---

## Done
*(move items here when fixed)*
