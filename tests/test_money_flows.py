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
