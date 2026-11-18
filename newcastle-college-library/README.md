# Newcastle College Library Management System

A runnable Python/Flask + SQLite prototype for a college library. It includes catalogue and member management, indexed searching, borrowing/returns, FIFO waitlists, fines and borrowing analytics.

## Requirements
- Python 3.10+
- pip

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. A demo catalogue and three sample members are seeded automatically on first run.

## Main features
- Books: create, edit, delete (deletion is blocked when loan history or waitlist records exist).
- Search: all fields or a selected title, author, ISBN or genre field. ISBN uses an exact lookup; other fields use parameterised substring matching.
- Members: registration and member ID uniqueness.
- Loans: 14-day loan period, five active loans per member, return processing.
- Fines: prototype policy is 25p per overdue day, applied on return.
- Waitlists: FIFO ordering. A returned copy is offered to the oldest waiting member; staff can fulfil the offer to create the next loan.
- Analytics: most-borrowed titles and borrowing counts by genre.

## Data structures and algorithm notes
- SQLite indexes support ISBN, title, author, genre, active member loans and waitlist order.
- ISBN equality lookup is indexed. Text searches use parameterised SQL `LIKE` queries; leading-wildcard substring searches may still require a table scan, depending on the query plan.
- Waitlist allocation is FIFO using an increasing integer key (`ORDER BY id`).
- Analytics use SQL aggregation (`COUNT`, `GROUP BY`, `ORDER BY`).
- Relational tables and foreign keys provide durable records and referential integrity.

## Tests
Run from this directory:
```bash
python -m unittest discover -s tests -v
```
GitHub Actions runs the same test command on pushes to `main` and `feature/**` branches and on pull requests to `main`.

## Prototype policy / limitations
This is a teaching prototype, not a production library platform. It has no authentication/role permissions, email/SMS notifications, barcode integration, multi-branch stock, or deployment hardening. Staff must contact a member when a waitlist entry becomes `offered`. Fine policy and loan limits should be confirmed by the college. For production, add authentication, CSRF protection, audit logs, backups, migrations, concurrency tests and privacy review. Set a strong `SECRET_KEY` in the deployment environment.

## Reset demo data
Stop the app, delete `library.db`, then run `python app.py` again. The sample database will be recreated. The database is local runtime data and is excluded from Git.
