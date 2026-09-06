from __future__ import annotations

from dataclasses import dataclass

import httpx

from langrank.errors import FetchError


@dataclass(frozen=True)
class HttpClientOptions:
    timeout: float = 20.0
    user_agent: str = "langrank/0.1.0"


class HttpClientFactory:
    def __init__(self, options: HttpClientOptions | None = None) -> None:
        self._options = options or HttpClientOptions()

    def build(self) -> httpx.Client:
        return httpx.Client(
            timeout=self._options.timeout,
            headers={"User-Agent": self._options.user_agent},
            follow_redirects=True,
        )

    @staticmethod
    def map_error(error: httpx.HTTPError) -> FetchError:
        return FetchError(str(error))
