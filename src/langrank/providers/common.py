from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langrank.models import Observation, RawArtifact, SourceRecord
from langrank.providers.base import FetchPayload


def build_observation_hash(record: SourceRecord) -> str:
    return hashlib.sha256(
        json.dumps(asdict(record), sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def payload_from_content(
    *,
    provider_id: str,
    cache_dir: Path,
    url: str,
    content: bytes,
    mime_type: str,
    metadata_json: dict[str, object],
    no_cache: bool,
) -> FetchPayload:
    retrieved_at = datetime.now(UTC)
    sha256 = hashlib.sha256(content).hexdigest()
    artifact = None
    if not no_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        ext = ".csv" if mime_type == "text/csv" else ".bin"
        file_path = cache_dir / f"{provider_id}-{sha256[:12]}{ext}"
        file_path.write_bytes(content)
        artifact = RawArtifact(
            id=str(uuid4()),
            rating_id=provider_id,
            url=url,
            retrieved_at=retrieved_at,
            sha256=sha256,
            mime_type=mime_type,
            local_path=str(file_path),
            metadata_json={
                **metadata_json,
                "provider": provider_id,
                "sha256": sha256,
                "url": url,
                "retrieved_at": retrieved_at.isoformat(),
            },
        )
    return FetchPayload(artifact=artifact, content=content)


def build_observation(
    *,
    record: SourceRecord,
    language_id: str,
    parser_version: str,
    retrieved_at: datetime,
    is_derived: bool,
    derivation_method: str | None,
    source_document_id: str | None,
    source_published_at: datetime | None,
    sample_size: int | None = None,
    population: str | None = None,
) -> Observation:
    return Observation(
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
        source_document_id=source_document_id,
        is_derived=is_derived,
        derivation_method=derivation_method,
        retrieved_at=retrieved_at,
        source_published_at=source_published_at,
        parser_version=parser_version,
        raw_record_hash=build_observation_hash(record),
        metadata_json=record.metadata,
        sample_size=sample_size,
        population=population,
    )
