import httpx

from tests.helpers import auth_headers, create_account, get_category_id, get_misc_category_id


async def test_transaction_update_delete_balance_effects(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Cash", currency="ARS", opening_balance="100.00"
    )

    created = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "20.00",
            "type": "expense",
        },
    )
    assert created.status_code == 201, created.text

    updated = await client.patch(
        f"/api/transactions/{created.json()['id']}",
        headers=headers,
        json={"amount": "30.00"},
    )
    assert updated.status_code == 200, updated.text
    account_after_update = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert account_after_update.json()["balance"] == "70.00"

    deleted = await client.delete(f"/api/transactions/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    account_after_delete = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert account_after_delete.json()["balance"] == "100.00"


async def test_balance_adjustment_changes_balance_but_not_month_summary(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    account = await create_account(
        client, headers, name="Cash", currency="ARS", opening_balance="100.00"
    )

    adjustment = await client.post(
        f"/api/accounts/{account['id']}/adjustments",
        headers=headers,
        json={"target_balance": "135.50", "description": "Cash count"},
    )
    assert adjustment.status_code == 201, adjustment.text
    assert adjustment.json()["amount"] == "35.50"
    assert adjustment.json()["type"] == "income"
    assert adjustment.json()["is_adjustment"] is True

    account_after_adjustment = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert account_after_adjustment.json()["balance"] == "135.50"

    summary = await client.get("/api/transactions/month-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["income_ars"] == "0.00"
    assert summary.json()["expense_ars"] == "0.00"

    changed = await client.patch(
        f"/api/transactions/{adjustment.json()['id']}", headers=headers, json={"amount": "40.00"}
    )
    assert changed.status_code == 422, changed.text
    deleted = await client.delete(f"/api/transactions/{adjustment.json()['id']}", headers=headers)
    assert deleted.status_code == 422, deleted.text

    no_change = await client.post(
        f"/api/accounts/{account['id']}/adjustments",
        headers=headers,
        json={"target_balance": "135.50"},
    )
    assert no_change.status_code == 422, no_change.text


async def test_balance_adjustment_categories_cannot_be_used_normally(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    account = await create_account(
        client, headers, name="Cash", currency="ARS", opening_balance="100.00"
    )
    category_id = await get_category_id(client, headers, "balance-adjustment-expense")

    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "10.00",
            "type": "expense",
        },
    )
    assert transaction.status_code == 422, transaction.text


async def test_delete_account_removes_history_and_reverses_linked_transfers(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    source = await create_account(
        client, headers, name="Source", currency="ARS", opening_balance="100.00"
    )
    destination = await create_account(
        client, headers, name="Destination", currency="ARS", opening_balance="20.00"
    )
    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": source["id"],
            "category_id": category_id,
            "amount": "10.00",
            "type": "expense",
        },
    )
    assert transaction.status_code == 201, transaction.text
    transfer = await client.post(
        "/api/transfers",
        headers=headers,
        json={
            "source_account_id": source["id"],
            "destination_account_id": destination["id"],
            "source_amount": "30.00",
        },
    )
    assert transfer.status_code == 201, transfer.text
    preferences = await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": source["id"]},
    )
    assert preferences.status_code == 200, preferences.text

    deleted = await client.delete(f"/api/accounts/{source['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing = await client.get(f"/api/accounts/{source['id']}", headers=headers)
    assert missing.status_code == 404, missing.text
    destination_after = await client.get(f"/api/accounts/{destination['id']}", headers=headers)
    assert destination_after.json()["balance"] == "20.00"
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["default_account_id"] is None


async def test_cross_currency_transfer_with_manual_rate(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    usd = await create_account(
        client, headers, name="USD", currency="USD", opening_balance="100.00"
    )
    ars = await create_account(
        client, headers, name="ARS", currency="ARS", opening_balance="1000.00"
    )

    transfer = await client.post(
        "/api/transfers",
        headers=headers,
        json={
            "source_account_id": usd["id"],
            "destination_account_id": ars["id"],
            "source_amount": "10.00",
            "rate_override": "1000.00",
        },
    )
    assert transfer.status_code == 201, transfer.text
    assert transfer.json()["destination_amount"] == "10000.00"
    assert transfer.json()["rate_used"] == "1000.000000"

    usd_after = await client.get(f"/api/accounts/{usd['id']}", headers=headers)
    ars_after = await client.get(f"/api/accounts/{ars['id']}", headers=headers)
    assert usd_after.json()["balance"] == "90.00"
    assert ars_after.json()["balance"] == "11000.00"


async def test_chat_parse_does_not_write_and_confirm_writes(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Default ARS", currency="ARS", opening_balance="200.00"
    )
    prefs = await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )
    assert prefs.status_code == 200, prefs.text

    parsed = await client.post(
        "/api/chat/parse-message",
        headers=headers,
        json={"message": "Gaste 50 en el super"},
    )
    assert parsed.status_code == 200, parsed.text
    balance_after_parse = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert balance_after_parse.json()["balance"] == "200.00"

    confirmed = await client.post(
        "/api/chat/confirm",
        headers=headers,
        json={"draft": parsed.json()},
    )
    assert confirmed.status_code == 200, confirmed.text
    balance_after_confirm = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert balance_after_confirm.json()["balance"] == "150.00"


async def test_chat_income_uses_uncategorized_income_fallback(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    account = await create_account(
        client, headers, name="Income ARS", currency="ARS", opening_balance="0.00"
    )
    uncategorized_income_id = await get_category_id(client, headers, "uncategorized-income")
    await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"]},
    )

    parsed = await client.post(
        "/api/chat/parse-message", headers=headers, json={"message": "Cobre 100"}
    )
    assert parsed.status_code == 200, parsed.text
    assert parsed.json()["transaction_type"] == "income"
    assert parsed.json()["category_id"] == uncategorized_income_id
