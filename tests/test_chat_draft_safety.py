import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from app.models.chat_draft import ChatDraftSession
from sqlalchemy import select
from sqlalchemy import update as sa_update

from app.db.session import AsyncSessionMaker
from tests.helpers import auth_headers, create_account, get_misc_category_id


async def _parse(client: httpx.AsyncClient, headers: dict[str, str], message: str) -> dict:
    response = await client.post(
        "/api/chat/parse-message", headers=headers, json={"message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _backdate_draft(draft_id: str) -> None:
    async with AsyncSessionMaker() as session:
        await session.execute(
            sa_update(ChatDraftSession)
            .where(ChatDraftSession.id == uuid.UUID(draft_id))
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()


async def _draft_ids_for_user(user_id: str) -> set[str]:
    async with AsyncSessionMaker() as session:
        rows = list(
            await session.scalars(
                select(ChatDraftSession.id).where(
                    ChatDraftSession.user_id == uuid.UUID(user_id)
                )
            )
        )
    return {str(row) for row in rows}


async def test_confirm_rejects_unknown_and_foreign_drafts(client: httpx.AsyncClient) -> None:
    owner_headers = await auth_headers(client)
    other_headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, owner_headers)
    account = await create_account(
        client, owner_headers, name="Owner ARS", currency="ARS", opening_balance="100.00"
    )
    await client.patch(
        "/api/users/me/preferences",
        headers=owner_headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )

    parsed = await _parse(client, owner_headers, "Gaste 10 en el kiosco")

    unknown = await client.post(
        "/api/chat/confirm",
        headers=owner_headers,
        json={"draft_id": str(uuid.uuid4()), "draft": parsed["draft"]},
    )
    assert unknown.status_code == 404, unknown.text

    foreign = await client.post(
        "/api/chat/confirm",
        headers=other_headers,
        json={"draft_id": parsed["id"], "draft": parsed["draft"]},
    )
    assert foreign.status_code == 404, foreign.text

    confirmed = await client.post(
        "/api/chat/confirm",
        headers=owner_headers,
        json={"draft_id": parsed["id"], "draft": parsed["draft"]},
    )
    assert confirmed.status_code == 200, confirmed.text


async def test_expired_draft_cannot_confirm_and_is_purged(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Expiry ARS", currency="ARS", opening_balance="100.00"
    )
    prefs = await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )
    assert prefs.status_code == 200, prefs.text
    me = await client.get("/api/auth/me", headers=headers)
    user_id = me.json()["id"]

    parsed = await _parse(client, headers, "Gaste 5 en el super")

    await _backdate_draft(parsed["id"])

    expired = await client.post(
        "/api/chat/confirm",
        headers=headers,
        json={"draft_id": parsed["id"], "draft": parsed["draft"]},
    )
    assert expired.status_code == 409, expired.text

    replacement = await _parse(client, headers, "Gaste 6 en el super")
    remaining_ids = await _draft_ids_for_user(user_id)
    assert remaining_ids == {replacement["id"]}


async def test_invalid_confirm_payload_keeps_draft_reusable(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Retry ARS", currency="ARS", opening_balance="100.00"
    )
    await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )

    parsed = await _parse(client, headers, "Gaste 20 en el super")

    bad_type = dict(parsed["draft"], transaction_type="bogus")
    rejected_type = await client.post(
        "/api/chat/confirm",
        headers=headers,
        json={"draft_id": parsed["id"], "draft": bad_type},
    )
    assert rejected_type.status_code == 422, rejected_type.text

    long_description = dict(parsed["draft"], description="x" * 501)
    rejected_description = await client.post(
        "/api/chat/confirm",
        headers=headers,
        json={"draft_id": parsed["id"], "draft": long_description},
    )
    assert rejected_description.status_code == 422, rejected_description.text

    edited = dict(parsed["draft"], amount="25.00")
    confirmed = await client.post(
        "/api/chat/confirm",
        headers=headers,
        json={"draft_id": parsed["id"], "draft": edited},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["amount"] == "25.00"

    account_after = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert account_after.json()["balance"] == "75.00"


async def test_concurrent_confirms_write_exactly_once(client: httpx.AsyncClient) -> None:
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="Race ARS", currency="ARS", opening_balance="200.00"
    )
    await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )

    parsed = await _parse(client, headers, "Gaste 50 en el super")
    payload = {"draft_id": parsed["id"], "draft": parsed["draft"]}

    results = await asyncio.gather(
        client.post("/api/chat/confirm", headers=headers, json=payload),
        client.post("/api/chat/confirm", headers=headers, json=payload),
    )
    statuses = sorted(result.status_code for result in results)
    assert statuses == [200, 409], [(r.status_code, r.text) for r in results]

    account_after = await client.get(f"/api/accounts/{account['id']}", headers=headers)
    assert account_after.json()["balance"] == "150.00"
