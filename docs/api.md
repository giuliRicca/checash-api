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

## Categories
- `GET /api/categories`
- `POST /api/categories`
  - Body: `name`.
- `PATCH /api/categories/{category_id}`
  - Body: `name`.
- `DELETE /api/categories/{category_id}`
  - Deletes only user-owned unused categories.

System categories are global, immutable, and visible to all users.

## Accounts
- `POST /api/accounts`
  - Body: `name`, `currency`, `opening_balance`, `rate_type`.
- `GET /api/accounts?include_archived=false`
- `GET /api/accounts/{account_id}`
- `PATCH /api/accounts/{account_id}`
  - Body: optional `name`, optional `rate_type`.
- `POST /api/accounts/{account_id}/archive`
  - Archives account. Non-zero balances return warning metadata.
- `GET /api/accounts/net-worth?include_archived=false`
  - Returns symmetric totals in ARS and USD.

Account currency and balance are not directly editable after creation.

## Transactions
- `POST /api/transactions`
  - Creates expense or income.
  - Body: `account_id`, `category_id`, `amount`, `type`, optional `description`.
- `PATCH /api/transactions/{transaction_id}`
  - Updates transaction and recalculates balance atomically.
- `DELETE /api/transactions/{transaction_id}`
  - Deletes transaction and reverses balance effect atomically.

Transaction `type` values: `expense`, `income`.

## Transfers
- `POST /api/transfers`
  - Body: `source_account_id`, `destination_account_id`, `source_amount`, optional `rate_override`, optional `description`.
- `PATCH /api/transfers/{transfer_id}`
  - Updates transfer and recalculates both balances atomically.
- `DELETE /api/transfers/{transfer_id}`
  - Deletes transfer and reverses both balance effects atomically.

Cross-currency transfers use destination account `rate_type` unless `rate_override` is provided.

## Chat Pipeline
- `POST /api/chat/parse-message`
  - Body: `message`.
  - Returns confirm-ready draft.
  - Does not write to database.
- `POST /api/chat/confirm`
  - Body: `draft` returned by parse endpoint, optionally edited by client.
  - Creates transaction or transfer after revalidation.

## Activity Feeds
- `GET /api/activity?limit=50&cursor=<opaque>`
- `GET /api/accounts/{account_id}/activity?limit=50&cursor=<opaque>`

Feed response:

```json
{
  "items": [],
  "next_cursor": null
}
```

Cursor is opaque base64 JSON containing `created_at`, `kind`, and `id`. Clients should not parse it.

Activity item `kind` values:
- `transaction`
- `transfer`
