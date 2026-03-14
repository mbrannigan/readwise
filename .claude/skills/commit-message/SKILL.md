---

name: commit-message

description: >

&nbsp; Analyze git changes and generate conventional commit messages. Supports batch commits

&nbsp; for multiple unrelated changes. Use when: (1) Creating git commits, (2) Reviewing

&nbsp; staged changes, (3) Splitting large changesets into logical commits.

---



\# commit-message



Analyze git changes and generate context-aware commit messages following Conventional Commits.



\## Quick Start



```bash

\# Analyze all changes

python3 .shared/commit-message/scripts/analyze\_changes.py --analyze



\# Get batch commit suggestions

python3 .shared/commit-message/scripts/analyze\_changes.py --batch



\# Generate message for specific files

python3 .shared/commit-message/scripts/analyze\_changes.py --generate "src/api/\*.py"

```



\## Commands



| Command | Description |

|---------|-------------|

| `--analyze` | Show all changed files with status and categories |

| `--batch` | Suggest how to split changes into multiple commits |

| `--generate \[pattern]` | Generate commit message for matching files |

| `--staged` | Only analyze staged changes (default: all changes) |



\## Commit Types



| Type | Description | Example |

|------|-------------|---------|

| `feat` | New feature | `feat(api): add user authentication` |

| `fix` | Bug fix | `fix(db): resolve connection timeout` |

| `refactor` | Code restructuring | `refactor(utils): simplify helper functions` |

| `docs` | Documentation | `docs: update README` |

| `test` | Tests | `test(api): add user endpoint tests` |

| `chore` | Maintenance | `chore: update dependencies` |

| `style` | Formatting | `style: fix linting errors` |



\## Batch Commit Workflow



When you have multiple unrelated changes:



1\. Run `--batch` to see suggested commit groups

2\. Stage files for first commit: `git add <files>`

3\. Commit with suggested message

4\. Repeat for remaining groups



\## Grouping Strategy



Files are grouped by:

\- \*\*Directory/Module\*\*: `src/api/`, `tests/`, `docs/`

\- \*\*Change Type\*\*: Added vs Modified vs Deleted

\- \*\*Semantic Relationship\*\*: Related files together



\## Context-Aware Commit Messages



> \*\*Note\*\*: The `analyze\_changes.py` script provides file grouping and basic suggestions. Use its output as a starting point, then read `git diff` to understand the actual changes and generate context-aware messages following the examples below.



When generating commit messages, analyze the \*\*actual code changes\*\* to infer business context. Don't just describe files—describe what the changes accomplish.



\### Scope Guidelines



The scope should reflect the \*\*business module or feature\*\*, not just the directory:



| Scope Type | Example | When to Use |

|------------|---------|-------------|

| Feature/Module | `companion`, `calendar`, `inbox` | Changes to a specific product feature |

| Platform | `ios`, `android`, `web` | Platform-specific changes |

| Integration | `outlook`, `gmail`, `slack` | Third-party integration changes |

| Component | `auth`, `api`, `db` | Core infrastructure changes |



\### Input/Output Examples



\*\*Example 1: New Feature\*\*

```

Input (code changes):

&nbsp; + src/companion/pages/AvailabilityDetailPage.tsx

&nbsp; + src/companion/pages/AvailabilityActionsPage.tsx

&nbsp; + src/companion/components/AvailabilityCard.tsx

&nbsp; M src/companion/navigation/routes.ts



Output:

&nbsp; feat(companion): add availability detail and actions pages for ios



&nbsp; - New AvailabilityDetailPage showing time slot details

&nbsp; - New AvailabilityActionsPage for booking/canceling

&nbsp; - AvailabilityCard component for list display

&nbsp; - Updated navigation routes

```



\*\*Example 2: Bug Fix\*\*

```

Input (code changes):

&nbsp; M src/integrations/outlook/email\_sender.py

&nbsp; M src/integrations/outlook/auth.py



Output:

&nbsp; fix(outlook): resolve email sending failures due to token expiration



&nbsp; Refresh OAuth token before sending when close to expiry

```



\*\*Example 3: Multi-platform Change\*\*

```

Input (code changes):

&nbsp; M ios/Calendar/CalendarView.swift

&nbsp; M android/calendar/CalendarFragment.kt

&nbsp; M web/src/calendar/Calendar.tsx



Output:

&nbsp; feat(calendar): add week view across all platforms



&nbsp; Implement consistent week view UI for iOS, Android, and web

```



\*\*Example 4: Chore/Maintenance\*\*

```

Input (code changes):

&nbsp; M package.json

&nbsp; M yarn.lock

&nbsp; M requirements.txt



Output:

&nbsp; chore(deps): update dependencies to latest versions

```



\### Writing Good Descriptions



|  Bad (Generic) | Good (Context-Aware) |

|-----------------|------------------------|

| `feat: add new file` | `feat(payments): add Stripe webhook handler` |

| `fix: fix bug` | `fix(auth): prevent session timeout on mobile` |

| `chore: update code` | `chore(ci): reduce build time with parallel jobs` |

| `refactor: refactor utils` | `refactor(api): extract rate limiting to middleware` |



\### Key Principles



1\. \*\*Read the code\*\* - Understand what the changes actually do

2\. \*\*Identify the feature\*\* - What user-facing or system capability is affected?

3\. \*\*Be specific\*\* - Include relevant details (platform, integration, component)

4\. \*\*Use active voice\*\* - "add", "fix", "update", not "added", "fixed", "updated"

5\. \*\*Keep it concise\*\* - First line under 72 characters

