from __future__ import annotations

from dataclasses import dataclass

from langrank.db.repository import Database
from langrank.providers.registry import ProviderRegistry


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    latest_local_observation: str | None
    last_fetch_status: str | None
    last_failed_fetch_at: str | None
    last_fetch_started_at: str | None
    record_count: int
    upstream_latest_period: str | None
    provider_state: str


class StatusService:
    def __init__(self, database: Database, registry: ProviderRegistry) -> None:
        self._database = database
        self._registry = registry

    def statuses(self) -> list[ProviderStatus]:
        items: list[ProviderStatus] = []
        for provider in self._registry.all():
            last_run = self._database.last_fetch_run(provider.provider_id)
            last_failed = self._database.last_failed_fetch_run(provider.provider_id)
            upstream_latest_period = (
                provider.upstream_latest_period()
                if hasattr(provider, "upstream_latest_period")
                else None
            )
            latest_local = self._database.latest_observation_for_provider(provider.provider_id)
            provider_state = "unknown"
            if latest_local and upstream_latest_period:
                provider_state = (
                    "current" if str(latest_local).startswith(upstream_latest_period) else "stale"
                )
            elif latest_local:
                provider_state = "ready"
            items.append(
                ProviderStatus(
                    provider_id=provider.provider_id,
                    latest_local_observation=latest_local,
                    last_fetch_status=None if last_run is None else last_run["status"],
                    last_failed_fetch_at=None if last_failed is None else last_failed["started_at"],
                    last_fetch_started_at=None if last_run is None else last_run["started_at"],
                    record_count=self._database.count_observations(provider.provider_id),
                    upstream_latest_period=upstream_latest_period,
                    provider_state=provider_state,
                )
            )
        return items
