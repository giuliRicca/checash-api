from datetime import UTC, datetime, timedelta

import httpx

from tests.helpers import auth_headers, create_account, get_misc_category_id


async def test_budget_uses_transaction_occurred_at(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Cash", currency="ARS", opening_balance="1000.00"
    )
    budget = await client.post(
        "/api/budgets",
        headers=headers,
        json={"category_id": category_id, "amount": "100.00", "currency": "ARS"},
    )
    assert budget.status_code == 201, budget.text
    occurred_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "25.00",
            "type": "expense",
            "occurred_at": occurred_at,
        },
    )
    assert transaction.status_code == 201, transaction.text
    assert datetime.fromisoformat(transaction.json()["occurred_at"]) == datetime.fromisoformat(
        occurred_at
    )
    summary = await client.get("/api/budgets/month-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()[0]["spent"] == "25.00"
    assert summary.json()[0]["remaining"] == "75.00"


async def test_transaction_rejects_future_occurred_at(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Cash", currency="ARS", opening_balance="100.00"
    )
    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "10.00",
            "type": "expense",
            "occurred_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 422, response.text
