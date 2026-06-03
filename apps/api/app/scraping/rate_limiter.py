from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, delay_ms: int) -> None:
        self.delay_ms = max(delay_ms, 0)

    def wait(self) -> None:
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)
