from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from langrank.errors import FetchError
from langrank.models import Observation, RawArtifact, Severity, SourceRecord, ValidationReport
from langrank.providers.base import FetchPayload

# Cache filename extensions written by :func:`payload_from_content`, newest-first
# preference order is irrelevant (mtime decides), but the set bounds the glob.
_CACHE_EXTENSIONS = (".json", ".csv", ".bin")

# A provider id safe to interpolate into a cache glob: no path separators or
# traversal segments (SEC-5).
_PROVIDER_ID_RE = re.compile(r"^[a-z0-9-]+$")


# Calendar bounds ``(start_month, start_day, end_month, end_day)`` of each quarter,
# indexed by quarter number. Quarter-end months (Mar/Jun/Sep/Dec) have fixed last
# days, so no leap-year handling is needed.
_QUARTER_BOUNDS = {
    1: (1, 1, 3, 31),
    2: (4, 1, 6, 30),
    3: (7, 1, 9, 30),
    4: (10, 1, 12, 31),
}


def quarter_period(year: int, quarter: int) -> tuple[date, date, str]:
    """Return the calendar bounds and label for a calendar quarter.

    Quarters follow the standard calendar convention: Q1 is Jan 1..Mar 31, Q2 is
    Apr 1..Jun 30, Q3 is Jul 1..Sep 30, and Q4 is Oct 1..Dec 31. Used by quarterly
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

    newest = max(candidates, key=lambda p: p.stat().st_mtime)
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


def filter_records_by_window(
    records: Sequence[SourceRecord],
    *,
    since: Optional[date] = None,
    until: Optional[date] = None,
    years: Optional[int] = None,
    default_years: int = 10,
) -> list[SourceRecord]:
    """Trim parsed records to a request window keyed on ``period_start``.

    Reproduces the shared window semantics of the quarterly / annual providers: with
    no explicit ``until`` the window ends at the latest ``period_start`` present in the
    data (missing periods are never synthesised), and with no explicit ``since`` it
    spans ``years`` (or ``default_years`` when ``years`` is unset or zero) back from
    that end, anchored to January 1 of the resulting year. Only records already present
    are kept - nothing is fabricated or interpolated. Pure over its inputs: no network,
    no database.

    :param records: The parsed source records to filter.
    :param since: The inclusive lower bound, or ``None`` to derive it from the window
        span ending at ``until``.
    :param until: The inclusive upper bound, or ``None`` to use the latest
        ``period_start`` present in ``records``.
    :param years: The window span in years when ``since`` is ``None``; ``None`` or
        zero falls back to ``default_years``.
    :param default_years: The span used when neither ``since`` nor a positive ``years``
        is supplied.
    :returns: The subset whose ``period_start`` falls in ``[since, until]``, as a new
        list; an empty input yields an empty list.
    """
    if not records:
        return list(records)
    window_end = until or max(record.period_start for record in records)
    if since is not None:
        window_start = since
    else:
        span = years or default_years
        window_start = date(window_end.year - span, 1, 1)
    return [record for record in records if window_start <= record.period_start <= window_end]


def compute_competition_ranks(items: Sequence[tuple[str, float]]) -> dict[str, int]:
    """Assign standard competition ranks (1, 2, 2, 4) over ``(id, value)`` pairs.

    Ranks a single group (e.g. one period) by value in descending order, so the
    highest value is rank 1. Equal values share a rank and the next distinct value
    skips the tied positions, yielding the ``1, 2, 2, 4`` competition pattern. Ties are
    broken by ascending id purely so the ordering is deterministic; tied items still
    receive the same rank regardless of that order. Value equality is exact float
    equality, matching the duplicated provider implementations. Pure over its inputs.

    :param items: The ``(id, value)`` pairs to rank; ids should be unique within the
        group (a repeated id keeps its last-seen rank).
    :returns: A mapping of each id to its competition rank; empty for empty input.
    """
    ordered = sorted(items, key=lambda item: (-item[1], item[0]))
    ranks: dict[str, int] = {}
    current_rank = 0
    previous_value: Optional[float] = None
    for index, (identifier, value) in enumerate(ordered, start=1):
        if previous_value is None or value != previous_value:
            current_rank = index
            previous_value = value
        ranks[identifier] = current_rank
    return ranks


def validate_positive_ranks(
    observations: Sequence[Observation],
    report: ValidationReport,
    *,
    metric_id: Optional[str] = None,
    code: str = "rank_positive",
    severity: Severity = Severity.ERROR,
    message: Optional[Callable[[Observation], str]] = None,
) -> None:
    """Flag observations whose ``rank`` is present but not strictly positive.

    Appends one issue per offending observation to ``report``; a ``None`` rank is
    never flagged (missing data stays missing). When ``metric_id`` is given only
    observations carrying that exact metric are checked, otherwise every observation
    is. The default message matches the wording shared by the rank-checking providers;
    pass ``message`` to reproduce a provider's own phrasing verbatim.

    :param observations: The observations to check.
    :param report: The report to append issues to (mutated in place).
    :param metric_id: When set, only observations with this metric id are checked.
    :param code: The issue code recorded for each violation.
    :param severity: The issue severity recorded for each violation.
    :param message: Optional callable building the issue message from the offending
        observation; defaults to ``"{language_id} rank must be positive"``.
    :returns: ``None``; ``report`` is mutated in place.
    """
    for observation in observations:
        if metric_id is not None and observation.metric_id != metric_id:
            continue
        if observation.rank is not None and observation.rank <= 0:
            text = message(observation) if message is not None else f"{observation.language_id} rank must be positive"
            report.add(severity, code, text)


def validate_bounded_values(
    observations: Sequence[Observation],
    report: ValidationReport,
    *,
    code: str,
    metric_id: Optional[str] = None,
    min_value: float = 0.0,
    max_value: float = 100.0,
    severity: Severity = Severity.ERROR,
    message: Optional[Callable[[Observation], str]] = None,
) -> None:
    """Flag observations whose ``value`` falls outside ``[min_value, max_value]``.

    Appends one issue per offending observation to ``report``; a ``None`` value is
    never flagged. When ``metric_id`` is given only observations carrying that exact
    metric are checked, otherwise every observation is (some providers bound every
    metric). The bound is inclusive on both ends. Pass ``message`` to reproduce a
    provider's own phrasing verbatim.

    :param observations: The observations to check.
    :param report: The report to append issues to (mutated in place).
    :param code: The issue code recorded for each violation.
    :param metric_id: When set, only observations with this metric id are checked.
    :param min_value: The inclusive lower bound.
    :param max_value: The inclusive upper bound.
    :param severity: The issue severity recorded for each violation.
    :param message: Optional callable building the issue message from the offending
        observation; defaults to
        ``"{language_id} value outside {min}..{max} at {period_label}"``.
    :returns: ``None``; ``report`` is mutated in place.
    """
    for observation in observations:
        if metric_id is not None and observation.metric_id != metric_id:
            continue
        value = observation.value
        if value is not None and not min_value <= value <= max_value:
            if message is not None:
                text = message(observation)
            else:
                text = f"{observation.language_id} value outside {min_value}..{max_value} at {observation.period_label}"
            report.add(severity, code, text)


def validate_unique_observations(
    observations: Sequence[Observation],
    report: ValidationReport,
    *,
    code: str = "duplicate_language_period",
    severity: Severity = Severity.ERROR,
    message: Optional[Callable[[Observation], str]] = None,
) -> None:
    """Flag repeated ``(language_id, period_start, metric_id)`` triples.

    Appends one issue for each observation whose natural key has already been seen in
    ``observations``; the first occurrence of a key is never flagged. This mirrors the
    upsert natural key used by the store, so a duplicate here would collide on upsert.
    Pass ``message`` to reproduce a provider's own phrasing verbatim.

    :param observations: The observations to check.
    :param report: The report to append issues to (mutated in place).
    :param code: The issue code recorded for each violation.
    :param severity: The issue severity recorded for each violation.
    :param message: Optional callable building the issue message from the duplicate
        observation; defaults to
        ``"duplicate language/period metric for {language_id} {period_label}"``.
    :returns: ``None``; ``report`` is mutated in place.
    """
    seen: set[tuple[str, date, str]] = set()
    for observation in observations:
        key = (observation.language_id, observation.period_start, observation.metric_id)
        if key in seen:
            if message is not None:
                text = message(observation)
            else:
                text = f"duplicate language/period metric for {observation.language_id} {observation.period_label}"
            report.add(severity, code, text)
        seen.add(key)


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
