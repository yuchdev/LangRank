from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from langrank.models import (
    FetchRequest,
    Granularity,
    MethodologyNote,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    Severity,
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import build_observation, payload_from_content


class RedMonkProvider:
    provider_id = "redmonk"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        self._data_path = Path(__file__).parent / "data" / "redmonk.csv"

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="RedMonk",
            description="RedMonk language rank snapshots.",
            homepage="https://redmonk.com/sogrady/",
            default_metric="redmonk-rank",
            native_granularity=Granularity.MONTH,
            caveats=["Sparse snapshots; monthly interpolation is intentionally not performed."],
            parser_version="redmonk-v1",
            metrics=[
                MetricDefinition(
                    id="redmonk-rank",
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Published RedMonk snapshot rank; ties preserved.",
                )
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="2026-v1",
                    valid_from=date(2016, 1, 1),
                    valid_to=None,
                    description="Snapshot-based rankings with publication date provenance.",
                    source_url="https://redmonk.com/sogrady/",
                )
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        content = self._data_path.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url="https://redmonk.com/sogrady/",
            content=content,
            mime_type="text/csv",
            metadata_json={"mode": request.source or "published", "provenance": "official"},
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        rows = csv.DictReader(raw.content.decode("utf-8").splitlines())
        records: list[SourceRecord] = []
        for row in rows:
            period_start = date.fromisoformat(row["period"])
            period_end = period_start
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id="redmonk-rank",
                    language=row["language"],
                    period_start=period_start,
                    period_end=period_end,
                    period_label=period_start.strftime("%Y-%m"),
                    granularity=Granularity.MONTH,
                    rank=int(row["rank"]),
                    value=float(row["rank"]),
                    unit="rank",
                    source_url=row["source_url"],
                    metadata={
                        "provenance": row.get("provenance") or "official",
                        "publication_date": row["publication_date"],
                    },
                )
            )
        return records

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        parser_version = self.metadata().parser_version
        observations: list[Observation] = []
        for record in records:
            publication_date = record.metadata.get("publication_date")
            published_at = (
                datetime.combine(date.fromisoformat(str(publication_date)), datetime.min.time(), UTC)
                if publication_date
                else None
            )
            observations.append(
                build_observation(
                    record=record,
                    language_id=self._normalizer.resolve(record.language),
                    parser_version=parser_version,
                    retrieved_at=self._retrieved_at,
                    is_derived=False,
                    derivation_method=None,
                    source_document_id=record.metadata.get("publication_date") or record.period_label,
                    source_published_at=published_at,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        for item in observations:
            if item.rank is not None and item.rank <= 0:
                report.add(Severity.ERROR, "rank_positive", f"{item.language_id} rank must be positive")
            key = (item.language_id, item.period_start, item.metric_id)
            if key in seen:
                report.add(
                    Severity.ERROR,
                    "duplicate_language_period",
                    f"duplicate language/period metric for {item.language_id} {item.period_label}",
                )
            seen.add(key)
        return report

    def upstream_latest_period(self) -> str:
        return "2025-06"
