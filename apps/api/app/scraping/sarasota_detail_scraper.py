from __future__ import annotations

from app.scraping.playwright_client import PageClient, PageLoadResult
from app.scraping.rate_limiter import RateLimiter


class SarasotaDetailScraper:
    def __init__(self, *, client: PageClient, rate_limiter: RateLimiter) -> None:
        self.client = client
        self.rate_limiter = rate_limiter

    def load_detail_page(self, url: str) -> PageLoadResult:
        result = self.client.load_page(url)
        self.rate_limiter.wait()
        return result
