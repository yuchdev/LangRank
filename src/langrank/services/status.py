from __future__ import annotations

from dataclasses import dataclass

from langrank.db.repository import Database
from langrank.providers.registry import ProviderRegistry


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    latest_local_observation: str | None
    last_fetch_status: str | None
    last_fetch_started_at: str | None
    record_count: int
    provider_state: str


class StatusService:
    def __init__(self, database: Database, registry: ProviderRegistry) -> None:
        self._database = database
        self._registry = registry

    def statuses(self) -> list[ProviderStatus]:
        items: list[ProviderStatus] = []
        for provider in self._registry.all():
            last_run = self._database.last_fetch_run(provider.provider_id)
            items.append(
                ProviderStatus(
                    provider_id=provider.provider_id,
                    latest_local_observation=self._database.latest_observation_for_provider(
                        provider.provider_id
                    ),
                    last_fetch_status=None if last_run is None else last_run["status"],
                    last_fetch_started_at=None if last_run is None else last_run["started_at"],
                    record_count=self._database.count_observations(provider.provider_id),
                    provider_state="ready",
                )
            )
        return items
