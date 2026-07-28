from datetime import UTC, datetime

import httpx
from sqlalchemy import update

from app.db.session import AsyncSessionMaker
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from tests.helpers import auth_headers, create_account, get_misc_category_id


async def create_transaction(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    account_id: str,
    category_id: str,
    amount: str,
) -> dict:
    response = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": amount,
            "type": "expense",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_transfer(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    source_account_id: str,
    destination_account_id: str,
) -> dict:
    response = await client.post(
        "/api/transfers",
        headers=headers,
        json={
            "source_account_id": source_account_id,
            "destination_account_id": destination_account_id,
            "source_amount": "1.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def get_all_pages(
    client: httpx.AsyncClient, headers: dict[str, str], url: str, limit: int
) -> tuple[list[dict], int]:
    cursor = None
    items: list[dict] = []
    pages = 0
    while True:
        params: dict[str, int | str] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get(url, headers=headers, params=params)
        assert response.status_code == 200, response.text
        page = response.json()
        items.extend(page["items"])
        pages += 1
        cursor = page["next_cursor"]
        if cursor is None:
            return items, pages


async def test_global_activity_cursor_paginates_past_source_lookahead(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    source = await create_account(
        client, headers, name="Source", currency="ARS", opening_balance="100.00"
    )
    destination = await create_account(
        client, headers, name="Destination", currency="ARS", opening_balance="0.00"
    )
    transfer = await create_transfer(client, headers, source["id"], destination["id"])
    transactions = [
        await create_transaction(client, headers, source["id"], category_id, f"{amount}.00")
        for amount in range(1, 7)
    ]

    items, pages = await get_all_pages(client, headers, "/api/activity", limit=2)

    assert pages == 4
    assert {(item["kind"], item["id"]) for item in items} == {
        *(("transaction", transaction["id"]) for transaction in transactions),
        ("transfer", transfer["id"]),
    }
    assert len(items) == len({item["id"] for item in items})


async def test_account_activity_cursor_paginates_mixed_types_to_exhaustion(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    source = await create_account(
        client, headers, name="Source", currency="ARS", opening_balance="100.00"
    )
    destination = await create_account(
        client, headers, name="Destination", currency="ARS", opening_balance="0.00"
    )
    transfer = await create_transfer(client, headers, source["id"], destination["id"])
    transactions = [
        await create_transaction(client, headers, source["id"], category_id, f"{amount}.00")
        for amount in range(1, 7)
    ]

    items, pages = await get_all_pages(
        client, headers, f"/api/accounts/{source['id']}/activity", limit=2
    )

    assert pages == 4
    assert [item["kind"] for item in items].count("transfer") == 1
    assert {item["id"] for item in items} == {
        transfer["id"],
        *(item["id"] for item in transactions),
    }


async def test_activity_cursor_orders_equal_timestamps_deterministically(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    source = await create_account(
        client, headers, name="Source", currency="ARS", opening_balance="100.00"
    )
    destination = await create_account(
        client, headers, name="Destination", currency="ARS", opening_balance="0.00"
    )
    transfers = [
        await create_transfer(client, headers, source["id"], destination["id"]) for _ in range(2)
    ]
    transactions = [
        await create_transaction(client, headers, source["id"], category_id, f"{amount}.00")
        for amount in range(1, 3)
    ]
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    async with AsyncSessionMaker() as session:
        await session.execute(
            update(Transaction)
            .where(Transaction.id.in_([item["id"] for item in transactions]))
            .values(created_at=created_at)
        )
        await session.execute(
            update(Transfer)
            .where(Transfer.id.in_([item["id"] for item in transfers]))
            .values(created_at=created_at)
        )
        await session.commit()

    items, pages = await get_all_pages(client, headers, "/api/activity", limit=1)

    assert pages == 4
    assert [(item["kind"], item["id"]) for item in items] == [
        (item["kind"], item["id"])
        for item in sorted(
            items, key=lambda item: (item["created_at"], item["kind"], item["id"]), reverse=True
        )
    ]


async def test_activity_rejects_invalid_cursor(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)

    response = await client.get("/api/activity?cursor=not-base64", headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid cursor"
