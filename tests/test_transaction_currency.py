from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.enums import RateProvider, RateType
from app.models.exchange_rate import ExchangeRate
from tests.helpers import auth_headers, create_account, get_misc_category_id


async def seed_exchange_rate(rate_type: RateType, value: str) -> None:
    async with AsyncSessionMaker() as session:
        existing = await session.scalar(
            select(ExchangeRate).where(
                ExchangeRate.provider == RateProvider.DOLARAPI,
                ExchangeRate.rate_type == rate_type,
                ExchangeRate.effective_date == date.today(),
            )
        )
        if existing is None:
            session.add(
                ExchangeRate(
                    provider=RateProvider.DOLARAPI,
                    rate_type=rate_type,
                    value=Decimal(value),
                    fetched_at=datetime.now(UTC),
                    effective_date=date.today(),
                )
            )
        else:
            existing.value = Decimal(value)
            existing.fetched_at = datetime.now(UTC)
        await session.commit()


async def test_foreign_currency_transaction_uses_persisted_account_amount(
    client: httpx.AsyncClient,
) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    await seed_exchange_rate(RateType.MEP, "1200.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    ars = await create_account(
        client, headers, name="ARS", currency="ARS", opening_balance="20000.00", rate_type="blue"
    )
    usd = await create_account(
        client, headers, name="USD", currency="USD", opening_balance="100.00", rate_type="mep"
    )

    created = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": ars["id"],
            "category_id": category_id,
            "amount": "10.00",
            "currency": "USD",
            "type": "expense",
        },
    )

    assert created.status_code == 201, created.text
    assert created.json()["currency"] == "USD"
    assert created.json()["account_amount"] == "10000.00"
    assert created.json()["rate_used"] == "1000.000000"
    assert (await client.get(f"/api/accounts/{ars['id']}", headers=headers)).json()[
        "balance"
    ] == "10000.00"
    history = await client.get("/api/accounts/net-worth/history", headers=headers)
    activity = await client.get("/api/activity", headers=headers)
    assert history.status_code == 200, history.text
    assert history.json()["points"][-1]["total_ars"] == "130000.00"
    assert activity.status_code == 200, activity.text
    assert activity.json()["items"][0]["account_amount"] == "10000.00"
    assert activity.json()["items"][0]["account_currency"] == "ARS"

    updated = await client.patch(
        f"/api/transactions/{created.json()['id']}", headers=headers, json={"amount": "12.00"}
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["account_amount"] == "12000.00"
    assert (await client.get(f"/api/accounts/{ars['id']}", headers=headers)).json()[
        "balance"
    ] == "8000.00"

    moved = await client.patch(
        f"/api/transactions/{created.json()['id']}",
        headers=headers,
        json={"account_id": usd["id"]},
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["account_amount"] == "12.00"
    assert moved.json()["rate_used"] == "1200.000000"
    assert (await client.get(f"/api/accounts/{ars['id']}", headers=headers)).json()[
        "balance"
    ] == "20000.00"
    assert (await client.get(f"/api/accounts/{usd['id']}", headers=headers)).json()[
        "balance"
    ] == "88.00"

    deleted = await client.delete(f"/api/transactions/{created.json()['id']}", headers=headers)

    assert deleted.status_code == 204, deleted.text
    assert (await client.get(f"/api/accounts/{usd['id']}", headers=headers)).json()[
        "balance"
    ] == "100.00"


async def test_reports_keep_transaction_rate_after_account_rate_type_changes(
    client: httpx.AsyncClient,
) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    await seed_exchange_rate(RateType.MEP, "1200.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="ARS", currency="ARS", opening_balance="20000.00", rate_type="blue"
    )
    budget = await client.post(
        "/api/budgets",
        headers=headers,
        json={"category_id": category_id, "amount": "20.00", "currency": "USD"},
    )
    assert budget.status_code == 201, budget.text
    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "12000.00",
            "currency": "ARS",
            "type": "expense",
        },
    )
    assert transaction.status_code == 201, transaction.text

    changed_account = await client.patch(
        f"/api/accounts/{account['id']}", headers=headers, json={"rate_type": "mep"}
    )
    assert changed_account.status_code == 200, changed_account.text

    summary = await client.get("/api/transactions/month-summary", headers=headers)
    budget_summary = await client.get("/api/budgets/month-summary", headers=headers)

    assert summary.status_code == 200, summary.text
    assert summary.json()["expense_usd"] == "12.00"
    assert budget_summary.status_code == 200, budget_summary.text
    assert budget_summary.json()[0]["spent"] == "12.00"


async def test_transaction_currency_update_refreshes_rate_and_account_impact(
    client: httpx.AsyncClient,
) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="ARS", currency="ARS", opening_balance="20000.00", rate_type="blue"
    )
    created = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "12000.00",
            "currency": "ARS",
            "type": "expense",
        },
    )
    assert created.status_code == 201, created.text

    updated = await client.patch(
        f"/api/transactions/{created.json()['id']}",
        headers=headers,
        json={"amount": "10.00", "currency": "USD"},
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["currency"] == "USD"
    assert updated.json()["rate_used"] == "1000.000000"
    assert updated.json()["account_amount"] == "10000.00"
    assert (await client.get(f"/api/accounts/{account['id']}", headers=headers)).json()[
        "balance"
    ] == "10000.00"


async def test_chat_confirmation_keeps_draft_currency(client: httpx.AsyncClient) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client, headers, name="ARS", currency="ARS", opening_balance="20000.00"
    )
    await client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"default_account_id": account["id"], "default_category_id": category_id},
    )
    parsed = await client.post(
        "/api/chat/parse-message", headers=headers, json={"message": "Gaste 10 usd"}
    )
    assert parsed.status_code == 200, parsed.text
    assert parsed.json()["currency"] == "USD"

    confirmed = await client.post(
        "/api/chat/confirm", headers=headers, json={"draft": parsed.json()}
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["currency"] == "USD"
    assert confirmed.json()["account_amount"] == "10000.00"
