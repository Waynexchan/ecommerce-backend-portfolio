# Ecommerce Demo Backend API

Django REST backend for a multivendor ecommerce demo. The API supports product browsing, carts, checkout, customer accounts, vendors, payments, and reporting-friendly transactional data.

This repository is prepared as a portfolio backend for Junior Data Analyst, Reporting Analyst, and BI Analyst applications. The emphasis is not only the API implementation, but also the business data model behind ecommerce activity.

## Tech Stack

- Python
- Django
- Django REST Framework
- Simple JWT authentication
- SQLite for local development
- PostgreSQL support through `DATABASE_URL`
- django-cors-headers
- drf-yasg API documentation tooling
- Stripe and PayPal payment integrations
- Optional AWS S3 storage support

## Main Apps

- `store`: products, categories, cart, orders, coupons, reviews, taxes, checkout, payment status
- `userauths`: custom user model, profiles, JWT auth, registration, password reset
- `vendor`: vendor registration, dashboard, products, orders, earnings, coupons, notifications
- `customer`: customer orders, wishlist, notifications, invoices, settings
- `api`: API URL routing

## Main API Areas

- Users and JWT auth
- Product catalog and search
- Shopping cart
- Checkout and order creation
- Stripe and PayPal payment flows
- Customer order history and invoices
- Vendor dashboard, products, orders, earnings, and reviews
- Coupon and discount workflows

## Frontend Repository

Frontend repository: `PASTE_FRONTEND_REPO_URL_HERE`

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
copy .env.example .env
```

Update `.env` with local placeholder-safe values. For local development, SQLite is enough:

```env
SECRET_KEY=replace-with-your-own-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Run migrations:

```bash
python manage.py migrate
```

Create an admin user if needed:

```bash
python manage.py createsuperuser
```

Run the API locally:

```bash
python manage.py runserver
```

The local API will be available at:

```text
http://127.0.0.1:8000/api/v1/
```

## Data And Media Safety

Do not commit `.env`, `db.sqlite3`, `django_debug.log`, `media/`, `staticfiles/`, virtual environments, or Python cache files.

For demo data, prefer one of these approaches instead of committing `db.sqlite3`:

- Add Django fixtures with sanitized sample products, vendors, and orders.
- Add a management command that generates fake ecommerce demo data.
- Document a migration-only setup and let reviewers create local sample data.

For product images, keep uploaded `media/` out of Git. If sample product images are needed, add a small curated folder of sanitized assets and document that they are demo-only.

## Analytics Opportunities

The backend data model can support practical ecommerce reporting and BI questions:

- Monthly revenue
- Order count
- Average order value
- Best-selling products
- Product and category performance
- Customer repeat behaviour
- Vendor performance
- Coupon and discount analysis
- Order status trends
- Payment method analysis

## Portfolio Note

This backend demonstrates how ecommerce transactions become structured business data. Customer browsing, cart creation, checkout, order status, product performance, vendor earnings, and payment events can all feed reporting workflows and BI dashboards.

For analyst roles, this project can be presented as a data-generating application that supports later analysis in SQL, Excel, Power BI, Tableau, or Python.

## GitHub Safety Note

Before publishing, confirm that no real credentials, runtime logs, local databases, uploaded media, virtual environments, or generated static files are tracked. If sensitive files were previously committed, rotate those credentials and consider publishing from a clean new Git history.
