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


class PyplProvider:
    provider_id = "pypl"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        self._data_path = Path(__file__).parent / "data" / "pypl.csv"

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="PYPL",
            description="PYPL language popularity history.",
            homepage="https://pypl.github.io/PYPL.html",
            default_metric="pypl-share",
            native_granularity=Granularity.MONTH,
            caveats=["C/C++ is published as a combined category and remains combined."],
            parser_version="pypl-v1",
            metrics=[
                MetricDefinition(
                    id="pypl-rank",
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Monthly PYPL ordinal ranking.",
                ),
                MetricDefinition(
                    id="pypl-share",
                    rating_id=self.provider_id,
                    display_name="Share",
                    unit="percent",
                    higher_is_better=True,
                    description="Monthly PYPL share percentage.",
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="2026-v1",
                    valid_from=date(2016, 1, 1),
                    valid_to=None,
                    description="Published monthly shares imported without splitting combined categories.",
                    source_url="https://pypl.github.io/PYPL.html",
                )
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        content = self._data_path.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url="https://pypl.github.io/PYPL.html",
            content=content,
            mime_type="text/csv",
            metadata_json={"mode": request.source or "published", "provenance": "published"},
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        rows = csv.DictReader(raw.content.decode("utf-8").splitlines())
        records: list[SourceRecord] = []
        for row in rows:
            period_start = date.fromisoformat(row["period"])
            period_end = date(period_start.year, period_start.month, 28)
            meta = {
                "provenance": row.get("provenance") or "published",
                "is_derived": row.get("is_derived") == "1",
                "derivation_method": row.get("derivation_method") or None,
            }
            rank = int(row["rank"])
            share = float(row["share"])
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id="pypl-share",
                    language=row["language"],
                    period_start=period_start,
                    period_end=period_end,
                    period_label=period_start.strftime("%Y-%m"),
                    granularity=Granularity.MONTH,
                    rank=rank,
                    value=share,
                    unit="percent",
                    source_url=row["source_url"],
                    metadata=meta,
                )
            )
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id="pypl-rank",
                    language=row["language"],
                    period_start=period_start,
                    period_end=period_end,
                    period_label=period_start.strftime("%Y-%m"),
                    granularity=Granularity.MONTH,
                    rank=rank,
                    value=float(rank),
                    unit="rank",
                    source_url=row["source_url"],
                    metadata=meta,
                )
            )
        return records

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        parser_version = self.metadata().parser_version
        observations: list[Observation] = []
        for record in records:
            language_id = self._normalizer.resolve(record.language)
            is_derived = bool(record.metadata.get("is_derived", False))
            observations.append(
                build_observation(
                    record=record,
                    language_id=language_id,
                    parser_version=parser_version,
                    retrieved_at=self._retrieved_at,
                    is_derived=is_derived,
                    derivation_method=record.metadata.get("derivation_method") or None,
                    source_document_id=record.period_label,
                    source_published_at=None,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        for item in observations:
            if item.metric_id == "pypl-rank" and item.rank is not None and item.rank <= 0:
                report.add(Severity.ERROR, "rank_positive", f"{item.language_id} rank must be positive")
            if item.metric_id == "pypl-share" and item.value is not None and not 0 <= item.value <= 100:
                report.add(
                    Severity.ERROR,
                    "share_range",
                    f"{item.language_id} share outside 0..100 at {item.period_label}",
                )
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
        return "2025-12"
