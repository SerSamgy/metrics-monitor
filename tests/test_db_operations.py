import random

import pytest

from metrics_monitor.db_operations import create_table, save_metrics
from metrics_monitor.models import WebsiteMetrics


@pytest.mark.asyncio
async def test_create_table(db_pool, fake_metrics):
    async with db_pool.acquire() as conn:
        await create_table(conn)

        result = await conn.execute(
            """INSERT INTO website_metrics (url, request_timestamp, response_time, status_code, pattern_found) 
            VALUES ($1, $2, $3, $4, $5)""",
            fake_metrics.url,
            fake_metrics.request_timestamp,
            fake_metrics.response_time,
            fake_metrics.status_code,
            fake_metrics.pattern_found,
        )
        assert result == "INSERT 0 1"

        await conn.execute("DROP TABLE website_metrics")


@pytest.mark.asyncio
async def test_save_metrics(db_conn, fake_metrics):
    await save_metrics(fake_metrics, db_conn)

    row = await db_conn.fetchrow("SELECT * FROM website_metrics")
    assert row["url"] == fake_metrics.url
    assert row["request_timestamp"] == fake_metrics.request_timestamp
    assert row["response_time"] == fake_metrics.response_time
    assert row["status_code"] == fake_metrics.status_code
    assert row["pattern_found"] == fake_metrics.pattern_found


@pytest.fixture
def fake_metrics(faker):
    return WebsiteMetrics(
        url=faker.url(),
        request_timestamp=faker.date_time_this_month(),
        response_time=faker.pyfloat(),
        status_code=random.choice([200, 404, 500]),
        pattern_found=faker.pybool(),
    )
