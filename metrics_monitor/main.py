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

load_dotenv()


async def check_website(
    url: str, interval: int, regexp_pattern: str, conn: asyncpg.Connection
):
    """
    Check the given website at a specified interval and log the response time, status code, and whether a given regular
    expression pattern was found in the response content.

    Args:
        url (str): The URL of the website to check.
        interval (int): The interval, in seconds, at which to check the website.
        regexp_pattern (str): The regular expression pattern to search for in the response content.
        conn (asyncpg.Connection): The connection to the database where website metrics will be stored.
    """
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

                    await conn.execute(
                        "INSERT INTO website_metrics (url, request_timestamp, response_time, status_code, pattern_found) VALUES ($1, $2, $3, $4, $5)",
                        url,
                        start_time,
                        response_time,
                        status_code,
                        pattern_found,
                    )

        except Exception as e:
            logging.error(f"Error checking {url}: {str(e)}")

        await asyncio.sleep(interval)


async def main(input_file: TextIO):
    """
    Asynchronously monitors website metrics by periodically sending HTTP requests to specified URLs and storing the
    response time, status code, and whether a specified pattern was found in the response. The monitoring parameters
    are read from a JSON file passed as an argument.

    :param input_file: A file-like object containing a JSON array of monitoring parameters. Each parameter is a JSON
                       object with the following keys:
                       - url: The URL to monitor
                       - interval: The interval between requests in seconds
                       - regexp_pattern: A regular expression pattern to search for in the response body
    """

    pg_user = os.environ.get("POSTGRES_USER")
    pg_password = os.environ.get("POSTGRES_PASSWORD")
    pg_host = os.environ.get("POSTGRES_HOST")
    pg_port = os.environ.get("POSTGRES_PORT")
    pg_database = os.environ.get("POSTGRES_DATABASE")
    dsn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    conn = await asyncpg.connect(dsn)

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS website_metrics (id serial primary key, url text, request_timestamp timestamptz, response_time float, status_code int, pattern_found boolean)"
    )

    tasks = []
    monitoring_args = json.load(input_file)
    for args in monitoring_args:
        tasks.append(
            check_website(
                args["url"],
                args["interval"],
                args["regexp_pattern"],
                conn,
            )
        )

    await asyncio.gather(*tasks)


parser = argparse.ArgumentParser()
parser.add_argument(
    "config", type=argparse.FileType("r"), help="config file with monitoring args"
)
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
asyncio.run(main(args.config))
