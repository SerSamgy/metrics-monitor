import asyncpg
import pytest
import pytest_asyncio

from metrics_monitor.db_operations import create_table
from metrics_monitor.settings import Settings


@pytest.fixture(scope="session")
def settings():
    return Settings(_env_file=".env.test", _env_file_encoding="utf-8").model_dump()  # type: ignore


@pytest_asyncio.fixture
async def db_pool(settings):
    async with asyncpg.create_pool(
        settings["postgres_dsn"],
        min_size=int(settings["pool_min_size"]),
        max_size=int(settings["pool_max_size"]),
    ) as pool:
        yield pool


@pytest_asyncio.fixture
async def db_conn(db_pool):
    async with db_pool.acquire() as conn:
        await create_table(conn)

        yield conn

        await conn.execute("DROP TABLE website_metrics")
