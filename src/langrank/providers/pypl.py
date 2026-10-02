from __future__ import annotations

import csv
from calendar import monthrange
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional

from langrank.errors import ParseError
from langrank.models import (
    FetchRequest,
    Granularity,
    MethodologyNote,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    SourceRecord,
    ValidationReport,
)
from langrank.providers.base import BaseRatingProvider, FetchPayload
from langrank.providers.common import (
    build_observation,
    payload_from_content,
    validate_bounded_values,
    validate_positive_ranks,
    validate_unique_observations,
)


class PyplProvider(BaseRatingProvider):
    provider_id = "pypl"

    def __init__(self, cache_dir: Path) -> None:
        super().__init__(cache_dir)
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
            parser_version="pypl-v2",
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
        self._capture_payload_timestamp(raw)
        try:
            rows = csv.DictReader(raw.content.decode("utf-8").splitlines())
            records: list[SourceRecord] = []
            for row in rows:
                period_start = date.fromisoformat(row["period"])
                period_end = date(
                    period_start.year, period_start.month, monthrange(period_start.year, period_start.month)[1]
                )
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
        except (ValueError, KeyError, TypeError, csv.Error) as exc:
            raise ParseError("pypl payload is malformed.") from exc

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
        validate_positive_ranks(observations, report, metric_id="pypl-rank")
        validate_bounded_values(
            observations,
            report,
            code="share_range",
            metric_id="pypl-share",
            message=lambda item: f"{item.language_id} share outside 0..100 at {item.period_label}",
        )
        validate_unique_observations(observations, report)
        return report

    def _bundled_snapshot_payload(self) -> Optional[FetchPayload]:
        """Return the bundled PYPL CSV as a snapshot payload for period reporting.

        Feeds :meth:`~langrank.providers.base.BaseRatingProvider.upstream_latest_period`
        when no cached artifact exists, without any network access.

        :returns: A :class:`FetchPayload` wrapping the bundled ``pypl.csv`` bytes.
        """
        return FetchPayload(artifact=None, content=self._data_path.read_bytes())
