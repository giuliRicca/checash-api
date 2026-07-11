from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import RateProvider, RateType
from app.models.exchange_rate import ExchangeRate
from app.schemas.common import quantize_rate

RATE_PATHS = {
    RateType.BLUE: "dolares/blue",
    RateType.MEP: "dolares/bolsa",
    RateType.TARJETA: "dolares/tarjeta",
}


async def get_exchange_rate(session: AsyncSession, rate_type: RateType) -> Decimal:
    latest = await get_latest_cached_rate(session, rate_type)
    if latest is not None and not is_stale(latest.fetched_at):
        return latest.value

    try:
        return await fetch_and_cache_rate(session, rate_type)
    except httpx.HTTPError as exc:
        if latest is not None:
            return latest.value
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exchange rate provider unavailable and no cached rate exists",
        ) from exc


async def get_latest_cached_rate(session: AsyncSession, rate_type: RateType) -> ExchangeRate | None:
    return await session.scalar(
        select(ExchangeRate)
        .where(ExchangeRate.provider == RateProvider.DOLARAPI, ExchangeRate.rate_type == rate_type)
        .order_by(ExchangeRate.fetched_at.desc())
        .limit(1)
    )


def is_stale(fetched_at: datetime) -> bool:
    settings = get_settings()
    return fetched_at <= datetime.now(UTC) - timedelta(seconds=settings.exchange_rate_ttl_seconds)


async def fetch_and_cache_rate(session: AsyncSession, rate_type: RateType) -> Decimal:
    settings = get_settings()
    path = RATE_PATHS[rate_type]
    async with httpx.AsyncClient(
        base_url=settings.exchange_rate_provider_base_url, timeout=10
    ) as client:
        response = await client.get(path)
        response.raise_for_status()
        payload = response.json()

    compra = Decimal(str(payload["compra"]))
    venta = Decimal(str(payload["venta"]))
    value = quantize_rate((compra + venta) / Decimal("2"))
    fetched_at = datetime.now(UTC)
    effective_date = parse_effective_date(payload.get("fechaActualizacion"), fetched_at)
    stmt = insert(ExchangeRate).values(
        provider=RateProvider.DOLARAPI,
        rate_type=rate_type,
        value=value,
        fetched_at=fetched_at,
        effective_date=effective_date,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["provider", "rate_type", "effective_date"],
        set_={"value": value, "fetched_at": fetched_at},
    )
    await session.execute(stmt)
    await session.commit()
    return value


def parse_effective_date(value: str | None, fallback: datetime) -> date:
    if value is None:
        return fallback.date()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return fallback.date()
