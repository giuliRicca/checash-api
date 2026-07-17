# Che Cash Project Decisions

## API
- Use `/api/...`, no `/api/v1` for MVP.
- Chat endpoints:
  - `POST /api/chat/parse-message`
  - `POST /api/chat/confirm`
- Manual endpoints:
  - `POST /api/transactions`
  - `POST /api/transfers`
- Unified feeds:
  - `GET /api/activity`
  - `GET /api/accounts/{account_id}/activity`

## Database
- PostgreSQL local instance.
- SQLAlchemy async with asyncpg.
- Alembic from day one.
- Autogenerate migrations, then review.
- No Docker Compose; assume existing local DB.

## Money
- Use Decimal end-to-end.
- Money: `NUMERIC(18, 2)`.
- Rates: `NUMERIC(18, 6)`.
- Round conversions with `ROUND_HALF_UP`.
- Reject float-style internal money handling.

## Auth
- Multi-user capable, no sharing/admin features.
- Normalize email with trim + lowercase.
- Password min length: 8.
- Password hashing: `pwdlib` Argon2id.
- JWT: PyJWT HS256.
- Access token lifetime: 7 days.
- No refresh tokens in MVP.

## Accounts
- Currency immutable.
- Rate type editable.
- Opening balance allowed.
- No direct balance edits after creation.
- Balance stored and updated atomically.
- Negative balances allowed.
- Archive accounts instead of deleting when used.
- Archive allowed with non-zero balance warning.
- Archived accounts excluded from net worth by default.
- New transactions/transfers blocked for archived accounts.

## Categories
- Categories table, not free-form strings.
- Global system categories plus user categories.
- System categories visible to all users.
- User categories visible only to owner.
- System categories immutable.
- Visible category slugs unique across system + user categories.
- `users.default_category_id` references categories.
- Transactions store `category_id` and `category_name_snapshot`.
- Delete category blocked if used.
- Category type is immutable and must match transaction type.
- Migration classifies existing user categories as `expense` unless only income transactions use it.
  This is acceptable only while project databases remain disposable; do not use this migration policy
  after production data exists.

## Transactions
- Transactions table stores only expense/income.
- Amounts stored positive.
- Expense subtracts balance.
- Income adds balance.
- Transactions editable/deletable.
- Edit/delete must reverse old balance effect atomically.

## Transfers
- Transfers use separate `transfers` table.
- Transfers are not transaction rows.
- Store source/destination account IDs.
- Store source/destination currency snapshots.
- Store source/destination amounts.
- Store `rate_used`.
- Same-currency transfers have no rate.
- Cross-currency transfer uses destination account rate type unless manual override.
- Manual override stored only on transfer, not rate cache.
- Transfers editable/deletable.
- Edit/delete must reverse old balance effects atomically.

## Exchange Rates
- Provider: `dolarapi.com`.
- Rate types: oficial, blue, mep, tarjeta, crypto.
- Provider `casa` mapping: oficial -> `oficial`, blue -> `blue`, mep -> `bolsa`, tarjeta ->
  `tarjeta`, crypto -> `cripto`.
- Use midpoint `(compra + venta) / 2`.
- Persist cache in `exchange_rates`.
- Refresh on demand when older than 1 hour.
- If provider fails, use latest cached rate.
- If no cached rate exists, return clear 503.

## Net Worth
- Calculate symmetrically in ARS and USD.
- Total USD = USD accounts + ARS accounts / account rate.
- Total ARS = ARS accounts + USD accounts * account rate.
- Exclude archived accounts by default.
- Support `include_archived=true`.

## Monthly Transaction Summary
- `GET /api/transactions/month-summary` uses current UTC calendar-month window.
- Totals include transactions only, not transfers.
- ARS/USD conversion uses each transaction account's current rate type, not historical rate.
- Money totals round to two decimal places with `ROUND_HALF_UP`.
- Rate cache/provider fallback rules apply; missing rate data returns 503.

## Chat Pipeline
- Parse-message never writes to DB.
- Parser returns confirm-ready draft.
- Rule parser for MVP.
- LLM-shaped interface for future.
- Fallback to default account/category when possible.
- If parser guesses/falls back on currency, set `needs_review=true`.
- Confirm endpoint revalidates everything before write.

## Activity Feed
- Unified feed merges transactions and transfers.
- Cursor pagination, not offset.
- Cursor is opaque base64 JSON with `created_at`, `kind`, and `id`.

## Testing And Verification
- Use real PostgreSQL test DB via `TEST_DATABASE_URL`.
- Required verification before completion:
  - `ruff check .`
  - `ruff format --check .`
  - `python -m compileall app tests`
  - `alembic upgrade head`
  - `alembic downgrade -1`
  - `alembic upgrade head`
  - `pytest`
- No completion claims without fresh command evidence.
