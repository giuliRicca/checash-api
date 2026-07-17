from uuid import uuid4

import httpx


async def auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    email = f"test-{uuid4()}@example.com"
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def get_misc_category_id(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    return await get_category_id(client, headers, "miscellaneous")


async def get_category_id(client: httpx.AsyncClient, headers: dict[str, str], slug: str) -> str:
    response = await client.get("/api/categories", headers=headers)
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json() if item["slug"] == slug)


async def create_account(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    currency: str,
    opening_balance: str,
    rate_type: str = "blue",
) -> dict:
    response = await client.post(
        "/api/accounts",
        headers=headers,
        json={
            "name": name,
            "currency": currency,
            "opening_balance": opening_balance,
            "rate_type": rate_type,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
