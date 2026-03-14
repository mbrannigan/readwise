# CLAUDE.md – ReadWise Desktop

> - Project overview: [CONTEXT.md](CONTEXT.md)
> - Architecture & structure: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
> - Feature specification: [SPEC.md](SPEC.md)
> - Phased roadmap: [ROADMAP.md](ROADMAP.md)

---

## Safety and Data Integrity

- All interactions with Calibre's `metadata.db` must be read-only.
- Never drop, alter, or create tables in a user's Calibre database.
- Never delete, move, or overwrite ebook files automatically.
- Use parameterized queries — no string-formatted SQL.
- If an operation might mutate user data, stop and ask.

## Dependencies

Do not introduce new dependencies without asking first.

## Coding Rules

- PEP 8, type hints on all new functions and public methods.
- Keep functions and methods short and focused.
- Clear code over clever code.
- Modify existing files instead of creating new ones unless a new module is clearly warranted.
- Do not add docstrings, comments, or type annotations to code that wasn't changed.
- Do not add features, refactors, or "improvements" beyond what was asked.

## Error Handling

- Anticipate missing/corrupted `metadata.db` and Calibre version differences (missing columns, extra tables).
- Fail with clear error messages; detect missing columns and fail soft, not hard.

## New Feature Requests

Before implementing any new feature or behaviour change:

1. Check it against `SPEC.md`, `ROADMAP.md`, and `CONTEXT.md`.
2. If the request goes beyond the current spec or roadmap phase — or introduces scope that wasn't discussed — say so clearly and ask for confirmation before proceeding.
3. If the user approves, update the appropriate root `.md` files to reflect the change before or alongside the implementation.

The goal is to keep the docs and the code in sync, and to catch scope creep early rather than after the fact.

## Commits and Pull Requests

When asked to commit or write a commit message, use the **`commit-message`** skill:
- Invoke `/commit-message` — it will inspect staged changes and generate a conventional commit message.
- Commit type must match the branch type (`fix`, `feat`, `perf`, `refactor`, `chore`, etc.).
- If the commit resolves one or more FIXES.md items, include `fixes FIXES.md #N` in the message footer.

When asked to open a PR or write a PR description, use the **`pr-description`** skill:
- Invoke `/pr-description` — it will generate a summary, test plan, and checklist from the diff.
- Before the PR merges: move resolved FIXES.md items to the Done section; update `ROADMAP.md` if a milestone completed; bump `pyproject.toml` version if this is a MINOR or PATCH release.

See `CONTRIBUTING.md` for the full branching strategy, merge rules, SemVer guidance, and tagging process.

## Code Review

When asked to review the code, run all three skills in parallel:

1. **`code-reviewer`** — code quality, SOLID, Qt lifecycle, signal/slot correctness, runtime bugs
2. **`performance-profiler`** — N+1 queries, UI thread blocking, widget churn, memory, I/O
3. **`senior-secops`** — SQL injection, path traversal, unsafe input handling, dependency vulnerabilities

After all three complete:

1. Consolidate findings into `FIXES.md`, grouped by section (Priority, Performance, Code Quality, Security, Confirm/Verify). Do not duplicate items already in `FIXES.md`.
2. Cross-check all fixes against each other for conflicts or regression risk:
   - Does fix A change an interface that fix B depends on?
   - Does fix A's change make fix B's symptom disappear (redundant)?
   - Could any fix change observable behaviour (not just internals)?
3. Reprioritize the full list based on: severity, regression risk, and dependency order (fixes that unblock other fixes come first). Update the ordering in `FIXES.md` to reflect the final priority.

## When Context Is Lost

Re-read this file and the four authoritative docs above, then inspect:
- `readwise/main.py`
- `readwise/ui/main_window.py`
- `readwise/db/database.py`
- `readwise/db/models/reading_plan.py`
