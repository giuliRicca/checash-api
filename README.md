# Che Cash Backend

FastAPI backend for Che Cash.

## Local Setup

1. Create and activate a Python 3.12+ virtual environment.
2. Install dependencies:

```powershell
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env`. Set `DATABASE_URL` and `JWT_SECRET_KEY` (minimum 16
   characters). Set `TEST_DATABASE_URL` only when running tests.
4. Run migrations:

```powershell
alembic upgrade head
```

5. Start development server:

```powershell
fastapi dev app/main.py
```

## Tests

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database, then run:

```powershell
pytest
```

The test fixture downgrades that database to `base` and upgrades it to `head` before tests.
