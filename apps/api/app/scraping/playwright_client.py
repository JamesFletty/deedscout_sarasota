from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.core.config import Settings

PageLoadStatus = Literal["success", "blocked", "failed"]


@dataclass(frozen=True)
class ScraperConfig:
    county: str = "sarasota"
    headless: bool = True
    max_pages: int = 150
    max_retries: int = 2
    delay_between_pages_ms: int = 1500
    timeout_ms: int = 30000
    screenshot_enabled: bool = True
    save_html_enabled: bool = True
    user_agent: str = "DeedScout Sarasota research-triage bot; public-record snapshot preservation"

    def __post_init__(self) -> None:
        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")
        if self.delay_between_pages_ms < 0:
            raise ValueError("delay_between_pages_ms cannot be negative")

    @classmethod
    def from_settings(cls, settings: Settings) -> ScraperConfig:
        return cls(
            headless=settings.scraper_headless,
            max_pages=settings.scraper_max_pages,
            max_retries=settings.scraper_max_retries,
            delay_between_pages_ms=settings.scraper_delay_ms,
            timeout_ms=settings.scraper_timeout_ms,
            screenshot_enabled=settings.scraper_screenshots_enabled,
            save_html_enabled=settings.scraper_save_html_enabled,
            user_agent=settings.scraper_user_agent,
        )


@dataclass(frozen=True)
class PageLoadResult:
    requested_url: str
    final_url: str | None
    status: PageLoadStatus
    http_status: int | None = None
    page_title: str | None = None
    html: str | None = None
    screenshot_bytes: bytes | None = None
    error_message: str | None = None
    attempts: int = 1
    blocked_reason: str | None = None


class PageClient(Protocol):
    def load_page(self, url: str) -> PageLoadResult: ...


class RetryablePageLoadError(RuntimeError):
    """Raised for bounded-retry Playwright navigation failures."""


class PlaywrightPageClient:
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config

    def load_page(self, url: str) -> PageLoadResult:
        last_error: str | None = None
        max_attempts = self.config.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                return self._load_once(url, attempt=attempt)
            except RetryablePageLoadError as exc:
                last_error = str(exc)

        return PageLoadResult(
            requested_url=url,
            final_url=None,
            status="failed",
            error_message=last_error or "Playwright page load failed",
            attempts=max_attempts,
        )

    def _load_once(self, url: str, *, attempt: int) -> PageLoadResult:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found]
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        browser: Any | None = None
        context: Any | None = None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.config.headless)
                context = browser.new_context(user_agent=self.config.user_agent)
                context.set_default_timeout(self.config.timeout_ms)
                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                html = page.content() if self.config.save_html_enabled else None
                title = page.title()
                screenshot = page.screenshot(full_page=True) if self.config.screenshot_enabled else None
                final_url = page.url
                status_code = response.status if response is not None else None
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            raise RetryablePageLoadError(str(exc)) from exc
        finally:
            if context is not None:
                with suppress(PlaywrightError):
                    context.close()
            if browser is not None:
                with suppress(PlaywrightError):
                    browser.close()

        blocked_reason = detect_blocked_reason(title=title, html=html, http_status=status_code)
        if blocked_reason is not None:
            return PageLoadResult(
                requested_url=url,
                final_url=final_url,
                status="blocked",
                http_status=status_code,
                page_title=title,
                html=html,
                screenshot_bytes=screenshot,
                attempts=attempt,
                blocked_reason=blocked_reason,
            )

        return PageLoadResult(
            requested_url=url,
            final_url=final_url,
            status="success",
            http_status=status_code,
            page_title=title,
            html=html,
            screenshot_bytes=screenshot,
            attempts=attempt,
        )


def detect_blocked_reason(*, title: str | None, html: str | None, http_status: int | None) -> str | None:
    if http_status in {401, 403, 429, 503}:
        return f"HTTP status {http_status} indicates access may be blocked or rate-limited"

    text = f"{title or ''}\n{html or ''}".lower()
    blocked_markers = (
        "captcha",
        "access denied",
        "forbidden",
        "too many requests",
        "cloudflare",
        "bot detection",
        "blocked",
    )
    for marker in blocked_markers:
        if marker in text:
            return f"Page contains blocked-state marker: {marker}"
    return None
