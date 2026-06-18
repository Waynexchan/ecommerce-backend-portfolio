# GitHub Publishing Checklist

Use this checklist before pushing the backend repository to GitHub.

- Confirm `.env` is not tracked.
- Confirm `db.sqlite3` is not tracked.
- Confirm `django_debug.log` is not tracked.
- Confirm `media/`, `staticfiles/`, and virtual environment folders are not tracked.
- Confirm `__pycache__/` and `*.pyc` files are not tracked.
- Confirm `advanced_swecommerce_backend.git/` is not tracked.
- Confirm no real secrets exist in `backend/settings.py`.
- Confirm no Stripe, PayPal, AWS, email, database, JWT, or API secrets exist in source files.
- Confirm no real customer, order, user, address, or payment data is committed.
- Run `git status --short` before pushing.
- Run a secret scan before publishing.
- Rotate any credentials that were ever committed or exposed in logs.
- Consider creating a clean new GitHub repo if old history contains sensitive files.
