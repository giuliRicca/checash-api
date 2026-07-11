from uuid import uuid4

import httpx

from tests.helpers import auth_headers, create_account, get_misc_category_id


async def test_register_login_and_me(client: httpx.AsyncClient) -> None:
    email = f"user-{uuid4()}@example.com"
    register = await client.post(
        "/api/auth/register",
        json={"email": email.upper(), "password": "password123"},
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]

    login = await client.post(
        "/api/auth/login",
        json={"email": email.lower(), "password": "password123"},
    )
    assert login.status_code == 200, login.text

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email.lower()
    assert me.json()["default_category_id"] is not None


async def test_category_slug_collision_and_delete_if_used(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    collision = await client.post("/api/categories", headers=headers, json={"name": "Groceries"})
    assert collision.status_code == 409, collision.text

    custom = await client.post("/api/categories", headers=headers, json={"name": "Books"})
    assert custom.status_code == 201, custom.text
    category_id = custom.json()["id"]

    account = await create_account(
        client, headers, name="Wallet", currency="ARS", opening_balance="100.00"
    )
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
    assert transaction.status_code == 201, transaction.text

    delete_used = await client.delete(f"/api/categories/{category_id}", headers=headers)
    assert delete_used.status_code == 409, delete_used.text


async def test_account_archive_blocks_new_transaction(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Archive Wallet", currency="ARS", opening_balance="50.00"
    )

    archive = await client.post(f"/api/accounts/{account['id']}/archive", headers=headers)
    assert archive.status_code == 200, archive.text
    assert archive.json()["warnings"] == ["archived_account_has_non_zero_balance"]

    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "5.00",
            "type": "expense",
        },
    )
    assert transaction.status_code == 409, transaction.text
