from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from app.db.session import AsyncSessionMaker
from app.models.enums import RateProvider, RateType
from app.models.exchange_rate import ExchangeRate
from tests.helpers import auth_headers, create_account, get_category_id, get_misc_category_id


async def seed_exchange_rate(rate_type: RateType, value: str) -> None:
    async with AsyncSessionMaker() as session:
        session.add(
            ExchangeRate(
                provider=RateProvider.DOLARAPI,
                rate_type=rate_type,
                value=Decimal(value),
                fetched_at=datetime.now(UTC),
                effective_date=date.today(),
            )
        )
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
