# Development and Version History

This log records the development history of the Newcastle College Library Management System.

## Baseline prototype — 18 November 2026

The initial working prototype was assembled on this date. The first Git commit records the baseline project as it exists at this point; it does not claim that earlier development took place.

Included in the baseline:
- Flask application structure and SQLite schema.
- Book catalogue and search by title, author, ISBN and genre.
- Member registration and member records.
- Loan creation, return processing and overdue fine calculation.
- FIFO waitlist handling and reservation fulfilment.
- Borrowing analytics and initial dashboard.
- Setup instructions, dependency list and a smoke-test file.

## Recommended future milestones

Complete each milestone, run the relevant tests, inspect the changes, and then create a commit. Record the real date and a short summary below when the work is actually completed.

| Milestone | Suggested commit message | Evidence to retain |
|---|---|---|
| 1. Requirements and design | `docs: document requirements and system design` | Requirements, use cases, data-structure rationale |
| 2. Database and models | `feat: add library database schema and models` | Schema and database tests |
| 3. Catalogue and search | `feat: implement book catalogue and indexed search` | Search tests for each field and ISBN lookup |
| 4. Member management | `feat: add member registration and records` | Member validation tests |
| 5. Borrowing and returns | `feat: implement loans returns and fines` | Borrow/return and overdue-fine test results |
| 6. Reservation queue | `feat: add FIFO waitlist and reservation fulfilment` | Multiple-waiter ordering test |
| 7. Analytics and interface | `feat: add dashboard and borrowing analytics` | Screenshots and analytics test evidence |
| 8. Quality and release | `test: add integration tests and release documentation` | Test report, README, tagged release |

These are planned milestones, not historical commits. Do not assign past dates to them. If you continue developing the project, commit each completed change at the time it is made so Git records an authentic timeline.

## Keeping evidence

- Make small, meaningful commits as you work; avoid one large final commit for all changes.
- Use `git log --oneline --decorate --date=short` to review commit history.
- Use `git show <commit>` to show the files and code changes in a particular commit.
- Keep screenshots, test output and design notes in the repository where appropriate.
- Never commit real student data, passwords, API keys or the generated SQLite database.
