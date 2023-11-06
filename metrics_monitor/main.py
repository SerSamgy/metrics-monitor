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
from metrics_monitor.models import WebsiteMetrics
from metrics_monitor.settings import Settings


async def check_website(
    url: str,
    interval: int,
    regexp_pattern: str,
    pool: asyncpg.pool.Pool,
    sem: asyncio.Semaphore,
):
    """
    Check the given website at a specified interval and log the response time, status code, and whether a given regular
    expression pattern was found in the response content.

    Args:
        url (str): The URL of the website to check.
        interval (int): The interval, in seconds, at which to check the website.
        regexp_pattern (str): The regular expression pattern to search for in the response content.
        pool (asyncpg.pool.Pool): The connection pool to the database where website metrics will be stored.
        sem (asyncio.Semaphore): The semaphore to limit the number of concurrent database connections.

    Returns:
        None
    """

    await asyncio.sleep(interval)

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                async with session.get(url) as response:
                    metrics = await prepare_website_metrics(
                        response, start_time, url, regexp_pattern
                    )
                    logging.info(
                        f"{url} - response_time: {metrics.response_time} - status_code: {metrics.status_code} - pattern_found: {metrics.pattern_found}"
                    )

                    async with sem, pool.acquire() as conn:
                        await save_metrics(metrics, conn)
        except Exception as e:
            logging.error(f"Error checking {url}: {str(e)}")


async def prepare_website_metrics(
    response: aiohttp.ClientResponse,
    start_time: datetime,
    url: str,
    regexp_pattern: str,
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
    if re.search(regexp_pattern, content):
        pattern_found = True
    else:
        pattern_found = False

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
            - url: The URL to monitor
            - interval: The interval between requests in seconds
            - regexp_pattern: A regular expression pattern to search for in the response body

    Returns:
        None
    """

    settings = Settings().model_dump()
    print(f"{settings=}")

    async with asyncpg.create_pool(
        settings["postgres_dsn"],
        min_size=settings["pool_min_size"],
        max_size=settings["pool_max_size"],
    ) as pool:
        async with pool.acquire() as conn:
            await create_table(conn)

        sem = asyncio.Semaphore(settings["semaphore_max_concurrent"])
        tasks = []
        monitoring_args = json.load(input_file)
        for args in monitoring_args:
            tasks.append(
                check_website(
                    args["url"],
                    args["interval"],
                    args["regexp_pattern"],
                    pool,
                    sem,
                )
            )

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
        print(f"Error: {str(e)}")
    finally:
        print("Exiting...")
