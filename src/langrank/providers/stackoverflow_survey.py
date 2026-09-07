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


class StackOverflowSurveyProvider:
    provider_id = "stackoverflow-survey"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        self._data_path = Path(__file__).parent / "data" / "stackoverflow_survey.csv"

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Stack Overflow Survey",
            description="Stack Overflow Developer Survey language usage percentages.",
            homepage="https://survey.stackoverflow.co/",
            default_metric="worked_with_percent",
            native_granularity=Granularity.YEAR,
            caveats=["Yearly snapshots with schema-adapter lineage tracked in metadata."],
            parser_version="stackoverflow-survey-v1",
            metrics=[
                MetricDefinition(
                    id="worked_with_percent",
                    rating_id=self.provider_id,
                    display_name="Worked with (%)",
                    unit="percent",
                    higher_is_better=True,
                    description="Percentage of respondents who reported working with the language.",
                ),
                MetricDefinition(
                    id="stackoverflow-survey-rank",
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Yearly rank derived from worked-with percentages.",
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="2026-v1",
                    valid_from=date(2016, 1, 1),
                    valid_to=None,
                    description=(
                        "Denominator is respondents answering the language usage question for each year."
                    ),
                    source_url="https://survey.stackoverflow.co/",
                )
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        content = self._data_path.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url="https://survey.stackoverflow.co/",
            content=content,
            mime_type="text/csv",
            metadata_json={"mode": request.source or "official", "provenance": "official"},
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        rows = csv.DictReader(raw.content.decode("utf-8").splitlines())
        by_year: dict[int, list[dict[str, str]]] = {}
        for row in rows:
            by_year.setdefault(int(row["year"]), []).append(row)

        records: list[SourceRecord] = []
        for year, rows_for_year in sorted(by_year.items()):
            ranked = sorted(
                rows_for_year,
                key=lambda row: (-float(row["worked_with_percent"]), row["language"].lower()),
            )
            rank_map = {item["language"]: index for index, item in enumerate(ranked, start=1)}
            for row in rows_for_year:
                period_start = date(year, 1, 1)
                period_end = date(year, 12, 31)
                metadata = {
                    "provenance": row.get("provenance") or "official",
                    "schema_adapter": f"{year}-language-worked-with",
                    "column": "LanguageWorkedWith" if year <= 2020 else "LanguageHaveWorkedWith",
                    "delimiter": ";",
                    "denominator_rule": "respondents answering language usage question",
                    "sample_size": int(row["sample_size"]),
                    "population": row["population"],
                }
                records.append(
                    SourceRecord(
                        rating_id=self.provider_id,
                        metric_id="worked_with_percent",
                        language=row["language"],
                        period_start=period_start,
                        period_end=period_end,
                        period_label=str(year),
                        granularity=Granularity.YEAR,
                        rank=rank_map[row["language"]],
                        value=float(row["worked_with_percent"]),
                        unit="percent",
                        source_url=row["source_url"],
                        metadata=metadata,
                    )
                )
                records.append(
                    SourceRecord(
                        rating_id=self.provider_id,
                        metric_id="stackoverflow-survey-rank",
                        language=row["language"],
                        period_start=period_start,
                        period_end=period_end,
                        period_label=str(year),
                        granularity=Granularity.YEAR,
                        rank=rank_map[row["language"]],
                        value=float(rank_map[row["language"]]),
                        unit="rank",
                        source_url=row["source_url"],
                        metadata=metadata,
                    )
                )
        return records

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        parser_version = self.metadata().parser_version
        observations: list[Observation] = []
        for record in records:
            observations.append(
                build_observation(
                    record=record,
                    language_id=self._normalizer.resolve(record.language),
                    parser_version=parser_version,
                    retrieved_at=self._retrieved_at,
                    is_derived=False,
                    derivation_method=None,
                    source_document_id=record.period_label,
                    source_published_at=None,
                    sample_size=record.metadata.get("sample_size"),
                    population=record.metadata.get("population"),
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        for item in observations:
            if (
                item.metric_id == "worked_with_percent"
                and item.value is not None
                and not 0 <= item.value <= 100
            ):
                report.add(
                    Severity.ERROR,
                    "percentage_range",
                    f"{item.language_id} worked_with_percent outside 0..100 at {item.period_label}",
                )
            if item.sample_size is None or item.sample_size <= 0:
                report.add(
                    Severity.ERROR,
                    "sample_size_positive",
                    f"{item.language_id} sample size missing/invalid at {item.period_label}",
                )
            if not item.population:
                report.add(
                    Severity.ERROR,
                    "population_required",
                    f"{item.language_id} population missing at {item.period_label}",
                )
            key = (item.language_id, item.period_start, item.metric_id)
            if key in seen:
                report.add(
                    Severity.ERROR,
                    "duplicate_language_year_metric",
                    f"duplicate language/year/metric for {item.language_id} {item.period_label}",
                )
            seen.add(key)
        return report

    def upstream_latest_period(self) -> str:
        return "2025"
