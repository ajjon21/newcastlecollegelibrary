# Newcastle College Library Management System

A Python and Flask library-management prototype backed by SQLite.

The application source lives in [newcastle-college-library](newcastle-college-library/README.md). See its README for installation, features, policy assumptions and limitations.

## Repository structure

- `newcastle-college-library/app.py` — Flask routes and SQLite data layer
- `newcastle-college-library/templates/` — server-rendered pages
- `newcastle-college-library/static/` — stylesheets
- `newcastle-college-library/tests/` — automated tests
- `newcastle-college-library/DEVELOPMENT_LOG.md` — factual development notes and milestone evidence
- `.github/workflows/tests.yml` — automated test workflow

## Quick start

```bash
cd newcastle-college-library
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000.

## Development

Run the test suite from `newcastle-college-library`:

```bash
python -m unittest discover -s tests -v
```
ReadMe will be redone for final system build.
