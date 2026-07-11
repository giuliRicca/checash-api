# Che Cash Backend

FastAPI backend for Che Cash.

## Local Setup

1. Create and activate a Python 3.12+ virtual environment.
2. Install dependencies:

```powershell
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and set local PostgreSQL URLs and JWT secret.
4. Run migrations:

```powershell
alembic upgrade head
```

5. Start development server:

```powershell
fastapi dev app/main.py
```
