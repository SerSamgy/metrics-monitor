from datetime import datetime

from pydantic import BaseModel


class WebsiteMetrics(BaseModel):
    """Fields of a website_metrics DB table."""

    url: str
    request_timestamp: datetime
    response_time: float
    status_code: int
    pattern_found: bool
