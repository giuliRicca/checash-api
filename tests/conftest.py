import os
from collections.abc import AsyncGenerator

import httpx
import pytest
from alembic.config import Config
from dotenv import load_dotenv

from alembic import command

load_dotenv()

test_database_url = os.environ.get("TEST_DATABASE_URL")
if not test_database_url:
    raise RuntimeError("TEST_DATABASE_URL is required for tests")
os.environ["DATABASE_URL"] = test_database_url


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
