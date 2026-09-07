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


class TiobeProvider:
    provider_id = "tiobe"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        self._data_path = Path(__file__).parent / "data" / "tiobe.csv"

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="TIOBE",
            description="TIOBE Index monthly language rank and rating history.",
            homepage="https://www.tiobe.com/tiobe-index/",
            default_metric="tiobe-rating",
            native_granularity=Granularity.MONTH,
            caveats=["Historical imports may include documented fallback reconstruction."],
            parser_version="tiobe-v1",
            metrics=[
                MetricDefinition(
                    id="tiobe-rank",
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Monthly TIOBE ordinal rank where 1 is best.",
                ),
                MetricDefinition(
                    id="tiobe-rating",
                    rating_id=self.provider_id,
                    display_name="Rating",
                    unit="percent",
                    higher_is_better=True,
                    description="Monthly TIOBE rating percentage.",
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="2026-v1",
                    valid_from=date(2016, 1, 1),
                    valid_to=None,
                    description="Monthly source snapshots with rank and rating imported as published.",
                    source_url="https://www.tiobe.com/tiobe-index/",
                )
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        mode = request.source or "auto"
        content = self._data_path.read_bytes()
        provenance = "official" if mode in {"auto", "official"} else "third_party_reconstruction"
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url="https://www.tiobe.com/tiobe-index/",
            content=content,
            mime_type="text/csv",
            metadata_json={"mode": mode, "provenance": provenance},
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        rows = csv.DictReader(raw.content.decode("utf-8").splitlines())
        records: list[SourceRecord] = []
        for row in rows:
            period_start = date.fromisoformat(row["period"])
            period_end = date(period_start.year, period_start.month, 28)
            meta = {"provenance": row.get("provenance") or "official"}
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id="tiobe-rating",
                    language=row["language"],
                    period_start=period_start,
                    period_end=period_end,
                    period_label=period_start.strftime("%Y-%m"),
                    granularity=Granularity.MONTH,
                    rank=int(row["rank"]),
                    value=float(row["rating"]),
                    unit="percent",
                    source_url=row["source_url"],
                    metadata=meta,
                )
            )
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id="tiobe-rank",
                    language=row["language"],
                    period_start=period_start,
                    period_end=period_end,
                    period_label=period_start.strftime("%Y-%m"),
                    granularity=Granularity.MONTH,
                    rank=int(row["rank"]),
                    value=float(row["rank"]),
                    unit="rank",
                    source_url=row["source_url"],
                    metadata=meta,
                )
            )
        return records

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        notes = self.metadata().parser_version
        observations: list[Observation] = []
        for record in records:
            observations.append(
                build_observation(
                    record=record,
                    language_id=self._normalizer.resolve(record.language),
                    parser_version=notes,
                    retrieved_at=self._retrieved_at,
                    is_derived=False,
                    derivation_method=None,
                    source_document_id=record.period_label,
                    source_published_at=None,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        for item in observations:
            if item.metric_id == "tiobe-rank" and item.rank is not None and item.rank <= 0:
                report.add(Severity.ERROR, "rank_positive", f"{item.language_id} rank must be positive")
            if item.metric_id == "tiobe-rating" and item.value is not None and not 0 <= item.value <= 100:
                report.add(
                    Severity.ERROR,
                    "rating_range",
                    f"{item.language_id} rating outside 0..100 at {item.period_label}",
                )
            key = (item.language_id, item.period_start, item.metric_id)
            if key in seen:
                report.add(
                    Severity.ERROR,
                    "duplicate_language_period",
                    f"duplicate language/month metric for {item.language_id} {item.period_label}",
                )
            seen.add(key)
        return report

    def upstream_latest_period(self) -> str:
        return "2025-12"
