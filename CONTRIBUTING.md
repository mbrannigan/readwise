# Contributing to ReadWise Desktop

This document covers the development workflow, branching strategy, commit and PR conventions, versioning, and release tagging.

---

## Table of Contents

- [Development Lifecycle](#development-lifecycle)
- [Branching Strategy](#branching-strategy)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Versioning (SemVer)](#versioning-semver)
- [Tagging a Release](#tagging-a-release)

---

## Development Lifecycle

```
Plan → Branch → Code → Commit → PR → Review → Merge → Tag (if release)
```

1. **Plan** — confirm the work is in scope (check `SPEC.md`, `ROADMAP.md`). If not, discuss first.
2. **Branch** — create a branch from `main` (see naming below).
3. **Code** — make focused changes; keep commits small and logical.
4. **Commit** — use the `commit-message` skill to generate the message.
5. **PR** — open a PR when the branch is ready to merge; use the `pr-description` skill.
6. **Review** — self-review or peer review; run `pytest` before merging.
7. **Merge** — squash-merge fix branches; regular merge for feature/phase branches.
8. **Tag** — tag `main` after merging a release (see [Tagging a Release](#tagging-a-release)).

---

## Branching Strategy

`main` is always stable and runnable. All work happens on short-lived branches.

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Phase feature | `phase-N/<short-description>` | `phase-2/highlights` |
| Sub-feature | `feat/<short-description>` | `feat/obsidian-sync` |
| Bug fix | `fix/<short-description>` | `fix/scroll-timer` |
| FIXES.md item | `fix/<fixes-item-id>-<description>` | `fix/p0-zip-slip` |
| Performance | `perf/<short-description>` | `perf/n-plus-one` |
| Refactor | `refactor/<short-description>` | `refactor/book-card-batch` |
| Docs / config | `chore/<short-description>` | `chore/update-roadmap` |

### Rules

- Branch from `main`; rebase on `main` if it diverges significantly.
- One logical unit of work per branch — don't mix a feature with unrelated bug fixes.
- FIXES.md coordination groups (e.g., the `book_card.py` batch) ship as one branch.
- Delete the branch after merging.

---

## Commit Messages

Use the **`commit-message`** skill to generate commit messages:

```
/commit-message
```

The skill will inspect staged changes and produce a conventional commit message. Review and adjust before committing.

**Format (Conventional Commits):**

```
<type>(<scope>): <short summary>

<optional body>

<optional footer>
```

**Types:** `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `chore`

**Examples:**

```
fix(epub): block zip slip path traversal in extractall

perf(library): batch plan queries and cache pixmaps in BookCard

feat(highlights): add color highlight capture in ReaderView
```

**Rules:**
- Summary line ≤ 72 characters, imperative mood ("add", not "added")
- Reference FIXES.md items where relevant: `fixes FIXES.md #1`
- Never include secrets, file paths from local machines, or debug output

---

## Pull Requests

Open a PR when the branch is ready to merge into `main`. Use the **`pr-description`** skill:

```
/pr-description
```

The skill will generate a summary, test plan, and checklist from the diff.

### When to open a PR

- Always — even for solo work. PRs are the record of what changed and why.
- Before merging any branch that touches the database schema, reader logic, or session tracking.
- After completing a FIXES.md coordination group.

### PR checklist (verify before merging)

- [ ] `pytest` passes
- [ ] No new dependencies added without updating `pyproject.toml` and asking first
- [ ] `FIXES.md` items resolved by this PR are moved to the **Done** section
- [ ] `ROADMAP.md` updated if a phase milestone was completed
- [ ] No debug prints or commented-out code left in

### Merge strategy

| Branch type | Merge strategy | Reason |
|-------------|----------------|--------|
| `fix/*` | Squash merge | Keep main history clean for small fixes |
| `perf/*` | Squash merge | Same |
| `feat/*` | Regular merge | Preserve individual commit history |
| `phase-N/*` | Regular merge | Phase history tells the story |
| `chore/*` | Squash merge | Housekeeping — no history value |

---

## Versioning (SemVer)

ReadWise follows [Semantic Versioning 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`

| Segment | Increment when… | Example |
|---------|-----------------|---------|
| `MAJOR` | Breaking change to stored data format (DB schema incompatible with prior versions) or major UX overhaul | `1.0.0 → 2.0.0` |
| `MINOR` | New feature or completed roadmap phase merged to main | `0.1.0 → 0.2.0` |
| `PATCH` | Bug fix, security fix, or performance improvement with no new features | `0.1.0 → 0.1.1` |

**Current version:** `0.1.0` (Phase 1 complete)

**Planned milestones:**

| Version | Milestone |
|---------|-----------|
| `0.1.0` | Phase 1 — read + track (current) |
| `0.2.0` | Phase 2 — highlights + Obsidian |
| `0.3.0` | Phase 3 — PDF reader |
| `0.4.0` | Phase 4 — Notion sync |
| `1.0.0` | Stable, distributable release |

**Update `pyproject.toml` version** as part of the PR that completes the milestone — before tagging.

---

## Environment Setup

### Windows — PySide6 version sensitivity

PySide6 has DLL compatibility issues on Windows with versions other than `6.8.2`. Always use the pinned version:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install "PySide6==6.8.2"
pip install -e ".[dev]"
```

**If you see** `ImportError: DLL load failed while importing QtWidgets` — your venv is using the wrong PySide6 version. Delete `.venv` and recreate it with the steps above.

Do not upgrade PySide6 without testing on Windows first.

---

## Tagging a Release

Tag `main` after merging a version-worthy PR (MINOR or PATCH increment).

```bash
# Ensure you are on main and it is up to date
git checkout main
git pull

# Create an annotated tag
git tag -a v0.2.0 -m "Phase 2: highlights and Obsidian sync"

# Push the tag
git push origin v0.2.0
```

**Tag naming:** `v<MAJOR>.<MINOR>.<PATCH>` — always prefixed with `v`.

**Tag message:** one sentence describing the milestone.

**When to tag:**

| Situation | Tag? |
|-----------|------|
| Phase milestone merged | Yes — MINOR bump |
| Security fix (P0 from FIXES.md) | Yes — PATCH bump |
| Bug or perf fix | Yes if user-visible; optional otherwise |
| Docs, chore, refactor only | No |
