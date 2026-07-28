# Che Cash API

Base path: `/api`.

Authentication: protected endpoints require `Authorization: Bearer <access_token>`.

## Health
- `GET /api/health`

## Auth
- `POST /api/auth/register`
  - Body: `email`, `password`.
  - Returns bearer access token.
- `POST /api/auth/login`
  - Body: `email`, `password`.
  - Returns bearer access token.
- `GET /api/auth/me`
  - Returns current user profile.

## User Preferences
- `PATCH /api/users/me/preferences`
  - Body: optional `default_account_id`, optional `default_category_id`.
  - Omit field to leave it unchanged; send `null` to clear that default.

## Categories
- `GET /api/categories`
- `POST /api/categories`
  - Body: `name`, `type` (`expense` or `income`). Category type is immutable after creation.
- `PATCH /api/categories/{category_id}`
  - Body: `name`.
- `DELETE /api/categories/{category_id}`
  - Deletes only user-owned unused categories.

System categories are global, immutable, and visible to all users. Transaction categories must
match the transaction type; `Miscellaneous` is the expense fallback and `Uncategorized income`
is the income fallback.

## Accounts
- `POST /api/accounts`
  - Body: `name`, `currency` (`ARS` or `USD`), `rate_type`, optional `opening_balance`
    (defaults to `0.00`). Returns `200`.
- `GET /api/accounts?include_archived=false`
- `GET /api/accounts/{account_id}`
- `PATCH /api/accounts/{account_id}`
  - Body: optional `name`, optional `rate_type`.
- `POST /api/accounts/{account_id}/adjustments`
  - Body: `target_balance`, optional `description`, optional timezone-aware `occurred_at`.
  - Server calculates and records positive/negative difference as a balance adjustment transaction.
  - Target balance must differ from current balance. Adjustment rows are excluded from monthly summary
    and budget spending.
- `POST /api/accounts/{account_id}/archive`
  - Archives account. Non-zero balances return warning metadata.
- `DELETE /api/accounts/{account_id}`
  - Permanently deletes account, its transactions/adjustments, and linked transfers.
  - Reverses deleted transfer effects on surviving counterpart accounts. Clears default account when needed.
- `GET /api/accounts/net-worth?include_archived=false`
  - Returns symmetric totals in ARS and USD.
- `GET /api/accounts/net-worth/history`
  - Returns daily current-UTC-month net-worth points in ARS and USD for active accounts.
  - Reconstructs balances from current account balances and surviving current-month transactions by
    `occurred_at`; transfers use `created_at` until transfers support an effective date.

Account currency and balance are not directly editable after creation; use adjustment endpoint for a
recorded balance correction.
Supported `rate_type` values: `oficial`, `blue`, `mep`, `tarjeta`, `crypto`. Rates use dolarapi
`casa` values `oficial`, `blue`, `bolsa`, `tarjeta`, and `cripto`, respectively.

## Transactions
- `POST /api/transactions`
- Creates expense or income.
- Body: `account_id`, `category_id`, `amount`, `currency` (`ARS` or `USD`), `type`, optional `description`, optional
  timezone-aware `occurred_at`. It defaults to current UTC time and cannot be future.
  - `currency` defaults to account currency only for clients using prior API payloads. It is immutable
    after creation.
  - The response includes nominal `amount`, `currency`, immutable ARS-per-USD `rate_used`, and
    converted `account_amount` used for account balance effects.
   - The selected category must have the same type as the transaction.
   - Balance adjustment categories are reserved for account adjustment endpoint.
- `PATCH /api/transactions/{transaction_id}`
  - Updates transaction and recalculates balance atomically.
  - Body: optional `account_id`, `category_id`, `amount`, `currency`, `description`, `occurred_at`.
    Send `description: null` to clear it. `occurred_at` must be timezone-aware and not future.
  - Transaction type is immutable. Changing account or currency refreshes the stored exchange rate and
    recalculates account impact. Balance adjustments cannot be changed through transaction endpoints.
- `DELETE /api/transactions/{transaction_id}`
  - Deletes transaction and reverses balance effect atomically.
  - Balance adjustments cannot be deleted through transaction endpoints.

Transaction `type` values: `expense`, `income`.

### Month Summary
- `GET /api/transactions/month-summary`
- Returns `month_start`, `month_end`, `income_ars`, `income_usd`, `expense_ars`, `expense_usd`.
- Window is current UTC calendar month by `occurred_at`. Transfers are excluded.
- Conversion uses each transaction's stored rate, rounds money half-up to two decimals, and remains
  stable after account rate-type changes. Legacy transactions without a stored rate use the account's
  current rate type and normal exchange-rate cache fallback.

## Transfers
- `POST /api/transfers`
  - Body: `source_account_id`, `destination_account_id`, `source_amount`, optional `rate_override`, optional `description`.
- `PATCH /api/transfers/{transfer_id}`
  - Updates transfer and recalculates both balances atomically.
  - Body: optional `source_account_id`, `destination_account_id`, `source_amount`,
    `rate_override`, `description`. For cross-currency updates, omit `rate_override` to
    recalculate with destination account rate type; send a positive override to use it.
- `DELETE /api/transfers/{transfer_id}`
  - Deletes transfer and reverses both balance effects atomically.

Cross-currency transfers use destination account `rate_type` unless `rate_override` is provided.

## Net Worth History
- History starts with current active-account balances, reverses current-month activity, then reapplies
  activity day by day. A backdated transaction changes every point from its `occurred_at` date onward.
- History uses current account rate types and normal exchange-rate cache/provider fallback. It is a
  current reconstruction, so editing or deleting historical activity updates prior points.
- Transfers use their immutable `created_at` until transfer effective dates are supported.

## Budgets
- `GET /api/budgets`
- `POST /api/budgets`
  - Body: `category_id`, positive `amount`, `currency` (`ARS` or `USD`).
  - One budget exists per user and expense category. System categories are allowed.
- `PATCH /api/budgets/{budget_id}`
- `DELETE /api/budgets/{budget_id}`
- `GET /api/budgets/month-summary`
  - Returns current UTC-month spending by each budget's category, `remaining`, `percentage`, and
    `on_track`, `at_limit`, or `over_budget` status.
- All matching expense transactions count by `occurred_at`. Cross-currency amounts convert through
  each transaction's stored rate. Legacy transactions without one use current account-rate lookup.
  - Balance adjustments never count toward budget spending.

## Chat Pipeline
- `POST /api/chat/parse-message`
  - Body: `message`.
  - Returns confirm-ready draft.
  - Does not write to database.
- `POST /api/chat/confirm`
  - Body: `draft` returned by parse endpoint, optionally edited by client.
  - Creates transaction or transfer after revalidation.

## Activity Feeds
- `GET /api/activity?limit=50&cursor=<opaque>` (`limit` is 1-100)
- `GET /api/accounts/{account_id}/activity?limit=50&cursor=<opaque>` (`limit` is 1-100)

Feed response:

```json
{
  "items": [],
  "next_cursor": null
}
```

Cursor is opaque base64 JSON containing `created_at`, `kind`, and `id`. Clients should not parse it.
Feeds sort by `created_at`, `kind`, then `id`, all descending. A `next_cursor` continues strictly
after the last item in that order and is omitted only when no further matching activity exists.

Activity item `kind` values:
- `transaction`
- `transfer`
