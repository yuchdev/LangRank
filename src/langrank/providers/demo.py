from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from langrank.models import (
    FetchRequest,
    Granularity,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    RawArtifact,
    Severity,
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import LanguageNormalizer
from langrank.providers.base import FetchPayload


class DemoProvider:
    provider_id = "demo"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Demo synthetic dataset",
            description="Deterministic synthetic annual language history for offline testing.",
            homepage=None,
            default_metric="rating",
            native_granularity=Granularity.YEAR,
            caveats=["Synthetic data only; do not use as real popularity evidence."],
            parser_version="demo-v1",
            metrics=[
                MetricDefinition(
                    id="rank",
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Synthetic ordinal ranking where 1 is best.",
                ),
                MetricDefinition(
                    id="rating",
                    rating_id=self.provider_id,
                    display_name="Rating",
                    unit="percent",
                    higher_is_better=True,
                    description="Synthetic relative rating expressed as a percentage.",
                ),
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        dataset = self._build_dataset(request)
        content = json.dumps(dataset, indent=2, sort_keys=True).encode("utf-8")
        sha256 = hashlib.sha256(content).hexdigest()
        artifact = None
        if not request.no_cache:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            file_path = self._cache_dir / f"demo-{sha256[:12]}.json"
            file_path.write_bytes(content)
            artifact = RawArtifact(
                id=str(uuid4()),
                rating_id=self.provider_id,
                url="demo://synthetic-history",
                retrieved_at=self._retrieved_at,
                sha256=sha256,
                mime_type="application/json",
                local_path=str(file_path),
                metadata_json={
                    "provider": self.provider_id,
                    "status_code": 200,
                    "retrieved_at": self._retrieved_at.isoformat(),
                    "sha256": sha256,
                    "url": "demo://synthetic-history",
                },
            )
        return FetchPayload(artifact=artifact, content=content)

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        dataset = json.loads(raw.content.decode("utf-8"))
        records: list[SourceRecord] = []
        for entry in dataset["records"]:
            records.append(
                SourceRecord(
                    rating_id=self.provider_id,
                    metric_id=entry["metric_id"],
                    language=entry["language"],
                    period_start=date.fromisoformat(entry["period_start"]),
                    period_end=date.fromisoformat(entry["period_end"]),
                    period_label=entry["period_label"],
                    granularity=Granularity(entry["granularity"]),
                    rank=entry["rank"],
                    value=entry["value"],
                    unit=entry["unit"],
                    source_url=entry["source_url"],
                    metadata={"synthetic": True},
                )
            )
        return records

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        observations: list[Observation] = []
        parser_version = self.metadata().parser_version
        for record in records:
            language_id = self._normalizer.resolve(record.language)
            raw_payload = json.dumps(asdict(record), sort_keys=True, default=str).encode("utf-8")
            observations.append(
                Observation(
                    rating_id=record.rating_id,
                    metric_id=record.metric_id,
                    language_id=language_id,
                    period_start=record.period_start,
                    period_end=record.period_end,
                    period_label=record.period_label,
                    granularity=record.granularity,
                    rank=record.rank,
                    value=record.value,
                    unit=record.unit,
                    source_language_name=record.language,
                    source_url=record.source_url,
                    source_document_id=record.period_label,
                    is_derived=False,
                    derivation_method=None,
                    retrieved_at=self._retrieved_at,
                    source_published_at=None,
                    parser_version=parser_version,
                    raw_record_hash=hashlib.sha256(raw_payload).hexdigest(),
                    metadata_json=record.metadata,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        report = ValidationReport()
        for observation in observations:
            if (
                observation.metric_id == "rating"
                and observation.value is not None
                and not 0 <= observation.value <= 100
            ):
                report.add(
                    Severity.ERROR,
                    "percentage_range",
                    f"{observation.language_id} rating is outside 0..100",
                )
            if (
                observation.metric_id == "rank"
                and observation.rank is not None
                and observation.rank <= 0
            ):
                report.add(
                    Severity.ERROR,
                    "rank_positive",
                    f"{observation.language_id} rank must be positive",
                )
        return report

    def upstream_latest_period(self) -> str:
        return "2026"

    def _build_dataset(self, request: FetchRequest) -> dict[str, object]:
        base = {
            "python": 18.0,
            "c": 14.5,
            "c++": 13.0,
            "java": 15.0,
            "javascript": 12.0,
            "rust": 4.0,
            "go": 5.0,
        }
        deltas = {
            "python": 0.9,
            "c": -0.2,
            "c++": -0.1,
            "java": -0.15,
            "javascript": 0.2,
            "rust": 0.8,
            "go": 0.6,
        }
        start_year = 2016
        end_year = 2026
        if request.since:
            start_year = max(start_year, request.since.year)
        if request.until:
            end_year = min(end_year, request.until.year)
        if request.years:
            start_year = max(start_year, end_year - request.years + 1)
        rows: list[dict[str, object]] = []
        for year in range(start_year, end_year + 1):
            ratings: dict[str, float] = {}
            for language, seed in base.items():
                years_since = year - 2016
                rating = round(
                    seed + years_since * deltas[language] + ((year + len(language)) % 3) * 0.2, 2
                )
                ratings[language] = max(rating, 0.5)
            ranked = sorted(ratings.items(), key=lambda item: (-item[1], item[0]))
            rank_map = {language: index for index, (language, _) in enumerate(ranked, start=1)}
            for language, rating in ratings.items():
                for metric_id in ("rating", "rank"):
                    rows.append(
                        {
                            "metric_id": metric_id,
                            "language": language,
                            "period_start": date(year, 1, 1).isoformat(),
                            "period_end": date(year, 12, 31).isoformat(),
                            "period_label": str(year),
                            "granularity": Granularity.YEAR.value,
                            "rank": rank_map[language],
                            "value": rating if metric_id == "rating" else float(rank_map[language]),
                            "unit": "percent" if metric_id == "rating" else "rank",
                            "source_url": "demo://synthetic-history",
                        }
                    )
        return {
            "provider": self.provider_id,
            "generated_at": self._retrieved_at.isoformat(),
            "synthetic": True,
            "records": rows,
        }
