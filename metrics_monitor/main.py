import argparse
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import TextIO

import aiohttp
import asyncpg
from dotenv import load_dotenv

from metrics_monitor.db_operations import create_table, save_metrics

load_dotenv()


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
                    response_time = (datetime.now() - start_time).total_seconds()
                    status_code = response.status
                    content = await response.text()

                    if re.search(regexp_pattern, content):
                        pattern_found = True
                    else:
                        pattern_found = False

                    logging.info(
                        f"{url} - response_time: {response_time} - status_code: {status_code} - pattern_found: {pattern_found}"
                    )

                    async with sem, pool.acquire() as conn:
                        await save_metrics(
                            url,
                            start_time,
                            response_time,
                            status_code,
                            pattern_found,
                            conn,
                        )

        except Exception as e:
            logging.error(f"Error checking {url}: {str(e)}")


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
    # TODO: move `dsn` to settings
    pg_user = os.getenv("POSTGRES_USER")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT")
    pg_database = os.getenv("POSTGRES_DATABASE")
    dsn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    # TODO: add settings for `pool`
    async with asyncpg.create_pool(dsn) as pool:
        async with pool.acquire() as conn:
            await create_table(conn)

        sem = asyncio.Semaphore(10)
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
