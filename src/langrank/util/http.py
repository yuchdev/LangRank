from __future__ import annotations

from dataclasses import dataclass
from time import sleep

import httpx

from langrank.errors import FetchError


@dataclass(frozen=True)
class HttpClientOptions:
    timeout: float = 20.0
    user_agent: str = "langrank/0.1.0"
    retries: int = 3
    backoff_seconds: float = 0.5


class HttpClientFactory:
    def __init__(self, options: HttpClientOptions | None = None) -> None:
        self._options = options or HttpClientOptions()

    def build(self) -> httpx.Client:
        return httpx.Client(
            timeout=self._options.timeout,
            headers={"User-Agent": self._options.user_agent},
            follow_redirects=True,
        )

    def get_bytes(self, url: str) -> bytes:
        last_error: Exception | None = None
        with self.build() as client:
            for attempt in range(self._options.retries):
                try:
                    response = client.get(url)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        raise FetchError(f"temporary upstream status {response.status_code}")
                    response.raise_for_status()
                    return response.content
                except (httpx.HTTPError, FetchError) as exc:
                    last_error = exc
                    if attempt < self._options.retries - 1:
                        sleep(self._options.backoff_seconds * (2**attempt))
            assert last_error is not None
            raise (
                self.map_error(last_error)
                if isinstance(last_error, httpx.HTTPError)
                else last_error
            )

    @staticmethod
    def map_error(error: httpx.HTTPError) -> FetchError:
        return FetchError(str(error))
