from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from langrank.errors import FetchError
from langrank.models import Observation, RawArtifact, SourceRecord
from langrank.providers.base import FetchPayload

#: Cache filename extensions written by :func:`payload_from_content`, newest-first
#: preference order is irrelevant (mtime decides) but the set bounds the glob.
_CACHE_EXTENSIONS = (".json", ".csv", ".bin")

#: A provider id safe to interpolate into a cache glob: no path separators or
#: traversal segments (SEC-5).
_PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")


#: Calendar bounds ``(start_month, start_day, end_month, end_day)`` of each quarter,
#: indexed by quarter number. Quarter-end months (Mar/Jun/Sep/Dec) have fixed last
#: days, so no leap-year handling is needed.
_QUARTER_BOUNDS = {
    1: (1, 1, 3, 31),
    2: (4, 1, 6, 30),
    3: (7, 1, 9, 30),
    4: (10, 1, 12, 31),
}


def quarter_period(year: int, quarter: int) -> tuple[date, date, str]:
    """Return the calendar bounds and label for a calendar quarter.

    Quarters follow the standard calendar convention: Q1 is Jan 1..Mar 31, Q2 is
    Apr 1..Jun 30, Q3 is Jul 1..Sep 30 and Q4 is Oct 1..Dec 31. Used by quarterly
    providers to populate ``period_start`` / ``period_end`` / ``period_label`` on a
    :class:`~langrank.models.SourceRecord`.

    :param year: The calendar year the quarter belongs to.
    :param quarter: The quarter number, in ``1..4``.
    :returns: A ``(period_start, period_end, period_label)`` tuple where the label
        is formatted ``"YYYY-Qn"``.
    :raises ValueError: If ``quarter`` is not in ``1..4``.
    """
    bounds = _QUARTER_BOUNDS.get(quarter)
    if bounds is None:
        raise ValueError(f"quarter must be in 1..4, got {quarter!r}")
    start_month, start_day, end_month, end_day = bounds
    period_start = date(year, start_month, start_day)
    period_end = date(year, end_month, end_day)
    return period_start, period_end, f"{year:04d}-Q{quarter}"


def build_observation_hash(record: SourceRecord) -> str:
    return hashlib.sha256(json.dumps(asdict(record), sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _extension_for(mime_type: str) -> str:
    """Map a MIME type to the cache-file extension used on disk.

    :param mime_type: The artifact MIME type.
    :returns: ``.csv``, ``.json`` or ``.bin``.
    """
    if mime_type == "text/csv":
        return ".csv"
    if mime_type == "application/json":
        return ".json"
    return ".bin"


def load_cached_payload(*, provider_id: str, cache_dir: Path) -> FetchPayload:
    """Return the newest cached artifact for ``provider_id`` for offline replay.

    Used by ``--offline`` to replay the last cached bytes without any network. The
    lookup is confined to ``cache_dir``: ``provider_id`` is constrained to
    ``[a-z0-9-]``, only ``{provider_id}-*`` files with a known extension are
    considered, symlinks are rejected, and each candidate must resolve to a
    regular file under ``cache_dir`` (SEC-5).

    :param provider_id: The rating id whose cache subdirectory is being read.
    :param cache_dir: The provider's own cache directory.
    :returns: A :class:`FetchPayload` with the cached bytes and no artifact (a
        replay does not mint a new :class:`RawArtifact`).
    :raises FetchError: If ``provider_id`` is unsafe or no cached artifact exists.
    """
    if not _PROVIDER_ID_RE.match(provider_id):
        raise FetchError(f"invalid provider id for cache lookup: {provider_id!r}")
    base = cache_dir.resolve()
    if not base.is_dir():
        raise FetchError(f"no cached artifact for provider {provider_id!r}; run without --offline first")

    prefix = str(base) + os.sep
    candidates: list[Path] = []
    for extension in _CACHE_EXTENSIONS:
        for path in base.glob(f"{provider_id}-*{extension}"):
            if path.is_symlink():
                continue
            resolved = path.resolve()
            if not str(resolved).startswith(prefix) or not resolved.is_file():
                continue
            candidates.append(resolved)
    if not candidates:
        raise FetchError(f"no cached artifact for provider {provider_id!r}; run without --offline first")

    newest = max(candidates, key=lambda path: path.stat().st_mtime)
    return FetchPayload(artifact=None, content=newest.read_bytes())


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
        ext = _extension_for(mime_type)
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
    derivation_method: Optional[str],
    source_document_id: Optional[str],
    source_published_at: Optional[datetime],
    sample_size: Optional[int] = None,
    population: Optional[str] = None,
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
