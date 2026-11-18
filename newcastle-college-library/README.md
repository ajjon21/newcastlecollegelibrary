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
- Search: all fields or a selected title, author, ISBN or genre field. ISBN uses an exact indexed lookup; other fields use indexed columns with substring matching.
- Members: registration and member ID uniqueness.
- Loans: 14-day loan period, five active loans per member, return processing.
- Fines: prototype policy is 25p per overdue day, applied on return.
- Waitlists: FIFO ordering. A returned copy is offered to the oldest waiting member; staff can fulfil the offer to create the next loan.
- Analytics: most-borrowed titles and borrowing counts by genre.

## Data structures and algorithm notes
- SQLite B-tree indexes are created for ISBN, title, author, genre, active member loans and waitlist order.
- ISBN equality lookup is indexed. Text searches use parameterised SQL `LIKE` queries; substring searches may still scan matching index ranges depending on the query plan and SQLite optimiser.
- Waitlist allocation is FIFO using an increasing integer key (`ORDER BY id`).
- Analytics use SQL aggregation (`COUNT`, `GROUP BY`, `ORDER BY`) rather than sorting all records in application memory.
- Relational tables and foreign keys provide durable records and referential integrity.

## Prototype policy / limitations
This is a teaching prototype, not a production library platform. It has no authentication/role permissions, email/SMS notifications, barcode integration, multi-branch stock, or deployment hardening. Staff must contact a member when a waitlist entry becomes `offered`. Fine policy and loan limits should be confirmed by the college. For production, add authentication, CSRF protection, audit logs, backups, migrations, concurrency tests and privacy review. Change `SECRET_KEY` in a deployed environment.

## GitHub
Create an empty repository on https://github.com/new, then from this folder run:
```bash
git init
git add .
git commit -m "Initial Newcastle College Library prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/newcastle-college-library.git
git push -u origin main
```
Replace `YOUR-USERNAME` with the GitHub account name. Do not commit real student/member data or the generated `library.db`.

## Reset demo data
Stop the app, delete `library.db`, then run `python app.py` again. The sample database will be recreated.
