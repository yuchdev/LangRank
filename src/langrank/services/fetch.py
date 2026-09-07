from __future__ import annotations

from dataclasses import dataclass

from langrank.db.repository import Database
from langrank.models import FetchRequest, FetchRunStatus, ValidationReport
from langrank.providers.base import RatingProvider


@dataclass(frozen=True)
class FetchSummary:
    provider_id: str
    records_seen: int
    records_inserted: int
    records_updated: int
    validation_report: ValidationReport
    status: FetchRunStatus


class FetchService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def fetch(self, provider: RatingProvider, request: FetchRequest) -> FetchSummary:
        metadata = provider.metadata()
        self._database.upsert_provider_metadata(metadata)
        fetch_run_id = self._database.create_fetch_run(metadata.provider_id)
        try:
            payload = provider.fetch(request)
            if payload.artifact is not None:
                self._database.record_raw_artifact(payload.artifact)
            records = provider.parse(payload)
            observations = provider.normalize(records)
            report = provider.validate(observations)
            inserted = 0
            updated = 0
            status = FetchRunStatus.DRY_RUN if request.dry_run else FetchRunStatus.SUCCESS
            if report.ok and not request.dry_run:
                inserted, updated = self._database.upsert_observations(observations, fetch_run_id)
            self._database.finish_fetch_run(
                fetch_run_id,
                status=status,
                records_seen=len(records),
                records_inserted=inserted,
                records_updated=updated,
                warnings=[issue.message for issue in report.issues if issue.severity.value == "warning"],
                error=None if report.ok else "; ".join(issue.message for issue in report.issues),
            )
            return FetchSummary(
                provider_id=metadata.provider_id,
                records_seen=len(records),
                records_inserted=inserted,
                records_updated=updated,
                validation_report=report,
                status=status,
            )
        except Exception as exc:
            self._database.finish_fetch_run(
                fetch_run_id,
                status=FetchRunStatus.FAILED,
                records_seen=0,
                records_inserted=0,
                records_updated=0,
                warnings=[],
                error=str(exc),
            )
            raise
