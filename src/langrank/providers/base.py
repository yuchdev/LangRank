from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from copy import copy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import ClassVar, Optional, Protocol, runtime_checkable

from langrank.errors import LangRankError
from langrank.models import (
    FetchRequest,
    Granularity,
    Observation,
    ProviderMetadata,
    RawArtifact,
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import LanguageNormalizer


@dataclass(frozen=True)
class FetchPayload:
    artifact: Optional[RawArtifact]
    content: bytes


@runtime_checkable
class RatingProvider(Protocol):
    provider_id: str

    def metadata(self) -> ProviderMetadata: ...

    def fetch(self, request: FetchRequest) -> FetchPayload: ...

    def parse(self, raw: FetchPayload) -> list[SourceRecord]: ...

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]: ...

    def validate(self, observations: Sequence[Observation]) -> ValidationReport: ...

    def upstream_latest_period(self) -> Optional[str]: ...


class BaseRatingProvider(ABC):
    """Abstract base for rating providers holding the state every provider shares.

    Concentrates the boilerplate each provider previously duplicated: the
    per-provider cache subdirectory, the shared :class:`LanguageNormalizer`, the
    acquisition timestamp, the unmapped-label accumulator, and the request window
    stashed by :meth:`fetch` and applied in :meth:`parse`. It also supplies a
    concrete :meth:`upstream_latest_period` derived from local artifacts only (no
    network). Concrete providers implement the five pipeline methods and satisfy the
    :class:`RatingProvider` structural protocol.

    :cvar provider_id: Stable rating ID used across the pipeline and as the cache
        subdirectory name; every concrete subclass must define it.
    :ivar last_unmapped: Source labels the last :meth:`normalize` call could not
        resolve to a canonical language; populated by :meth:`_record_unmapped` and
        surfaced by each provider's ``validate``. Reset at the start of every
        ``normalize`` call by the subclass.
    """

    provider_id: ClassVar[str]

    def __init__(self, cache_dir: Path) -> None:
        """Wire the shared provider state; performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the
            ``{provider_id}`` subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        #: Request window stashed by :meth:`fetch` and applied in :meth:`parse`; all
        #: default to ``None`` so an import path that never calls ``fetch`` keeps
        #: every parsed record.
        self._request_since: Optional[date] = None
        self._request_until: Optional[date] = None
        self._request_years: Optional[int] = None
        #: Source labels the last :meth:`normalize` could not map (never guessed).
        self.last_unmapped: list[str] = []

    def _stash_request_window(self, request: FetchRequest) -> None:
        """Record the request's date window for :meth:`_filter_window` to apply.

        :param request: The fetch request whose ``since`` / ``until`` / ``years``
            window is stashed for use during :meth:`parse`.
        """
        self._request_since = request.since
        self._request_until = request.until
        self._request_years = request.years

    def _filter_window(self, records: list[SourceRecord], *, default_years: int = 10) -> list[SourceRecord]:
        """Trim parsed records to the stashed request window by ``period_start``.

        Delegates to :func:`langrank.providers.common.filter_records_by_window`
        using the window stashed by :meth:`_stash_request_window`; missing periods
        are never synthesised and nothing is fabricated.

        :param records: The parsed source records to filter.
        :param default_years: The look-back span used when neither ``since`` nor a
            positive ``years`` was stashed.
        :returns: The subset whose ``period_start`` falls in the request window.
        """
        from langrank.providers.common import filter_records_by_window

        return filter_records_by_window(
            records,
            since=self._request_since,
            until=self._request_until,
            years=self._request_years,
            default_years=default_years,
        )

    def _record_unmapped(self, label: str) -> None:
        """Record ``label`` as unmapped, preserving order and skipping duplicates.

        :param label: The source language label that resolved to no canonical
            language; appended to :attr:`last_unmapped` only if not already present.
        """
        if label not in self.last_unmapped:
            self.last_unmapped.append(label)

    def _capture_payload_timestamp(self, raw: FetchPayload) -> None:
        """Use the artifact's acquisition time, or the current local-import time.

        :param raw: Payload whose records will be normalized next.
        """
        self._retrieved_at = raw.artifact.retrieved_at if raw.artifact is not None else datetime.now(UTC)

    def _bundled_snapshot_payload(self) -> Optional[FetchPayload]:
        """Return a repo-bundled snapshot payload for :meth:`upstream_latest_period`.

        The default returns ``None`` (no bundled snapshot). Providers that ship a
        curated dataset override this to return its bytes so ``langrank status`` can
        report an upstream period without any network access.

        :returns: A bundled :class:`FetchPayload`, or ``None`` when the provider
            ships none.
        """
        return None

    def _local_snapshot_payloads(self) -> Iterator[FetchPayload]:
        """Yield the local snapshot payloads to probe, most authoritative first.

        Yields the provider's own cache (offline replay of the last fetched bytes)
        when present, then the repo-bundled snapshot from
        :meth:`_bundled_snapshot_payload` when the provider ships one. Payloads are
        produced lazily, so the bundled snapshot is only read when the cache did not
        already answer. Never touches the network.

        :returns: An iterator over the available local payloads (possibly empty).
        """
        from langrank.providers.common import load_cached_payload

        try:
            yield load_cached_payload(provider_id=self.provider_id, cache_dir=self._cache_dir)
        except LangRankError:
            pass
        bundled = self._bundled_snapshot_payload()
        if bundled is not None:
            yield bundled

    def upstream_latest_period(self) -> Optional[str]:
        """Report the latest period available from local artifacts, without network.

        Derives the maximum ``period_start`` from the first local snapshot
        (:meth:`_local_snapshot_payloads`: cache, then bundled snapshot) that this
        provider's :meth:`parse` turns into at least one record. A cached artifact
        that fails to parse with a :class:`~langrank.errors.LangRankError` or yields
        no records falls through to the bundled snapshot. The period is formatted by
        :meth:`metadata`'s ``native_granularity``:
        :attr:`~langrank.models.Granularity.YEAR` yields ``"YYYY"`` and every finer
        granularity yields ``"YYYY-MM"`` so ``StatusService``'s ``startswith``
        comparison against the latest local observation keeps working. Returns
        ``None`` when no local snapshot yields records; exceptions other than
        :class:`~langrank.errors.LangRankError` are not masked.

        Parsing runs on a shallow copy with its request window cleared, so a
        status probe neither inherits a previous fetch window nor changes the
        original provider's pending parser state. Referenced acquisition clients
        and normalizers are shared but are not used mutably by snapshot parsers.

        :returns: The latest local period label, or ``None`` when unavailable.
        """
        probe = copy(self)
        probe._stash_request_window(FetchRequest())
        for payload in probe._local_snapshot_payloads():
            try:
                records = probe.parse(payload)
            except LangRankError:
                continue
            if not records:
                continue
            latest = max(record.period_start for record in records)
            if self.metadata().native_granularity is Granularity.YEAR:
                return f"{latest.year:04d}"
            return f"{latest.year:04d}-{latest.month:02d}"
        return None

    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata."""

    @abstractmethod
    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Acquire the raw payload for ``request``."""

    @abstractmethod
    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw payload into source records."""

    @abstractmethod
    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into canonical observations."""

    @abstractmethod
    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations and return a report."""


@runtime_checkable
class SupportsRawImport(Protocol):
    """Optional provider capability: stream a local raw file into source records.

    A provider implements this when ``langrank import`` should ingest a large,
    untrusted, operator-supplied file by **streaming** it under explicit byte and
    row caps, rather than through the default whole-file ``path.read_bytes()`` path
    (which loads the entire file into memory). ``cli.py`` detects the capability at
    runtime via :func:`isinstance` and dispatches to :meth:`import_path`; providers
    without it keep the existing bytes path unchanged. The method owns all parsing
    business logic - the CLI only dispatches.
    """

    provider_id: str

    def import_path(self, path: Path) -> list[SourceRecord]:
        """Stream ``path`` and return the parsed source records (capped, no full read)."""
        ...
