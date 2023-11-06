import argparse
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import TextIO

import aiohttp
import asyncpg

from metrics_monitor.db_operations import create_table, save_metrics
from metrics_monitor.models import MonitorParams, WebsiteMetrics
from metrics_monitor.settings import Settings


async def check_website(
    monitor_params: MonitorParams, pool: asyncpg.pool.Pool, sem: asyncio.Semaphore
):
    """
    Check the given website at a specified interval and log the response time, status code, and whether a given regular
    expression pattern was found in the response content.

    Args:
        monitor_params (MonitorParams): An object containing the monitoring parameters for the website.
        pool (asyncpg.pool.Pool): The connection pool to the database where website metrics will be stored.
        sem (asyncio.Semaphore): The semaphore to limit the number of concurrent database connections.

    Returns:
        None
    """

    while True:
        await asyncio.sleep(monitor_params.interval)

        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                async with session.get(monitor_params.url) as response:
                    metrics = await prepare_website_metrics(
                        response,
                        start_time,
                        monitor_params.url,
                        monitor_params.regexp_pattern,
                    )
                    logging.info(
                        f"{monitor_params.url} - response_time: {metrics.response_time} "
                        f"- status_code: {metrics.status_code} - pattern_found: {metrics.pattern_found}"
                    )

                    async with sem, pool.acquire() as conn:
                        await save_metrics(metrics, conn)
                    logging.info(f"Saved metrics to database: {metrics}.")
        except Exception as e:
            logging.error(f"Error checking {monitor_params.url}: {e}")


async def prepare_website_metrics(
    response: aiohttp.ClientResponse,
    start_time: datetime,
    url: str,
    regexp_pattern: str | None,
) -> WebsiteMetrics:
    """
    Extracts website metrics from an aiohttp response object.

    Args:
        response (aiohttp.ClientResponse): The response object to extract metrics from.
        start_time (datetime): The time the request was sent.
        url (str): The URL of the website being monitored.
        regexp_pattern (str): The regular expression pattern to search for in the response content.

    Returns:
        WebsiteMetrics: An object containing the extracted website metrics.
    """

    response_time = (datetime.now() - start_time).total_seconds()
    status_code = response.status
    content = await response.text()

    pattern_found = False
    if regexp_pattern:
        if re.search(regexp_pattern, content):
            pattern_found = True

    return WebsiteMetrics(
        url=url,
        request_timestamp=start_time,
        response_time=response_time,
        status_code=status_code,
        pattern_found=pattern_found,
    )


async def main(input_file: TextIO):
    """
    Asynchronously monitors website metrics by periodically sending HTTP requests to specified URLs and storing the
    response time, status code, and whether a specified pattern was found in the response. The monitoring parameters
    are read from a JSON file passed as an argument.

    Args:
        input_file (TextIO): A file-like object containing a JSON array of monitoring parameters. Each parameter is a
            JSON object with the following keys:
            - url (str): The URL to monitor
            - interval (int): The interval between requests in seconds
            - regexp_pattern (str | null): A regular expression pattern to search for in the response body

    Returns:
        None
    """

    settings = Settings().model_dump()

    async with asyncpg.create_pool(
        settings["postgres_dsn"],
        min_size=int(settings["pool_min_size"]),
        max_size=int(settings["pool_max_size"]),
    ) as pool:
        async with pool.acquire() as conn:
            await create_table(conn)

        sem = asyncio.Semaphore(int(settings["semaphore_max_concurrent"]))
        monitoring_args = json.load(input_file)
        tasks = [
            check_website(
                MonitorParams(
                    url=args["url"],
                    interval=args["interval"],
                    regexp_pattern=args.get("regexp_pattern"),
                ),
                pool,
                sem,
            )
            for args in monitoring_args
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config", type=argparse.FileType("r"), help="config file with monitoring args"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    print("Starting execution of scheduled tasks.")
    try:
        asyncio.run(main(args.config))
    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Exiting...")
