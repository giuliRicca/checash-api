from decimal import Decimal

from app.db.session import AsyncSessionMaker
from app.models.enums import RateType
from app.services import exchange_rates


class MockDolarApiResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return [
            {
                "casa": "oficial",
                "compra": 1000,
                "venta": 1100,
                "fechaActualizacion": "2026-07-14T12:00:00.000Z",
            },
            {
                "casa": "cripto",
                "compra": 1200,
                "venta": 1300,
                "fechaActualizacion": "2026-07-14T12:00:00.000Z",
            },
        ]


class MockDolarApiClient:
    requested_paths: list[str] = []

    def __init__(self, base_url: str, timeout: int) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def __aenter__(self) -> "MockDolarApiClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def get(self, path: str) -> MockDolarApiResponse:
        self.requested_paths.append(path)
        return MockDolarApiResponse()


async def test_fetch_and_cache_rate_maps_dolarapi_list_response(monkeypatch) -> None:
    MockDolarApiClient.requested_paths = []
    monkeypatch.setattr(exchange_rates.httpx, "AsyncClient", MockDolarApiClient)

    async with AsyncSessionMaker() as session:
        oficial = await exchange_rates.fetch_and_cache_rate(session, RateType.OFICIAL)
        crypto = await exchange_rates.fetch_and_cache_rate(session, RateType.CRYPTO)

    assert oficial == Decimal("1050.000000")
    assert crypto == Decimal("1250.000000")
    assert MockDolarApiClient.requested_paths == ["dolares", "dolares"]
