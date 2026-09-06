from __future__ import annotations

from pathlib import Path

from langrank.errors import ProviderError
from langrank.providers.base import RatingProvider
from langrank.providers.demo import DemoProvider


class ProviderRegistry:
    def __init__(self, cache_dir: Path) -> None:
        self._providers: dict[str, RatingProvider] = {
            "demo": DemoProvider(cache_dir),
        }

    def get(self, provider_id: str) -> RatingProvider:
        if provider_id == "all":
            raise ProviderError("'all' is only valid for fetch commands.")
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ProviderError(f"Unknown provider '{provider_id}'.") from exc

    def all(self) -> list[RatingProvider]:
        return list(self._providers.values())
