import asyncio
import io
import json
import random
from datetime import datetime
from unittest.mock import AsyncMock, patch

import aiohttp
import asyncpg
import pytest
from freezegun import freeze_time

from metrics_monitor.errors import (
    ConfigDeserializationError,
    SettingsInitializationError,
)
from metrics_monitor.main import check_website_once, main, prepare_website_metrics
from metrics_monitor.models import MonitorParams


# Attribution: https://stackoverflow.com/a/59351425
class MockResponse:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


@freeze_time("2023-11-07 11:00:01")
@pytest.mark.asyncio
async def test_check_website_once_successful(fake_monitor_params, mocked_response, semaphore, db_pool, db_conn):
    with patch("metrics_monitor.main.aiohttp.ClientSession.get", return_value=mocked_response):
        await check_website_once(fake_monitor_params, db_pool, semaphore)

    row = await db_conn.fetchrow("SELECT * FROM website_metrics")
    assert row["url"] == fake_monitor_params.url
    assert row["request_timestamp"] == datetime(2023, 11, 7, 11, 0, 1)
    assert row["response_time"] == 0.0
    assert row["status_code"] == 200
    assert row["pattern_found"] is True


@pytest.mark.asyncio
async def test_check_website_once_clienterror(fake_monitor_params, semaphore, db_pool, db_conn):
    with patch(
        "metrics_monitor.main.aiohttp.ClientSession.get",
        side_effect=aiohttp.ClientError,
    ):
        await check_website_once(fake_monitor_params, db_pool, semaphore)

    row = await db_conn.fetchrow("SELECT * FROM website_metrics")
    assert row is None


@pytest.mark.asyncio
async def test_check_website_once_postgreserror(fake_monitor_params, semaphore, mocked_response, db_pool, db_conn):
    with patch("metrics_monitor.main.aiohttp.ClientSession.get", return_value=mocked_response), patch(
        "metrics_monitor.main.save_metrics",
        side_effect=asyncpg.FatalPostgresError("oops"),
    ):
        await check_website_once(fake_monitor_params, db_pool, semaphore)

    row = await db_conn.fetchrow("SELECT * FROM website_metrics")
    assert row is None


@pytest.mark.asyncio
async def test_check_website_once_exception(fake_monitor_params, semaphore, mocked_response, db_pool, db_conn):
    with patch("metrics_monitor.main.aiohttp.ClientSession.get", return_value=mocked_response), patch(
        "metrics_monitor.main.save_metrics",
        side_effect=Exception("oops"),
    ):
        await check_website_once(fake_monitor_params, db_pool, semaphore)

    row = await db_conn.fetchrow("SELECT * FROM website_metrics")
    assert row is None


@pytest.mark.parametrize(
    "regexp_pattern, response_body, expected_pattern_found",
    [
        (None, "Example", False),
        (r"Health: \d{2,3}%", "Health: 50%", True),
        (r"Health: \d{2,3}%", "Example", False),
    ],
)
@freeze_time("2023-11-07 11:00:01")
@pytest.mark.asyncio
async def test_prepare_website_metrics(regexp_pattern, response_body, expected_pattern_found, mocked_response, faker):
    url = faker.url()
    request_timestamp = datetime.now()
    mocked_response._text = response_body
    metrics = await prepare_website_metrics(mocked_response, request_timestamp, url, regexp_pattern)

    assert metrics.url == url
    assert metrics.request_timestamp == request_timestamp
    assert metrics.response_time == 0.0
    assert metrics.status_code == mocked_response.status
    assert metrics.pattern_found == expected_pattern_found


@pytest.mark.asyncio
async def test_main_settings_error(input_file_content):
    with patch("metrics_monitor.main.Settings", side_effect=ValueError("oops")), pytest.raises(
        SettingsInitializationError
    ):
        await main(input_file_content)


@pytest.mark.asyncio
async def test_main_config_deserialization_error():
    with pytest.raises(ConfigDeserializationError):
        await main(io.StringIO("not valid json"))


@pytest.mark.asyncio
async def test_main_successful(input_file_content):
    with patch("metrics_monitor.main.check_website", return_value=AsyncMock()) as mocked_check_website:
        await main(input_file_content)

    mocked_check_website.assert_awaited()


@pytest.fixture
def fake_monitor_params(faker):
    return MonitorParams(
        url=faker.url(),
        interval=random.randint(5, 300),
        regexp_pattern=r"Health: \d{2,3}%",
    )


@pytest.fixture
def semaphore(settings):
    return asyncio.Semaphore(int(settings["semaphore_max_concurrent"]))


@pytest.fixture
def mocked_response():
    return MockResponse("Health: 100%", 200)


@pytest.fixture
def input_file_content(fake_monitor_params):
    return io.StringIO(json.dumps([fake_monitor_params.model_dump()]))
