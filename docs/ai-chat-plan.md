# AI-Enhanced Chat Plan

Status: Phase 1 complete. Next: Phase 2A model benchmark.

Canonical handoff document for AI chat work. Read this file at start of each session.

## Current Chat

Chat currently parses one movement with deterministic rules, returns an editable draft, and writes
only after explicit confirmation. It does not call a model or retain conversation history.

## Product Decisions

| Topic | Decision |
| --- | --- |
| v1 scope | Log one income, expense, transfer, or exchange per message. History Q&A later. |
| Learning | Opt-in, per-user derived merchant/category and account aliases only. No raw-prompt training, cross-user data, or fine-tuning. |
| Model | Hosted-first provider adapter; benchmark local model before beta. |
| Cost | Private beta, no paid API. Hard quotas; manual fallback if free tier fails. |
| Provider privacy | API terms must exclude training on submitted data. |
| Model context | Prompt, account names/currencies, category names, timezone, aliases. No balances, identity, history, or database IDs. |
| Languages | Spanish and English. |
| Ambiguity | Clarify critical fields one at a time: amount, type, source, transfer destination. |
| Categories | Existing categories only. AI cannot create categories. |
| Dates | Common past dates, resolved using user profile IANA timezone. |
| Transfers | Included. Backend exchange rate is authoritative; explicit user rate may override. |
| Failure | Invalid/unavailable AI returns blank manual draft with original text; no regex fallback guessing. |
| Confirmation | Always explicit. Never let model write financial records. |

## Phase 1: Write Safety

Complete and deployed.

- Added temporary `chat_draft_sessions` table with owner, JSONB payload, status, source message,
  creation time, and 24-hour expiry.
- Parse now returns `{ id, expires_at, draft }` and persists pending drafts.
- Confirm now requires `{ draft_id, draft }` and validates amount, type, description, and fields.
- Confirmation claim is atomic and single-use. Unknown/foreign drafts return 404; expired/replayed
  drafts return 409. Failed validation/write rolls back claim.
- Transaction and transfer balance writes lock affected account rows. Transfers lock accounts in
  deterministic ID order.
- Expired drafts purge lazily on parse.
- Safety tests cover foreign/unknown, expiry/purge, invalid retry, duplicate, and concurrent confirm.

### Phase 1 Evidence

- Migration: `202608210001_add_chat_draft_sessions`
- Backend commit: `d0b2bb1`
- Frontend commit: `8ebc44e`
- Production Neon migration: successful, `202608210001` head
- Backend CI: successful at `d0b2bb1`
- Frontend CI: successful at `8ebc44e`
- Local backend verification: `32 passed`; frontend: `29 passed`, typecheck and lint pass

## Phase 2A: Model Benchmark

Do this before provider integration.

1. Define versioned strict parser output contract. Keep symbolic account/category choices; backend
   maps them to owned IDs and validates ownership.
2. Create bilingual benchmark dataset. Include normal income/expense/transfer, currencies, dates,
   Spanish accents/slang, ambiguous account/category, missing amount, multiple movements, malformed
   input, prompt injection, and unsupported requests.
3. Add evaluator for schema validity, critical-field accuracy, clarification behavior, latency, and
   token/cost estimate. Never log raw benchmark or user prompts in production telemetry.
4. Verify current hosted free-tier API terms exclude training on API data.
5. Compare eligible hosted models and one local baseline (for example Ollama) using same dataset,
   schema, and prompt.
6. Record provider decision, model version, prompt version, limits, failure behavior, and privacy
   terms in benchmark report.

### Acceptance Gate

- At least 95% critical-field accuracy.
- At least 99% schema-valid output.
- 100% clarification on tested critical ambiguity.

## Phase 2B: Parser Adapter

- Add provider-neutral async adapter behind backend service boundary.
- Enforce timeout, bounded retries, structured-output validation, quota, and kill switch.
- Send minimum context only. Keep API key server-side.
- Map model symbols to user-owned accounts/categories; reject unknown values.
- Return typed clarification action or draft.
- Keep mandatory review and atomic Phase 1 confirmation.

## Phase 3: Personalization

- Add opt-in setting with explanation, inspect, delete, reset, and disable controls.
- Learn only specific merchant/category and account aliases from confirmed corrections.
- Store derived mappings, counts, and timestamps; never store raw prompts in learning tables.

## Phase 4: Chat UX

- Render typed clarification choices.
- Restore pending drafts after reload.
- Show manual fallback state.
- Detect multi-movement input and ask user to split it.
- Add privacy and beta disclosure.

## Phase 5: Operations

- Server allowlist, global kill switch, per-user daily quota, timeout circuit breaker.
- Metadata-only telemetry: provider/model, prompt version, latency, tokens, status, corrected field
  names. Never prompt, response, or description content.

## Later: History Q&A

Separate read-only phase. Use validated, user-scoped query tools with citations to transactions.
Do not replay raw conversation context as authority.

## Next Session Checklist

- Read this file and inspect current `main` status.
- Start Phase 2A, item 1: define parser output contract.
- Do not add provider SDK or API key yet.
- Keep benchmark data versioned and synthetic/anonymized.
- Run backend Ruff/tests and frontend typecheck/tests before claiming completion.
- Update this file with decisions, evidence, and next unfinished item.
