from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Sequence
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

from langrank.errors import FetchError, ParseError, ProviderError
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
from langrank.normalization import LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import load_cached_payload, payload_from_content, quarter_period
from langrank.util.http import HttpClientFactory

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "github"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "github-v1"

#: Homepage for the GitHub language-data landing page.
HOMEPAGE = "https://innovationgraph.github.com/global-metrics/programming-languages"

#: Commits API endpoint resolving the latest commit that touched the languages CSV.
IG_COMMITS_API = "https://api.github.com/repos/github/innovationgraph/commits?path=data/languages.csv&per_page=1"

#: Raw CSV URL template; ``{sha}`` is a validated 40-hex commit SHA (GH-SEC-2).
IG_RAW_URL = "https://raw.githubusercontent.com/github/innovationgraph/{sha}/data/languages.csv"

#: Host that may carry the optional ``GITHUB_TOKEN`` (commits API only) (GH-SEC-1).
API_HOST = "api.github.com"

#: Host serving the raw CSV; the token is never sent here (GH-SEC-1/GH-SEC-3).
RAW_HOST = "raw.githubusercontent.com"

#: Environment variable holding the optional GitHub personal access token.
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

#: A commit SHA must be exactly 40 lowercase hex digits before it is interpolated
#: into the raw download URL path (GH-SEC-2).
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

#: Requests a single innovation-graph fetch issues (1 commits API + 1 raw CSV) (GH-SEC-6).
IG_REQUEST_BUDGET = 2

#: GitHub REST hourly ceiling without a token (per source note).
IG_ANON_HOURLY = 60

#: GitHub REST hourly ceiling with a ``GITHUB_TOKEN`` (per source note).
IG_KEYED_HOURLY = 5000

#: Post-decompression byte ceiling for the raw CSV; sized for the real file
#: (a few MB, growing each quarter) with generous headroom (GH-SEC-3).
IG_MAX_CSV_BYTES = 64_000_000

#: Default backfill span (years) when the request supplies no window.
DEFAULT_YEARS = 10

#: Required CSV columns the innovation-graph parser reads (GH-SEC-5).
_IG_REQUIRED_COLUMNS = ("num_pushers", "language", "iso2_code", "year", "quarter")

#: Cache sidecar extension carrying the pinned commit SHA for offline replay; kept
#: outside :data:`langrank.providers.common._CACHE_EXTENSIONS` so it is never
#: mistaken for the cached CSV artifact itself.
_SIDECAR_EXT = ".meta"

#: Octoverse annual published rank (raw, one edition per year). Lower is better.
METRIC_OCTOVERSE_RANK = "github-octoverse-rank"

#: Innovation Graph quarterly global pusher count (derived sum over economies).
METRIC_IG_PUSHERS = "github-innovation-graph-pushers"

#: Innovation Graph quarterly global share of pushers (derived, percent).
METRIC_IG_SHARE = "github-innovation-graph-share"

#: Innovation Graph quarterly global rank (derived from the share). Lower is better.
METRIC_IG_RANK = "github-innovation-graph-rank"


class GitHubSource(StrEnum):
    """The two independently selectable GitHub variants.

    The variants measure different things and are never conflated: ``octoverse``
    is the annual Octoverse blog-post ranking, ``innovation-graph`` is the
    quarterly Innovation Graph per-economy pusher data aggregated to a global
    series. Each variant owns its own metric IDs.
    """

    OCTOVERSE = "octoverse"
    INNOVATION_GRAPH = "innovation-graph"


#: ``--source`` values that select the default (machine-readable) variant.
_AUTO_SOURCES = frozenset({None, "auto"})


def _resolve_source(value: Optional[str]) -> GitHubSource:
    """Resolve a ``--source`` value to a :class:`GitHubSource` variant.

    ``None`` and ``"auto"`` select :attr:`GitHubSource.INNOVATION_GRAPH` (the
    machine-readable dataset preferred by the plan); the two explicit variant
    names select themselves. The variants are never merged, so an unknown value
    is rejected rather than guessed.

    :param value: The raw ``--source`` flag, or ``None`` when unset.
    :returns: The selected :class:`GitHubSource`.
    :raises ProviderError: If ``value`` is neither ``auto`` nor a known variant.
    """
    if value in _AUTO_SOURCES:
        return GitHubSource.INNOVATION_GRAPH
    try:
        return GitHubSource(value)
    except ValueError as exc:
        valid = ", ".join(["auto", *sorted(source.value for source in GitHubSource)])
        raise ProviderError(f"unknown --source {value!r}; valid sources: {valid}.") from exc


class GitHubProvider:
    """Records GitHub language-popularity signals across two independent variants.

    The provider carries two variants selected with ``--source`` that are never
    conflated with each other, and neither is comparable with RedMonk's
    GitHub-derived component:

    - ``octoverse`` - the annual Octoverse published top-languages ranking
      (raw ``github-octoverse-rank``).
    - ``innovation-graph`` - the quarterly Innovation Graph per-economy pusher
      counts aggregated to a global series (derived
      ``github-innovation-graph-pushers`` / ``-share`` / ``-rank``).

    Variant selection is part of every metric ID, so a query can never silently
    mix the two variants. ``--source auto`` resolves to ``innovation-graph``.

    :ivar provider_id: Stable rating ID used across the pipeline.
    """

    provider_id = _RATING_ID

    def __init__(self, cache_dir: Path, *, http: Optional[HttpClientFactory] = None) -> None:
        """Wire the provider's cache directory, HTTP client and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the ``github``
            subdirectory beneath it.
        :param http: HTTP client factory; injectable so tests can supply an
            ``httpx.MockTransport``. Defaults to a real factory.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._http = http or HttpClientFactory()
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        #: Commit SHA of the payload last produced by :meth:`fetch`, carried into
        #: :meth:`parse` when a cached (artifact-less) payload is replayed.
        self._commit_sha: Optional[str] = None
        #: Request window stashed by :meth:`fetch` and applied in :meth:`parse`.
        self._request_since: Optional[date] = None
        self._request_until: Optional[date] = None
        self._request_years: Optional[int] = None

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: both variants' metrics and caveats.

        Performs no network or database access.

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="GitHub",
            description=(
                "GitHub language popularity across two independent variants: the annual Octoverse "
                "ranking (--source octoverse) and the quarterly Innovation Graph global pusher series "
                "(--source innovation-graph); the two are never conflated."
            ),
            homepage=HOMEPAGE,
            default_metric=METRIC_IG_SHARE,
            native_granularity=Granularity.QUARTER,
            caveats=[
                "Not RedMonk's GitHub component - a different, separately sourced measure.",
                "The octoverse and innovation-graph variants measure different things and are never conflated.",
                "Innovation Graph global values are sums of per-economy cells with >=100 developers (undercount).",
                "Octoverse ranking basis changes between editions.",
                "No chart-derived values - only ranks stated in the Octoverse text/tables are captured.",
            ],
            parser_version=PARSER_VERSION,
            metrics=[
                MetricDefinition(
                    id=METRIC_OCTOVERSE_RANK,
                    rating_id=self.provider_id,
                    display_name="Octoverse rank",
                    unit="rank",
                    higher_is_better=False,
                    description=(
                        "Annual Octoverse published top-languages rank (1 is best); raw, as printed in "
                        "the edition's text/table. The ranking basis changes between editions."
                    ),
                ),
                MetricDefinition(
                    id=METRIC_IG_PUSHERS,
                    rating_id=self.provider_id,
                    display_name="Innovation Graph pushers",
                    unit="count",
                    higher_is_better=True,
                    description=(
                        "Quarterly global count of distinct pushers per language, derived by summing the "
                        "Innovation Graph per-economy cells; cells below 100 developers are suppressed, so "
                        "the sum is an undercount biased against small languages."
                    ),
                ),
                MetricDefinition(
                    id=METRIC_IG_SHARE,
                    rating_id=self.provider_id,
                    display_name="Innovation Graph share (%)",
                    unit="percent",
                    higher_is_better=True,
                    description=(
                        "Quarterly global share of pushers, derived from github-innovation-graph-pushers "
                        "over the total pushers across all published languages that quarter."
                    ),
                ),
                MetricDefinition(
                    id=METRIC_IG_RANK,
                    rating_id=self.provider_id,
                    display_name="Innovation Graph rank",
                    unit="rank",
                    higher_is_better=False,
                    description=(
                        "Quarterly global ordinal rank (1 is best), derived from the Innovation Graph "
                        "share; not comparable with the annual Octoverse rank."
                    ),
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="innovation-graph-global-sum-v1",
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                    description=(
                        "innovation-graph source: global pusher counts are summed over per-economy cells, "
                        "each published only when it has >=100 developers "
                        "(derivation_method='sum_over_economies:suppressed_below_100')."
                    ),
                    source_url="https://github.com/github/innovationgraph",
                ),
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="octoverse-published-rank-v1",
                    valid_from=date(2014, 1, 1),
                    valid_to=None,
                    description=(
                        "octoverse source: ranks are transcribed from the annual Octoverse blog post; the "
                        "ranking basis changes between editions and no value is chart-extracted."
                    ),
                    source_url="https://github.blog/news-insights/octoverse/",
                ),
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw data for the selected variant.

        Resolves ``--source`` to a variant first, so an unknown source is rejected
        here. ``innovation-graph`` (the default) pins the commit SHA via the
        commits API, then downloads the raw CSV host-pinned and size-capped;
        ``--offline`` replays the newest cached CSV and its commit-SHA sidecar.
        Octoverse lands in subtask 07.

        :param request: Fetch parameters (date window, source mode, cache flags).
        :returns: The raw fetch payload whose artifact metadata carries the variant.
        :raises ProviderError: If ``--source`` names an unknown variant.
        :raises FetchError: On a malformed commit SHA, budget overflow, an
            integrity mismatch, or a failed download.
        :raises NotImplementedError: For the Octoverse variant, until subtask 07.
        """
        source = _resolve_source(request.source)
        self._request_since = request.since
        self._request_until = request.until
        self._request_years = request.years
        if source is GitHubSource.INNOVATION_GRAPH:
            return self._fetch_innovation_graph(request)
        raise NotImplementedError("github octoverse fetch lands in subtask 07.")

    def _fetch_innovation_graph(self, request: FetchRequest) -> FetchPayload:
        """Fetch (or replay) the Innovation Graph ``data/languages.csv`` at a pinned SHA.

        Online, exactly two requests are issued (GH-SEC-6): the optional
        ``GITHUB_TOKEN`` is read from the environment and attached only as an
        ``Authorization`` header on the ``api.github.com`` commits call (GH-SEC-1),
        the returned SHA is validated to 40 hex digits (GH-SEC-2), and the raw CSV
        is downloaded from ``raw.githubusercontent.com`` host-pinned, no-redirect
        and size-capped, carrying no credential (GH-SEC-3). The commit SHA and the
        CSV sha256 are recorded in the artifact metadata and a cache sidecar
        (GH-SEC-4). ``--offline`` replays the newest cached CSV.

        :param request: The fetch request (window, cache flags).
        :returns: The raw CSV fetch payload; its artifact metadata carries
            ``commit_sha``, ``csv_sha256`` and ``variant``.
        :raises FetchError: On budget overflow, a malformed SHA, an integrity
            mismatch, or a failed download.
        """
        if request.offline:
            return self._replay_innovation_graph_cache()

        token = os.environ.get(GITHUB_TOKEN_ENV) or None
        ceiling = IG_KEYED_HOURLY if token else IG_ANON_HOURLY
        _ensure_request_budget(IG_REQUEST_BUDGET, ceiling=ceiling, has_token=token is not None)

        headers = {"Authorization": f"Bearer {token}"} if token else None
        commit_sha = _resolve_commit_sha(self._http, headers=headers)
        raw_url = IG_RAW_URL.format(sha=commit_sha)
        content = self._http.get_capped_bytes(raw_url, allowed_host=RAW_HOST, max_bytes=IG_MAX_CSV_BYTES)

        csv_sha256 = hashlib.sha256(content).hexdigest()
        self._commit_sha = commit_sha
        payload = payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=raw_url,
            content=content,
            mime_type="text/csv",
            metadata_json={
                "variant": GitHubSource.INNOVATION_GRAPH.value,
                "commit_sha": commit_sha,
                "csv_sha256": csv_sha256,
                "source_document_id": f"github-innovation-graph@{commit_sha}",
                "requests_made": IG_REQUEST_BUDGET,
            },
            no_cache=request.no_cache,
        )
        if payload.artifact is not None:
            self._write_cache_sidecar(csv_sha256, commit_sha)
        return payload

    def _replay_innovation_graph_cache(self) -> FetchPayload:
        """Replay the newest cached Innovation Graph CSV, verifying its integrity.

        Reuses :func:`load_cached_payload` (which keeps its SEC-5 containment
        checks) for the CSV bytes, then recovers the pinned commit SHA from the
        sidecar written at fetch time and re-checks the CSV sha256 (GH-SEC-4)
        before the SHA is validated (GH-SEC-2) and stashed for :meth:`parse`.

        :returns: The cached CSV payload (``artifact`` is ``None``, a replay mints
            no new artifact); the commit SHA is carried on the provider.
        :raises FetchError: If the sidecar is missing, the SHA is malformed, or the
            cached bytes fail their sha256 integrity check.
        """
        cached = load_cached_payload(provider_id=self.provider_id, cache_dir=self._cache_dir)
        csv_sha256 = hashlib.sha256(cached.content).hexdigest()
        sidecar = self._cache_dir / f"{self.provider_id}-{csv_sha256[:12]}{_SIDECAR_EXT}"
        if not sidecar.is_file():
            raise FetchError(
                "cached github innovation-graph artifact is missing its commit-sha sidecar; re-fetch online."
            )
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FetchError("cached github innovation-graph sidecar is not valid JSON.") from exc
        if not isinstance(meta, dict) or meta.get("csv_sha256") != csv_sha256:
            raise FetchError("cached github innovation-graph CSV failed its sha256 integrity check.")
        self._commit_sha = _validate_commit_sha(str(meta.get("commit_sha", "")))
        return cached

    def _write_cache_sidecar(self, csv_sha256: str, commit_sha: str) -> None:
        """Persist the pinned commit SHA next to the cached CSV for offline replay.

        The sidecar filename embeds the CSV sha256 prefix so
        :meth:`_replay_innovation_graph_cache` can locate it deterministically from
        the replayed bytes; it uses a non-cache extension so it is never returned as
        the artifact itself.

        :param csv_sha256: Full sha256 of the cached CSV bytes.
        :param commit_sha: The validated 40-hex commit SHA to record.
        """
        sidecar = self._cache_dir / f"{self.provider_id}-{csv_sha256[:12]}{_SIDECAR_EXT}"
        sidecar.write_text(
            json.dumps({"commit_sha": commit_sha, "csv_sha256": csv_sha256}, sort_keys=True),
            encoding="utf-8",
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw Innovation Graph CSV payload into per-economy source records.

        The commit SHA is read from the artifact metadata when present, else from
        the value stashed by :meth:`fetch` (offline replay). Parsing itself is a
        pure function of the bytes and SHA; the request window
        (``since``/``until``/``years``) is applied afterwards by ``period_start``.

        :param raw: The raw fetch payload (Innovation Graph CSV).
        :returns: Source records, one per CSV row, within the request window.
        :raises ParseError: If the commit SHA is unknown or the CSV is malformed.
        """
        commit_sha: Optional[str] = None
        if raw.artifact is not None:
            candidate = raw.artifact.metadata_json.get("commit_sha")
            commit_sha = str(candidate) if candidate is not None else None
        commit_sha = commit_sha or self._commit_sha
        if commit_sha is None:
            raise ParseError("github payload has no commit sha; parse requires a fetched innovation-graph payload.")
        records = _parse_innovation_graph(raw.content, commit_sha=commit_sha)
        return self._filter_window(records)

    def _filter_window(self, records: list[SourceRecord]) -> list[SourceRecord]:
        """Filter parsed records to the request window by ``period_start``.

        With no explicit ``--until`` the window ends at the latest quarter present
        in the data; with no explicit ``--since`` it spans ``--years`` (default
        :data:`DEFAULT_YEARS`) back from that end. Missing quarters are never
        synthesised - only present rows are kept.

        :param records: Records from :func:`_parse_innovation_graph`.
        :returns: The subset whose ``period_start`` falls in ``[since, until]``.
        """
        if not records:
            return records
        until = self._request_until or max(record.period_start for record in records)
        if self._request_since is not None:
            since = self._request_since
        else:
            span = self._request_years or DEFAULT_YEARS
            since = date(until.year - span, 1, 1)
        return [record for record in records if since <= record.period_start <= until]

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations (implemented in subtasks 06/07).

        :param records: Parsed source records.
        :returns: Canonical observations.
        :raises NotImplementedError: Always, until subtasks 06/07 land normalization.
        """
        raise NotImplementedError("github normalize lands in subtasks 06/07.")

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations with named codes (implemented in subtask 08).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Always, until subtask 08 lands validation.
        """
        raise NotImplementedError("github validate lands in subtask 08.")


def _ensure_request_budget(planned: int, *, ceiling: int, has_token: bool) -> None:
    """Refuse to start a fetch whose planned request count exceeds the hourly ceiling.

    The Innovation Graph fetch issues at most :data:`IG_REQUEST_BUDGET` requests, so
    this guard is defence in depth: it never issues a request itself and rejects a
    plan before the first call (GH-SEC-6).

    :param planned: Number of requests the fetch intends to make.
    :param ceiling: Applicable GitHub hourly ceiling.
    :param has_token: Whether a ``GITHUB_TOKEN`` is set (affects the guidance only).
    :raises FetchError: If ``planned`` exceeds ``ceiling``.
    """
    if planned > ceiling:
        hint = "" if has_token else f" or set {GITHUB_TOKEN_ENV}"
        raise FetchError(
            f"planned {planned} GitHub requests exceed the hourly ceiling of {ceiling}; "
            f"narrow the window (--since/--until/--years){hint}."
        )


def _validate_commit_sha(sha: str) -> str:
    """Return ``sha`` only if it is exactly 40 lowercase hex digits (GH-SEC-2).

    Guards the untrusted commit SHA before it is interpolated into the raw
    download URL path, rejecting traversal/ref-confusion payloads.

    :param sha: The candidate commit SHA from the commits API or a cache sidecar.
    :returns: The validated SHA, unchanged.
    :raises FetchError: If ``sha`` is not a 40-char lowercase hex string.
    """
    if not _SHA_RE.match(sha):
        raise FetchError(f"github commit sha is not a 40-char hex string: {sha!r}")
    return sha


def _resolve_commit_sha(http: HttpClientFactory, *, headers: Optional[dict[str, str]] = None) -> str:
    """Resolve the latest commit SHA touching ``data/languages.csv`` via the commits API.

    Issues a single host-pinned, no-redirect, size-capped request to
    ``api.github.com`` (GH-SEC-3); the optional ``Authorization`` header is the only
    place a token may travel (GH-SEC-1). The returned SHA is validated (GH-SEC-2).

    :param http: The HTTP client factory (injected; may wrap a mock transport).
    :param headers: Optional ``Authorization`` header carrying ``GITHUB_TOKEN``.
    :returns: The validated 40-hex commit SHA.
    :raises FetchError: If the response shape is wrong or the SHA is malformed.
    """
    data = http.get_json(IG_COMMITS_API, allowed_host=API_HOST, headers=headers)
    if not isinstance(data, list) or not data:
        raise FetchError("github commits API returned no commit for data/languages.csv.")
    first = data[0]
    if not isinstance(first, dict):
        raise FetchError("github commits API returned a malformed commit entry.")
    sha = first.get("sha")
    if not isinstance(sha, str):
        raise FetchError("github commits API commit entry has no string 'sha'.")
    return _validate_commit_sha(sha)


def _parse_innovation_graph(content: bytes, *, commit_sha: str) -> list[SourceRecord]:
    """Parse the Innovation Graph ``languages.csv`` into one source record per row.

    Untrusted-input hardening (GH-SEC-5): the parser is the stdlib ``csv`` module
    (never ``eval``); a missing required column raises a :class:`ParseError` naming
    it; ``num_pushers`` must be a non-negative integer, ``year`` a plausible
    integer and ``quarter`` in ``1..4``; any per-row ``ValueError``/``KeyError`` is
    wrapped in a :class:`ParseError`. Each record preserves the raw Linguist
    language string and carries ``iso2_code``, ``commit_sha`` and ``variant`` in
    its metadata; the SHA-pinned raw URL is the ``source_url``.

    :param content: The raw CSV bytes.
    :param commit_sha: The validated 40-hex commit SHA the CSV was pinned to.
    :returns: One :class:`SourceRecord` per CSV row, in file order.
    :raises ParseError: On a decoding error, a missing required column, or a
        malformed / out-of-range cell.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("github innovation-graph CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(text.splitlines())
    fieldnames = reader.fieldnames or []
    for column in _IG_REQUIRED_COLUMNS:
        if column not in fieldnames:
            raise ParseError(f"github innovation-graph CSV is missing required column {column!r}.")
    source_url = IG_RAW_URL.format(sha=commit_sha)
    records: list[SourceRecord] = []
    for row in reader:
        records.append(_ig_record_from_row(row, commit_sha=commit_sha, source_url=source_url))
    return records


def _ig_record_from_row(row: dict[str, Any], *, commit_sha: str, source_url: str) -> SourceRecord:
    """Build one quarterly :class:`SourceRecord` from a validated CSV row (GH-SEC-5).

    :param row: A CSV row keyed by column name.
    :param commit_sha: The pinned commit SHA, echoed into record metadata.
    :param source_url: The SHA-pinned raw URL used as ``source_url``.
    :returns: A ``github-innovation-graph-pushers`` source record.
    :raises ParseError: If a numeric cell is missing, non-numeric or out of range.
    """
    try:
        num_pushers = int(row["num_pushers"])
        year = int(row["year"])
        quarter = int(row["quarter"])
        language = row["language"]
        iso2_code = row["iso2_code"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"github innovation-graph row is malformed: {row!r}") from exc
    if num_pushers < 0:
        raise ParseError(f"github innovation-graph num_pushers must be non-negative: {row!r}")
    if quarter not in (1, 2, 3, 4):
        raise ParseError(f"github innovation-graph quarter must be in 1..4: {row!r}")
    if not 2000 <= year <= 2100:
        raise ParseError(f"github innovation-graph year is implausible: {row!r}")
    period_start, period_end, period_label = quarter_period(year, quarter)
    return SourceRecord(
        rating_id=_RATING_ID,
        metric_id=METRIC_IG_PUSHERS,
        language=language,
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        granularity=Granularity.QUARTER,
        rank=None,
        value=float(num_pushers),
        unit="count",
        source_url=source_url,
        metadata={"iso2_code": iso2_code, "commit_sha": commit_sha, "variant": GitHubSource.INNOVATION_GRAPH.value},
    )
