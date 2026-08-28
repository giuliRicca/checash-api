# Deployment Plan

## Production

- Frontend: Vercel, repository `checash-web`, branch `main`.
- API: Render, repository `checash-api`, branch `main`.
- Database: Neon Postgres pooled connection.
- Migrations: manual GitHub Actions workflow, never API startup.

## Production Migration

Backend GitHub environment `production` must contain:

- `DATABASE_URL`: Neon pooled asyncpg URL with TLS, for example
  `postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require`
- `JWT_SECRET_KEY`: stable secret, at least 32 bytes

For each migration:

1. Push migration to `main`.
2. Open **Actions → Migrate Production Database**.
3. Select **Run workflow**, branch `main`.
4. Wait for `alembic upgrade head` to succeed.
5. Verify Neon migration version and API `/api/health`.
6. Deploy/restart Render and deploy Vercel when application contract requires both.

For breaking API changes, migration is additive first, then deploy backend and frontend together.
The Phase 1 migration is additive; production reached `202608210001` successfully.

## Required Checks

Backend:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run pytest
```

Frontend:

```text
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Never commit `.env`, Neon connection URLs, or JWT secrets.
