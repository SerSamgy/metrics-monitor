from datetime import datetime

from pydantic import BaseModel


class MonitorParams(BaseModel):
    """Parameters for monitoring a website."""

    url: str
    interval: int
    regexp_pattern: str | None = None


class WebsiteMetrics(BaseModel):
    """Fields of a website_metrics DB table."""

    url: str
    request_timestamp: datetime
    response_time: float
    status_code: int
    pattern_found: bool

    def __str__(self) -> str:
        return (
            f"url={self.url} "
            f"request_timestamp={self.request_timestamp.isoformat()} "
            f"response_time={round(self.response_time, 3)} "
            f"status_code={self.status_code} "
            f"pattern_found={self.pattern_found}"
        )
