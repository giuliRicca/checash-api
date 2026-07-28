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
  - Cursor pagination uses the descending `(created_at, kind, id)` activity order so mixed
    transaction and transfer pages do not skip or prematurely exhaust older items.

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
- Balance adjustments create flagged transaction rows from server-calculated target-balance deltas.
- Adjustments use immutable global `Balance adjustment` categories, remain visible in activity, and
  are excluded from income, expense, and budget reporting.
- Account deletion permanently removes account transactions, adjustments, and linked transfers.
  Deleting a linked transfer reverses its effect on surviving counterpart accounts atomically.
- Permanent deletion requires explicit frontend confirmation by account name.
- Archive allowed with non-zero balance warning.
- Archived accounts excluded from net worth by default.
- New transactions/transfers blocked for archived accounts.

## Categories
- Categories table, not free-form strings.
- Global system categories plus user categories.
- System categories visible to all users.
- User categories visible only to owner.
- System categories immutable.
- Balance adjustment system categories stay visible but cannot be selected for normal transactions or budgets.
- Visible category slugs unique across system + user categories.
- `users.default_category_id` references categories.
- New users default to system `Miscellaneous` category; `default_account_id` starts unset.
- Transactions store `category_id` and `category_name_snapshot`.
- Delete category blocked if used.
- Category type is immutable and must match transaction type.
- Migration classifies existing user categories as `expense` unless only income transactions use it.
  This is acceptable only while project databases remain disposable; do not use this migration policy
  after production data exists.

## Transactions
- Transactions table stores only expense/income.
- Amounts stored positive.
- Transaction currency is independently ARS or USD and defaults to account currency only when legacy
  clients omit it. It may be edited; a currency or account edit refreshes the stored exchange rate and
  recalculates account impact atomically.
- Transactions store nominal `amount`, immutable ARS-per-USD `rate_used`, and converted
  `account_amount`. `account_amount` is rounded half-up to two decimals and is used for every
  account-balance create, update, delete, and history effect.
- Expense subtracts `account_amount`; income adds `account_amount`.
- Transactions allow account, category, amount, currency, description, and effective-time edits; type
  remains immutable. Regular transactions are deletable.
- Edit/delete must reverse old balance effect atomically.
- Balance adjustments are only created through the account adjustment endpoint and cannot be edited or
  deleted through transaction endpoints.
- Adjustment rows retain normal transaction balance semantics but are excluded from monthly summaries and budgets.
- `created_at` is immutable audit/feed time. User-editable, timezone-aware `occurred_at` records
  effective transaction time, defaults to current UTC time, and cannot be future.
- `occurred_at` stores PostgreSQL `timestamp with time zone`; ORM mappings must use
  `DateTime(timezone=True)` so UTC month-window parameters bind correctly.
- Monthly summaries use `occurred_at`; activity feeds remain ordered by `created_at`.

## Budgets
- One current-month budget per user and expense category.
- Budget limits use ARS or USD. All category expenses count by `occurred_at`; cross-currency
  spending converts using each transaction's stored rate. Legacy rows without one use the account's
  current rate type.
- Budget changes apply immediately to all matching expenses in current UTC calendar month.
- Visual progress only for MVP: no threshold notifications, rollover, custom periods, or groups.
- Deleting an unused user category cascades deletion of its budget.

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
- Downgrading `oficial`/`crypto` rate-type migration remaps affected accounts to `blue` and
  deletes their cached rates. This is allowed only for disposable pre-production databases.

## Net Worth
- Calculate symmetrically in ARS and USD.
- Total USD = USD accounts + ARS accounts / account rate.
- Total ARS = ARS accounts + USD accounts * account rate.
- Exclude archived accounts by default.
- Support `include_archived=true`.
- Persist immutable ARS/USD snapshots after account, transaction, and transfer balance changes when
  all active-account rates are cached. This avoids making money writes depend on the rate provider and
  retains observed valuations for future audit/history features.
- Current-month history is reconstructed live from current active-account balances and surviving
  transactions by `occurred_at`. It returns one end-of-day point per UTC day; backdated changes affect
  their effective date and later points.
- Transfers use `created_at` in this reconstruction until they gain a user-editable effective date.
- History applies current account rate types and current exchange-rate lookup rules to every point;
  edits and deletes intentionally update historical chart values.

## Monthly Transaction Summary
- `GET /api/transactions/month-summary` uses current UTC calendar-month window.
- Totals include transactions only, not transfers.
- ARS/USD conversion uses each transaction's stored rate. Legacy rows without a stored rate fall
  back to the account's current rate type.
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

## Documentation
- Every completed feature must update affected API, architecture, roadmap, and project-decision
  documentation before completion.
