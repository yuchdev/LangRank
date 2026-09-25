from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import replace
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
    Severity,
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import GITHUB_NON_LANGUAGES, LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import (
    build_observation,
    load_cached_payload,
    payload_from_content,
    quarter_period,
)
from langrank.util.http import HttpClientFactory

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "github"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "github-v1"

#: Homepage for the GitHub language-data landing page.
HOMEPAGE = "https://innovationgraph.github.com/global-metrics/programming-languages"

#: Landing page for the annual Octoverse reports; each CSV row carries its own
#: per-edition ``source_url``, so this is only the artifact-level provenance URL.
OCTOVERSE_HOMEPAGE = "https://octoverse.github.com/"

#: ``--source`` value that would request experimental chart-pixel extraction. It is
#: deliberately **not** implemented (``--allow-chart-extraction`` is out of scope);
#: requesting it is refused with a :class:`ProviderError` (GH-SEC-8).
OCTOVERSE_CHART_SOURCE = "octoverse-chart"

#: Required columns of the curated Octoverse rankings CSV (GH-SEC-8 shape check).
_OCTOVERSE_REQUIRED_COLUMNS = ("year", "rank", "language", "ranking_basis", "source_url", "published_at")

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

#: Derivation method for the global pusher sum. The ``suppressed_below_100`` suffix
#: records that GitHub publishes an economy/language cell only when it has >=100
#: developers, so every global sum is an undercount biased against small languages;
#: the shortfall is flagged here, never corrected or interpolated.
IG_SUM_METHOD = "sum_over_economies:suppressed_below_100"

#: Derivation method for the global share. The denominator is the total pushers
#: across *all* published Linguist languages that quarter, including unmapped and
#: non-language names, so shares are comparable across quarters.
IG_SHARE_METHOD = "share_of_all_published_language_pushers"

#: Derivation method for the global rank: competition ranking on the global pusher
#: share, computed over mapped languages only.
IG_RANK_METHOD = "rank_by_global_pushers"

#: Per-economy developer floor GitHub applies before publishing a cell; recorded in
#: aggregate metadata so the undercount stays traceable.
IG_SUPPRESSION_THRESHOLD = 100

#: Population string stamped on every derived Innovation Graph observation: the
#: global aggregate sums only cells for economies with >=100 developers.
IG_POPULATION = "global (economies ≥100 developers)"

#: Metric IDs owned by the innovation-graph variant; every one is a derived global
#: aggregate, so validation requires ``is_derived=True`` on each (GH-08).
_IG_METRIC_IDS = frozenset({METRIC_IG_PUSHERS, METRIC_IG_SHARE, METRIC_IG_RANK})


def _variant_of(metric_id: str) -> Optional[str]:
    """Resolve which variant a metric ID belongs to for validation messages.

    :param metric_id: The observation's metric ID.
    :returns: :attr:`GitHubSource.OCTOVERSE` / :attr:`GitHubSource.INNOVATION_GRAPH`
        value for a known metric, else ``None`` (an unrecognised metric).
    """
    if metric_id == METRIC_OCTOVERSE_RANK:
        return GitHubSource.OCTOVERSE.value
    if metric_id in _IG_METRIC_IDS:
        return GitHubSource.INNOVATION_GRAPH.value
    return None


class OctoverseBasis(StrEnum):
    """The ranking basis GitHub used for a given Octoverse edition.

    The basis is **not** constant across editions and must be recorded per edition,
    because ranks under different bases are not directly comparable (a language ranked
    by total contributors is not the same measurement as one ranked by distinct
    monthly contributors). Each distinct basis present in the curated CSV yields one
    :class:`~langrank.models.MethodologyNote` (see :meth:`GitHubProvider.metadata`).

    :cvar CONTRIBUTORS: Editions ranked by the number of contributors using each
        language (e.g. Octoverse 2024, "the most used language on GitHub").
    :cvar MONTHLY_CONTRIBUTORS: Editions ranked by distinct monthly contributors
        (e.g. Octoverse 2025, TypeScript at #1).
    """

    CONTRIBUTORS = "contributors"
    MONTHLY_CONTRIBUTORS = "monthly_contributors"


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
    :ivar last_unmapped: Linguist language names the last :meth:`normalize` call
        could not resolve to a canonical language; skipped rather than guessed
        (documented :data:`GITHUB_NON_LANGUAGES` names are excluded), and reported
        by validation (subtask 08).
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
        #: Curated, repo-committed Octoverse rankings CSV read at ``fetch()`` time
        #: (manual curation only, no network - GH-SEC-8).
        self._octoverse_data_path = Path(__file__).parent / "data" / "github_octoverse.csv"
        #: Variant selected by the last :meth:`fetch`, used to route :meth:`parse`
        #: when a cached (artifact-less) payload is replayed.
        self._source: Optional[GitHubSource] = None
        #: Commit SHA of the payload last produced by :meth:`fetch`, carried into
        #: :meth:`parse` when a cached (artifact-less) payload is replayed.
        self._commit_sha: Optional[str] = None
        #: Request window stashed by :meth:`fetch` and applied in :meth:`parse`.
        self._request_since: Optional[date] = None
        self._request_until: Optional[date] = None
        self._request_years: Optional[int] = None
        #: Linguist names the last :meth:`normalize` could not map (never guessed).
        self.last_unmapped: list[str] = []

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
                "(--source innovation-graph); the two are never conflated. `fetch all` fetches only the "
                "default innovation-graph variant - run `langrank fetch github --source octoverse` for Octoverse."
            ),
            homepage=HOMEPAGE,
            default_metric=METRIC_IG_SHARE,
            native_granularity=Granularity.QUARTER,
            caveats=[
                "Not RedMonk's GitHub component - a different, separately sourced measure.",
                "The octoverse and innovation-graph variants measure different things and are never conflated.",
                "Innovation Graph global values are sums of per-economy cells with >=100 developers (undercount).",
                "Innovation Graph counts a developer once per economy they push from, so global sums may "
                "double-count multi-economy developers; not corrected.",
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
                *self._octoverse_methodology_notes(),
            ],
        )

    def _octoverse_methodology_notes(self) -> list[MethodologyNote]:
        """Build one :class:`MethodologyNote` per distinct Octoverse ranking basis.

        Reads the curated rankings CSV (no network) and groups its rows by
        ``ranking_basis``; each basis yields a single note whose ``valid_from`` /
        ``valid_to`` span the earliest and latest edition years that used it. This
        keeps the "ranks are not comparable across bases" caveat traceable to the
        exact editions it covers, and it stays in lock-step with the CSV rather than
        being hand-maintained. If the bundled CSV is absent the provider emits no
        Octoverse note rather than fabricating one.

        :returns: One note per distinct ranking basis, ordered by basis value.
        """
        if not self._octoverse_data_path.is_file():
            return []
        rows = _parse_octoverse(self._octoverse_data_path.read_bytes())
        spans: dict[str, tuple[int, int, str]] = {}
        for record in rows:
            basis = str(record.metadata["ranking_basis"])
            year = record.period_start.year
            low, high, url = spans.get(basis, (year, year, record.source_url))
            spans[basis] = (min(low, year), max(high, year), url)
        return [
            MethodologyNote(
                rating_id=self.provider_id,
                methodology_version=f"octoverse-{basis}-v1",
                valid_from=date(low, 1, 1),
                valid_to=date(high, 12, 31),
                description=(
                    f"octoverse source: ranks transcribed from the annual Octoverse report text/tables, "
                    f"ranked by {basis.replace('_', ' ')} for editions {low}-{high}; ranks under different "
                    f"bases are not directly comparable and no value is chart-extracted."
                ),
                source_url=url,
            )
            for basis, (low, high, url) in sorted(spans.items())
        ]

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw data for the selected variant.

        Resolves ``--source`` to a variant first, so an unknown source is rejected
        here. ``innovation-graph`` (the default) pins the commit SHA via the
        commits API, then downloads the raw CSV host-pinned and size-capped;
        ``--offline`` replays the newest cached CSV and its commit-SHA sidecar.
        Octoverse lands in subtask 07.

        :param request: Fetch parameters (date window, source mode, cache flags).
        :returns: The raw fetch payload whose artifact metadata carries the variant.
        :raises ProviderError: If ``--source`` names an unknown variant or requests
            unsupported Octoverse chart-pixel extraction.
        :raises FetchError: On a malformed commit SHA, budget overflow, an
            integrity mismatch, or a failed download.
        """
        if request.source == OCTOVERSE_CHART_SOURCE:
            raise ProviderError(
                "octoverse chart-pixel extraction is not implemented (--allow-chart-extraction is out "
                "of scope); only ranks printed in the Octoverse text/tables are captured."
            )
        source = _resolve_source(request.source)
        self._source = source
        self._request_since = request.since
        self._request_until = request.until
        self._request_years = request.years
        if source is GitHubSource.INNOVATION_GRAPH:
            return self._fetch_innovation_graph(request)
        return self._fetch_octoverse(request)

    def _fetch_octoverse(self, request: FetchRequest) -> FetchPayload:
        """Read the curated Octoverse rankings CSV bundled in the repository.

        Manual curation only: no network request is issued (GH-SEC-8, request budget
        0), the bytes come from the repo-committed
        ``providers/data/github_octoverse.csv`` whose integrity is assured by code
        review. The artifact metadata flags the ``octoverse`` variant and records the
        ``manual_curation`` provenance so the acquisition mode stays traceable; the
        per-edition ``source_url`` lives on each parsed record instead.

        :param request: The fetch request (only ``no_cache`` is honoured here).
        :returns: The raw CSV payload for the Octoverse variant.
        """
        content = self._octoverse_data_path.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=OCTOVERSE_HOMEPAGE,
            content=content,
            mime_type="text/csv",
            metadata_json={
                "variant": GitHubSource.OCTOVERSE.value,
                "provenance": "manual_curation",
                "source_document_id": "github-octoverse",
            },
            no_cache=request.no_cache,
        )

    def _fetch_innovation_graph(self, request: FetchRequest) -> FetchPayload:
        """Fetch (or replay) the Innovation Graph ``data/languages.csv`` at a pinned SHA.

        Online, exactly two requests are issued (GH-SEC-6): the optional
        ``GITHUB_TOKEN`` is read from the environment and attached only as an
        ``Authorization`` header on the ``api.github.com`` commits call (GH-SEC-1),
        the returned SHA is validated to 40 hex digits (GH-SEC-2), and the raw CSV
        is downloaded from ``raw.githubusercontent.com`` host-pinned, no-redirect
        and size-capped, carrying no credential (GH-SEC-3). The commit SHA and the
        CSV sha256 are recorded in the artifact metadata and a cache sidecar
        (GH-SEC-4), alongside the requested quarter window (GH-SEC-9).
        ``--offline`` replays the newest cached CSV.

        :param request: The fetch request (window, cache flags).
        :returns: The raw CSV fetch payload; its artifact metadata carries
            ``commit_sha``, ``csv_sha256``, ``variant`` and the
            ``requested_since`` / ``requested_until`` window.
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
                "requested_since": request.since.isoformat() if request.since else None,
                "requested_until": request.until.isoformat() if request.until else None,
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
        """Parse a raw payload into source records for the payload's variant.

        The variant is read from the artifact metadata when present, else from the
        value stashed by :meth:`fetch` (offline replay), defaulting to
        ``innovation-graph``. Octoverse payloads are parsed by :func:`_parse_octoverse`
        (annual published ranks); Innovation Graph payloads read the pinned commit SHA
        (from artifact metadata or :meth:`fetch`) and are parsed per economy, then
        filtered to the request window - Octoverse ranks are annual editions and are
        never window-filtered.

        :param raw: The raw fetch payload.
        :returns: Source records parsed from the payload.
        :raises ParseError: If the CSV is malformed, or the Innovation Graph commit
            SHA is unknown.
        """
        if self._payload_variant(raw) is GitHubSource.OCTOVERSE:
            return _parse_octoverse(raw.content)
        commit_sha: Optional[str] = None
        if raw.artifact is not None:
            candidate = raw.artifact.metadata_json.get("commit_sha")
            commit_sha = str(candidate) if candidate is not None else None
        commit_sha = commit_sha or self._commit_sha
        if commit_sha is None:
            raise ParseError("github payload has no commit sha; parse requires a fetched innovation-graph payload.")
        records = _parse_innovation_graph(raw.content, commit_sha=commit_sha)
        return self._filter_window(records)

    def _payload_variant(self, raw: FetchPayload) -> GitHubSource:
        """Resolve which variant a raw payload belongs to.

        Prefers the ``variant`` recorded in the artifact metadata (present for a
        freshly fetched, cached payload); falls back to the variant stashed by
        :meth:`fetch` for an offline, artifact-less replay; defaults to
        ``innovation-graph`` when neither is available so a directly constructed
        Innovation Graph payload keeps parsing as before.

        :param raw: The raw fetch payload.
        :returns: The :class:`GitHubSource` variant the payload belongs to.
        """
        if raw.artifact is not None:
            recorded = raw.artifact.metadata_json.get("variant")
            if isinstance(recorded, str):
                try:
                    return GitHubSource(recorded)
                except ValueError:
                    raise ParseError(f"github cached artifact has unknown variant {recorded!r}.") from None
        return self._source or GitHubSource.INNOVATION_GRAPH

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
        """Normalize Innovation Graph per-economy records into a derived global series.

        The per-economy pusher rows are first aggregated to one global cell per
        ``(quarter, Linguist language)`` by :func:`_aggregate_global`; every emitted
        value is therefore ``is_derived=True``. For each mapped language the method
        emits a global pusher count (:data:`IG_SUM_METHOD`), a global share
        (:data:`IG_SHARE_METHOD`) whose denominator is the total pushers across *all*
        published languages that quarter - including unmapped and non-language names -
        and, via :func:`_derive_ig_rank`, a competition rank over mapped languages
        only (:data:`IG_RANK_METHOD`). Unmapped names are skipped and recorded in
        :attr:`last_unmapped`, except documented :data:`GITHUB_NON_LANGUAGES` markup /
        config / data formats, which are skipped silently; either way they still
        count toward the share denominator. The >=100-developer suppression means the
        global sum undercounts, which the derivation method and the aggregate metadata
        (``economies_count`` / ``suppression_threshold``) keep traceable. Missing
        quarters are never interpolated. Pure over its inputs: no network, no database.

        A developer active in two economies in one quarter is counted once per
        economy by GitHub's own data; that double count is documented as a caveat and
        deliberately not corrected here.

        :param records: Parsed Innovation Graph source records from :meth:`parse`.
        :returns: Derived ``pushers`` / ``share`` / ``rank`` observations; empty when
            ``records`` is empty.
        :raises ProviderError: If the records mix the Octoverse and Innovation Graph
            variants, which are never conflated.
        """
        if not records:
            return []
        metric_ids = {record.metric_id for record in records}
        if metric_ids == {METRIC_OCTOVERSE_RANK}:
            return self._normalize_octoverse(records)
        if metric_ids != {METRIC_IG_PUSHERS}:
            raise ProviderError(
                "github normalize cannot mix variants: expected only innovation-graph pusher records or "
                f"only octoverse rank records, got metric ids {sorted(metric_ids)}."
            )
        parser_version = self.metadata().parser_version
        retrieved_at = self._retrieved_at
        aggregated = _aggregate_global(records)
        denominators: dict[date, float] = {}
        for record in aggregated:
            denominators[record.period_start] = denominators.get(record.period_start, 0.0) + (record.value or 0.0)
        self.last_unmapped = []
        observations: list[Observation] = []
        shares: list[tuple[str, SourceRecord]] = []
        for record in aggregated:
            language_id = self._normalizer.try_resolve(record.language, rating_id=self.provider_id)
            if language_id is None:
                if record.language not in GITHUB_NON_LANGUAGES and record.language not in self.last_unmapped:
                    self.last_unmapped.append(record.language)
                continue
            commit_sha = str(record.metadata.get("commit_sha", ""))
            source_document_id = f"innovationgraph@{commit_sha[:12]}"
            observations.append(
                build_observation(
                    record=record,
                    language_id=language_id,
                    parser_version=parser_version,
                    retrieved_at=retrieved_at,
                    is_derived=True,
                    derivation_method=IG_SUM_METHOD,
                    source_document_id=source_document_id,
                    source_published_at=None,
                    population=IG_POPULATION,
                )
            )
            denominator = denominators.get(record.period_start, 0.0)
            if denominator > 0:
                share_value = round(100.0 * (record.value or 0.0) / denominator, 4)
                share_record = replace(
                    record,
                    metric_id=METRIC_IG_SHARE,
                    value=share_value,
                    unit="percent",
                    metadata={**record.metadata, "denominator_count": denominator},
                )
                observations.append(
                    build_observation(
                        record=share_record,
                        language_id=language_id,
                        parser_version=parser_version,
                        retrieved_at=retrieved_at,
                        is_derived=True,
                        derivation_method=IG_SHARE_METHOD,
                        source_document_id=source_document_id,
                        source_published_at=None,
                        population=IG_POPULATION,
                    )
                )
                shares.append((language_id, share_record))
        observations.extend(_derive_ig_rank(shares, parser_version=parser_version, retrieved_at=retrieved_at))
        return observations

    def _normalize_octoverse(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize Octoverse rank records into raw, non-derived annual observations.

        Each published rank is emitted verbatim (``is_derived=False``,
        ``derivation_method=None``): Octoverse prints these ranks, so nothing is
        summed, inferred or interpolated. The printed language name is resolved to a
        canonical language via the ``github``-scoped alias map; an unmapped name is
        skipped and recorded in :attr:`last_unmapped` (never guessed), except the
        documented :data:`GITHUB_NON_LANGUAGES` markup / config / data formats, which
        are skipped silently. ``source_published_at`` is taken from the edition's
        ``published_at`` and the per-edition ``source_url`` doubles as
        ``source_document_id`` so every rank stays traceable to its report. Pure over
        its inputs: no network, no database.

        :param records: Octoverse ``github-octoverse-rank`` source records.
        :returns: One raw rank observation per mapped record; empty when none map.
        """
        parser_version = self.metadata().parser_version
        self.last_unmapped = []
        observations: list[Observation] = []
        for record in records:
            language_id = self._normalizer.try_resolve(record.language, rating_id=self.provider_id)
            if language_id is None:
                if record.language not in GITHUB_NON_LANGUAGES and record.language not in self.last_unmapped:
                    self.last_unmapped.append(record.language)
                continue
            published_raw = record.metadata.get("published_at")
            source_published_at = (
                datetime.combine(date.fromisoformat(str(published_raw)), datetime.min.time(), UTC)
                if published_raw
                else None
            )
            observations.append(
                build_observation(
                    record=record,
                    language_id=language_id,
                    parser_version=parser_version,
                    retrieved_at=self._retrieved_at,
                    is_derived=False,
                    derivation_method=None,
                    source_document_id=record.source_url,
                    source_published_at=source_published_at,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named, variant-specific codes.

        Covers both variants and never mutates or drops an observation. A report
        that carries only WARNINGs stays ``ok`` and its observations persist; any
        ERROR blocks the upsert in
        :class:`~langrank.services.fetch.FetchService`. Every message names the
        variant, language and period label so an operator can locate the row.

        Codes:

        - ``rank_positive`` (ERROR): any observation whose ``rank`` is at or below
          zero (Octoverse or derived Innovation Graph rank).
        - ``count_non_negative`` (ERROR): a ``github-innovation-graph-pushers``
          value below zero.
        - ``share_range`` (ERROR): a ``github-innovation-graph-share`` value
          outside 0..100.
        - ``duplicate_language_period`` (ERROR): a repeated
          ``(language_id, period_start, metric_id)`` triple.
        - ``aggregate_not_derived`` (ERROR): an Innovation Graph observation whose
          ``is_derived`` flag is not set (every global aggregate is derived).
        - ``mixed_variant`` (ERROR): a batch carrying both ``github-octoverse-*``
          and ``github-innovation-graph-*`` metrics; the two variants are never
          conflated.
        - ``octoverse_rank_gap`` (WARNING): the Octoverse ranks within one edition
          are not the contiguous run ``1..n``.
        - ``unmapped_language`` (WARNING): one per source language the last
          :meth:`normalize` call could not resolve.

        :param observations: Observations to validate.
        :returns: A validation report; WARNING-only reports remain ``ok``.
        """
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        variants: set[str] = set()
        octoverse_ranks: dict[str, list[int]] = {}
        for item in observations:
            variant = _variant_of(item.metric_id) or self.provider_id
            variants.add(variant)
            label = f"{variant} {item.language_id} at {item.period_label}"
            if item.rank is not None and item.rank <= 0:
                report.add(Severity.ERROR, "rank_positive", f"{label}: rank {item.rank} must be positive")
            if item.metric_id == METRIC_IG_PUSHERS and item.value is not None and item.value < 0:
                report.add(
                    Severity.ERROR, "count_non_negative", f"{label}: pusher count {item.value} must be non-negative"
                )
            if item.metric_id == METRIC_IG_SHARE and item.value is not None and not 0 <= item.value <= 100:
                report.add(Severity.ERROR, "share_range", f"{label}: share {item.value} is outside 0..100")
            if item.metric_id in _IG_METRIC_IDS and not item.is_derived:
                report.add(
                    Severity.ERROR,
                    "aggregate_not_derived",
                    f"{label}: innovation-graph aggregate must set is_derived",
                )
            key = (item.language_id, item.period_start, item.metric_id)
            if key in seen:
                report.add(Severity.ERROR, "duplicate_language_period", f"duplicate {label} ({item.metric_id})")
            seen.add(key)
            if item.metric_id == METRIC_OCTOVERSE_RANK and item.rank is not None:
                octoverse_ranks.setdefault(item.period_label, []).append(item.rank)
        if {GitHubSource.OCTOVERSE.value, GitHubSource.INNOVATION_GRAPH.value} <= variants:
            report.add(
                Severity.ERROR,
                "mixed_variant",
                "batch mixes octoverse and innovation-graph metrics; the two variants are never conflated",
            )
        for edition, ranks in sorted(octoverse_ranks.items()):
            ordered = sorted(ranks)
            if ordered != list(range(1, len(ordered) + 1)):
                report.add(
                    Severity.WARNING,
                    "octoverse_rank_gap",
                    f"octoverse edition {edition} ranks {ordered} are not the contiguous run 1..{len(ordered)}",
                )
        for name in self.last_unmapped:
            report.add(
                Severity.WARNING, "unmapped_language", f"github language {name!r} did not map to a canonical language"
            )
        return report


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


def _parse_octoverse(content: bytes) -> list[SourceRecord]:
    """Parse the curated Octoverse rankings CSV into one record per published rank.

    Untrusted-input hardening mirrors the Innovation Graph path (GH-SEC-8 reusing
    GH-SEC-5): the stdlib ``csv`` module is used (never ``eval``); a missing required
    column raises a :class:`ParseError` naming it; ``rank`` must be a positive integer
    and ``year`` a plausible integer; ``ranking_basis`` must be a known
    :class:`OctoverseBasis`; and any per-row ``ValueError`` / ``KeyError`` is wrapped
    in a :class:`ParseError`. Each record is annual (:attr:`Granularity.YEAR`),
    carries ``metric_id=METRIC_OCTOVERSE_RANK`` and a raw published ``rank`` /
    ``value`` (``is_derived`` is decided in normalization), and preserves the printed
    language string and the edition's ``source_url``.

    :param content: The raw curated CSV bytes.
    :returns: One :class:`SourceRecord` per rank row, in file order.
    :raises ParseError: On a decoding error, a missing required column, or a
        malformed / out-of-range cell.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("github octoverse CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(text.splitlines())
    fieldnames = reader.fieldnames or []
    for column in _OCTOVERSE_REQUIRED_COLUMNS:
        if column not in fieldnames:
            raise ParseError(f"github octoverse CSV is missing required column {column!r}.")
    return [_octoverse_record_from_row(row) for row in reader]


def _octoverse_record_from_row(row: dict[str, Any]) -> SourceRecord:
    """Build one annual :class:`SourceRecord` from a validated Octoverse CSV row.

    :param row: A CSV row keyed by column name.
    :returns: A ``github-octoverse-rank`` source record for one published rank.
    :raises ParseError: If a numeric cell is malformed, the rank is not positive, the
        year is implausible, or the ranking basis is unknown.
    """
    try:
        year = int(row["year"])
        rank = int(row["rank"])
        language = row["language"]
        basis = OctoverseBasis(row["ranking_basis"])
        source_url = row["source_url"]
        published_at = row["published_at"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"github octoverse row is malformed: {row!r}") from exc
    if rank <= 0:
        raise ParseError(f"github octoverse rank must be positive: {row!r}")
    if not 2000 <= year <= 2100:
        raise ParseError(f"github octoverse year is implausible: {row!r}")
    return SourceRecord(
        rating_id=_RATING_ID,
        metric_id=METRIC_OCTOVERSE_RANK,
        language=language,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=rank,
        value=float(rank),
        unit="rank",
        source_url=source_url,
        metadata={
            "ranking_basis": basis.value,
            "provenance": "manual_curation",
            "published_at": published_at,
            "variant": GitHubSource.OCTOVERSE.value,
        },
    )


def _aggregate_global(records: Sequence[SourceRecord]) -> list[SourceRecord]:
    """Sum per-economy pusher records into one global record per (quarter, language).

    Every ``num_pushers`` cell is summed within its ``(period_start, Linguist
    language)`` group; the group's economy count is stored as ``economies_count``
    so the aggregate's ``raw_record_hash`` (a hash of the whole record) changes
    whenever the contributing economies change - not only when the total does. The
    per-economy ``iso2_code`` is dropped because the result is global; the pinned
    ``commit_sha`` and the :data:`IG_SUPPRESSION_THRESHOLD` are kept so the
    documented >=100-developer undercount stays traceable. The suppression means
    the sum is a floor, never a corrected or interpolated figure.

    :param records: Per-economy Innovation Graph source records (one economy per
        ``(quarter, language)``).
    :returns: One aggregate ``github-innovation-graph-pushers`` record per
        ``(quarter, language)``, ordered by quarter then Linguist name.
    """
    grouped: dict[tuple[date, str], list[SourceRecord]] = {}
    for record in records:
        grouped.setdefault((record.period_start, record.language), []).append(record)
    aggregated: list[SourceRecord] = []
    for (_period_start, _language), group in sorted(grouped.items(), key=lambda item: item[0]):
        first = group[0]
        total = sum(record.value or 0.0 for record in group)
        commit_sha = str(first.metadata.get("commit_sha", ""))
        aggregated.append(
            replace(
                first,
                rank=None,
                value=total,
                metadata={
                    "commit_sha": commit_sha,
                    "economies_count": len(group),
                    "suppression_threshold": IG_SUPPRESSION_THRESHOLD,
                    "variant": GitHubSource.INNOVATION_GRAPH.value,
                },
            )
        )
    return aggregated


def _derive_ig_rank(
    shares: Sequence[tuple[str, SourceRecord]],
    *,
    parser_version: str,
    retrieved_at: datetime,
) -> list[Observation]:
    """Derive a global ``rank`` observation from each global ``share`` record.

    Ranking is standard competition ranking on the share within one quarter
    (highest share is rank 1): equal shares share a rank and the next distinct
    share skips the tied positions (e.g. ``1, 1, 3``). Rank is computed over mapped
    languages only. Each rank is built from a synthetic ``rank`` source record whose
    ``value`` is the rank itself, so its ``raw_record_hash`` reflects the rank and a
    rank-only change is not masked by the share's hash (the Task 01.0 caveat).

    :param shares: ``(language_id, share_record)`` pairs across any number of
        quarters.
    :param parser_version: Parser version stamped onto each observation.
    :param retrieved_at: Acquisition timestamp stamped onto each observation.
    :returns: One rank observation per input share.
    """
    by_quarter: dict[date, list[tuple[str, SourceRecord]]] = {}
    for language_id, record in shares:
        by_quarter.setdefault(record.period_start, []).append((language_id, record))
    ranked: list[Observation] = []
    for quarter in sorted(by_quarter):
        ordered = sorted(by_quarter[quarter], key=lambda item: (-(item[1].value or 0.0), item[0]))
        current_rank = 0
        previous_value: Optional[float] = None
        for index, (language_id, record) in enumerate(ordered, start=1):
            if previous_value is None or record.value != previous_value:
                current_rank = index
                previous_value = record.value
            commit_sha = str(record.metadata.get("commit_sha", ""))
            rank_record = replace(
                record,
                metric_id=METRIC_IG_RANK,
                unit="rank",
                rank=current_rank,
                value=float(current_rank),
            )
            ranked.append(
                build_observation(
                    record=rank_record,
                    language_id=language_id,
                    parser_version=parser_version,
                    retrieved_at=retrieved_at,
                    is_derived=True,
                    derivation_method=IG_RANK_METHOD,
                    source_document_id=f"innovationgraph@{commit_sha[:12]}",
                    source_published_at=None,
                    population=IG_POPULATION,
                )
            )
    return ranked
