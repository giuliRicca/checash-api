from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.db.session import AsyncSessionMaker
from app.models.account import Account
from app.models.enums import RateProvider, RateType
from app.models.exchange_rate import ExchangeRate
from tests.helpers import auth_headers, create_account, get_category_id, get_misc_category_id


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


async def test_transaction_month_summary_uses_account_specific_latest_rates(
    client: httpx.AsyncClient,
) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    await seed_exchange_rate(RateType.MEP, "1200.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    income_category_id = await get_category_id(client, headers, "salary")
    ars_account = await create_account(
        client,
        headers,
        name="ARS Cash",
        currency="ARS",
        opening_balance="0.00",
        rate_type="blue",
    )
    usd_account = await create_account(
        client,
        headers,
        name="USD Bank",
        currency="USD",
        opening_balance="100.00",
        rate_type="mep",
    )

    income = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": ars_account["id"],
            "category_id": income_category_id,
            "amount": "100.00",
            "type": "income",
        },
    )
    assert income.status_code == 201, income.text
    expense = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": usd_account["id"],
            "category_id": category_id,
            "amount": "10.00",
            "type": "expense",
        },
    )
    assert expense.status_code == 201, expense.text

    summary = await client.get("/api/transactions/month-summary", headers=headers)

    assert summary.status_code == 200, summary.text
    assert summary.json()["income_ars"] == "100.00"
    assert summary.json()["income_usd"] == "0.10"
    assert summary.json()["expense_ars"] == "12000.00"
    assert summary.json()["expense_usd"] == "10.00"


async def test_transaction_month_summary_returns_zeroes_without_transactions(
    client: httpx.AsyncClient,
) -> None:
    headers = await auth_headers(client)

    summary = await client.get("/api/transactions/month-summary", headers=headers)

    assert summary.status_code == 200, summary.text
    assert summary.json()["income_ars"] == "0.00"
    assert summary.json()["income_usd"] == "0.00"
    assert summary.json()["expense_ars"] == "0.00"
    assert summary.json()["expense_usd"] == "0.00"


async def test_net_worth_history_reconstructs_current_balances(client: httpx.AsyncClient) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client,
        headers,
        name="Tracked cash",
        currency="ARS",
        opening_balance="100.00",
    )

    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "30.00",
            "type": "expense",
        },
    )
    assert transaction.status_code == 201, transaction.text

    history = await client.get("/api/accounts/net-worth/history", headers=headers)

    assert history.status_code == 200, history.text
    assert history.json()["points"][-1]["total_ars"] == "70.00"
    assert history.json()["points"][-1]["total_usd"] == "0.07"


async def test_net_worth_history_applies_backdated_transaction_from_its_effective_date(
    client: httpx.AsyncClient,
) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    headers = await auth_headers(client)
    category_id = await get_misc_category_id(client, headers)
    account = await create_account(
        client,
        headers,
        name="Backdated cash",
        currency="ARS",
        opening_balance="100.00",
    )
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    occurred_at = max(month_start + timedelta(days=1), now - timedelta(days=2))
    async with AsyncSessionMaker() as session:
        stored_account = await session.get(Account, account["id"])
        assert stored_account is not None
        stored_account.created_at = occurred_at - timedelta(days=1)
        await session.commit()

    transaction = await client.post(
        "/api/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category_id,
            "amount": "30.00",
            "type": "expense",
            "occurred_at": occurred_at.isoformat(),
        },
    )
    assert transaction.status_code == 201, transaction.text

    history = await client.get("/api/accounts/net-worth/history", headers=headers)

    assert history.status_code == 200, history.text
    points = {point["date"]: point for point in history.json()["points"]}
    assert points[(occurred_at - timedelta(days=1)).date().isoformat()]["total_ars"] == "100.00"
    assert points[occurred_at.date().isoformat()]["total_ars"] == "70.00"


async def test_net_worth_history_is_user_scoped(client: httpx.AsyncClient) -> None:
    await seed_exchange_rate(RateType.BLUE, "1000.000000")
    first_headers = await auth_headers(client)
    await create_account(
        client,
        first_headers,
        name="Tracked cash",
        currency="ARS",
        opening_balance="100.00",
    )
    second_headers = await auth_headers(client)

    history = await client.get("/api/accounts/net-worth/history", headers=second_headers)

    assert history.status_code == 200, history.text
    assert history.json()["points"] == []
