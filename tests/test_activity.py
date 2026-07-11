import httpx

from tests.helpers import auth_headers, create_account, get_misc_category_id


async def test_activity_and_account_activity_cursor_pagination(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Feed", currency="ARS", opening_balance="100.00"
    )
    for amount in ["1.00", "2.00"]:
        response = await client.post(
            "/api/transactions",
            headers=headers,
            json={
                "account_id": account["id"],
                "category_id": category_id,
                "amount": amount,
                "type": "expense",
            },
        )
        assert response.status_code == 201, response.text

    first_page = await client.get("/api/activity?limit=1", headers=headers)
    assert first_page.status_code == 200, first_page.text
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["next_cursor"] is not None

    second_page = await client.get(
        f"/api/activity?limit=1&cursor={first_page.json()['next_cursor']}", headers=headers
    )
    assert second_page.status_code == 200, second_page.text
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["id"] != first_page.json()["items"][0]["id"]

    account_feed = await client.get(f"/api/accounts/{account['id']}/activity", headers=headers)
    assert account_feed.status_code == 200, account_feed.text
    assert len(account_feed.json()["items"]) == 2
