import asyncio
import logging
import os
import re
from datetime import datetime

import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv()
websites = [
    {
        "url": "https://google.com",
        "interval": 30,
        "regexp_pattern": "About",
    },
    {
        "url": "https://duckduckgo.com",
        "interval": 40,
        "regexp_pattern": "Privacy, simplified",
    },
]


async def check_website(url, interval, regexp_pattern, conn):
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


async def main():
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

    for website in websites:
        tasks.append(
            check_website(
                website["url"],
                website["interval"],
                website["regexp_pattern"],
                conn,
            )
        )

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
