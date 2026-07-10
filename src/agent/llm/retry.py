from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry(
    fn: Callable[..., T],
    retries: int = 1,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable[..., T]:
    def wrapper(*args: object, **kwargs: object) -> T:
        attempt = 0
        current_delay = delay_seconds
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                if attempt >= retries:
                    raise
                time.sleep(current_delay)
                current_delay *= backoff_factor
                attempt += 1
    return wrapper
