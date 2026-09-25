from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

from langrank.errors import ParseError, ProviderError
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
from langrank.normalization import IEEE_UNTRACKED_LABELS, LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import build_observation, payload_from_content

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "ieee-spectrum"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "ieee-spectrum-v1"

#: Landing page for the latest verified IEEE Spectrum edition; each curated CSV
#: row carries its own per-edition ``source_url`` (subtask 04), so this is only
#: the artifact-level provenance URL.
HOMEPAGE = "https://spectrum.ieee.org/top-programming-languages-2025"

#: Curated, repo-committed edition dataset read at :meth:`IeeeSpectrumProvider.fetch`
#: time (manual transcription only, 0 network requests). Columns:
#: ``year,profile,rank,language,score,source_url,published_at,methodology_version``.
DATA_PATH = Path(__file__).parent / "data" / "ieee_spectrum.csv"

#: ``--source`` values that select the only supported acquisition mode (the bundled,
#: manually transcribed CSV). ``None`` and ``"auto"`` fall through to it because
#: there is no network source; any other value is rejected with a
#: :class:`~langrank.errors.ProviderError`.
_BUNDLED_SOURCES: frozenset[Optional[str]] = frozenset({None, "auto", "bundled"})

#: ``derivation_method`` stamped on every **rank** observation in subtask 05. IEEE's
#: Flourish data file publishes only per-language scores, never a rank column, so we
#: compute the rank ourselves with standard competition ranking (ties share a rank,
#: the next distinct score skips the tied positions). Rank observations are therefore
#: ``is_derived=True``; score observations are ``is_derived=False`` (published raw).
RANK_DERIVATION_METHOD = "rank_by_published_score"

#: Published-score scale per edition, kept so subtask 05 never rescales a score. The
#: ``score`` column is IEEE's own figure from that edition's Flourish published data
#: file, stored exactly as published: 2022 is on a 0-100 scale, 2023-2025 on a 0-1
#: scale. The scale is edition-specific and scores are never comparable across
#: editions, so no normalization or rescaling is applied - the raw value is stored.
#: Adding an edition means updating this map, :data:`IEEE_EDITIONS` and the bundled
#: CSV together; a scored row for a year missing here raises ``ParseError``.
SCORE_SCALE_BY_YEAR: dict[int, str] = {
    2022: "0-100",
    2023: "0-1",
    2024: "0-1",
    2025: "0-1",
}

#: Exact curated-CSV header the parser requires; a missing column raises a
#: :class:`~langrank.errors.ParseError` so a malformed ``langrank import`` file
#: never lands silently miscolumned.
_REQUIRED_COLUMNS: tuple[str, ...] = (
    "year",
    "profile",
    "rank",
    "language",
    "score",
    "source_url",
    "published_at",
    "methodology_version",
)

#: ``metadata["provenance"]`` stamped on every record: IEEE ships no machine-readable
#: dataset, so ranks and scores are manually transcribed from the published edition.
_PROVENANCE = "manual_transcription"

#: Default look-back (years) applied to parsed editions when the request sets no
#: ``--since`` / ``--until`` / ``--years`` window (e.g. the ``langrank import`` path).
#: All curated editions fall inside a decade of the latest, so nothing is dropped.
_DEFAULT_YEARS = 10


class IeeeProfile(StrEnum):
    """The IEEE Spectrum ranking profiles imported as distinct metric pairs.

    Each edition re-weights one metric set into several *profiles*; a language's
    rank and score are only meaningful **within one profile of one edition**. The
    three names below are verified for the 2022-2025 editions and map 1:1 onto the
    pre-2022 interactive presets of the same name. The pre-2022 ``Open`` and
    ``Custom`` presets have no stable cross-edition definition and are deliberately
    **not** imported, so they are not members here (source-note decision, subtask
    01). Every profile is its own metric pair and profiles are never merged into a
    single comparable series.

    :cvar SPECTRUM: IEEE's default profile (typical IEEE-member / working-engineer
        weighting); plan.md's ``default`` maps to this name.
    :cvar JOBS: Employer-demand weighting.
    :cvar TRENDING: Zeitgeist weighting.
    """

    SPECTRUM = "spectrum"
    JOBS = "jobs"
    TRENDING = "trending"


#: Human-readable weighting summary per profile, reused in metric descriptions so
#: each profile's meaning stays attached to its metric pair.
_PROFILE_LABELS: dict[IeeeProfile, str] = {
    IeeeProfile.SPECTRUM: "Spectrum (default; typical IEEE-member / working-engineer weighting)",
    IeeeProfile.JOBS: "Jobs (employer demand)",
    IeeeProfile.TRENDING: "Trending (zeitgeist)",
}


def rank_metric_id(profile: IeeeProfile) -> str:
    """Return the rank metric ID for one profile.

    :param profile: The ranking profile.
    :returns: ``ieee-spectrum-{profile}-rank`` (e.g. ``ieee-spectrum-jobs-rank``).
    """
    return f"ieee-spectrum-{profile}-rank"


def score_metric_id(profile: IeeeProfile) -> str:
    """Return the score metric ID for one profile.

    :param profile: The ranking profile.
    :returns: ``ieee-spectrum-{profile}-score`` (e.g. ``ieee-spectrum-jobs-score``).
    """
    return f"ieee-spectrum-{profile}-score"


@dataclass(frozen=True)
class _Edition:
    """One IEEE Spectrum edition's methodology break, mirroring the source-note table.

    :ivar year: The edition's calendar year (one edition per year).
    :ivar methodology_version: Stable per-edition methodology identifier.
    :ivar source_url: The edition's article/app URL.
    :ivar description: Human-readable summary of that edition's metric set and why
        its scores are not comparable with other editions.
    """

    year: int
    methodology_version: str
    source_url: str
    description: str


#: One entry per edition row of ``docs/source-notes/ieee-spectrum.md``. The metric
#: set and weights change between editions and the score is renormalized per edition
#: (top = 100), so scores/ranks are never comparable across editions - each edition
#: is recorded as its own :class:`~langrank.models.MethodologyNote`.
IEEE_EDITIONS: tuple[_Edition, ...] = (
    _Edition(
        year=2025,
        methodology_version="ieee-2025-manual-7metrics",
        source_url="https://spectrum.ieee.org/top-programming-languages-2025",
        description=(
            "2025 edition: 7 metrics from 8 sources over 64 languages, gathered manually after API "
            "terminations; Stack Exchange question volume was ~22% of 2024's. The score is renormalized "
            "per edition (top language = 100), so ranks and scores are not comparable with other editions."
        ),
    ),
    _Edition(
        year=2024,
        methodology_version="ieee-2024-manual-8metrics",
        source_url="https://spectrum.ieee.org/top-programming-languages-2024",
        description=(
            "2024 edition: 8 metrics from 8 sources, gathered manually to avoid API bias and language-name "
            "collisions. Per-edition renormalization (top = 100); not comparable across editions."
        ),
    ),
    _Edition(
        year=2023,
        methodology_version="ieee-2023-8metrics",
        source_url="https://spectrum.ieee.org/the-top-programming-languages-2023",
        description=(
            "2023 edition (10th annual): 8-metric family; Spectrum #1 Python, Jobs #1 SQL. Per-edition "
            "renormalization (top = 100); not comparable across editions."
        ),
    ),
    _Edition(
        year=2022,
        methodology_version="ieee-2022-profile-redesign",
        source_url="https://spectrum.ieee.org/top-programming-languages-2022",
        description=(
            "2022 edition: profile presentation redesigned to the three named profiles (spectrum, jobs, "
            "trending). Per-edition renormalization (top = 100); not comparable across editions."
        ),
    ),
    _Edition(
        year=2021,
        methodology_version="ieee-2019-11metrics-8sources",
        source_url="https://spectrum.ieee.org/top-programming-languages-interactive-2021/",
        description=(
            "2021 interactive edition: 11 metrics from 8 sources; only the spectrum/jobs/trending presets "
            "are imported (Open/Custom are not). Per-edition renormalization (top = 100); not comparable "
            "across editions."
        ),
    ),
)


#: Profiles present in each edition's source-note table. IEEE presents the same three
#: named profiles (:class:`IeeeProfile`) in every imported edition (2022-2025, plus the
#: 2021 interactive presets mapped 1:1 in subtask 01), so each year maps to the full
#: profile set. :meth:`IeeeSpectrumProvider.validate` reads this to flag an observation
#: whose ``(year, profile)`` pair is absent from the source note (``profile_not_in_edition``).
EDITION_PROFILES: dict[int, frozenset[IeeeProfile]] = {
    edition.year: frozenset(IeeeProfile) for edition in IEEE_EDITIONS
}

#: Upper bound of each edition's published-score scale (:data:`SCORE_SCALE_BY_YEAR`).
#: A ``0-100`` edition tops out at 100, a ``0-1`` edition at 1; :meth:`validate`
#: range-checks each score against the bound named in its ``metadata_json['score_scale']``
#: rather than a fixed 100, because the scale is edition-specific and never rescaled.
_SCORE_SCALE_MAX: dict[str, float] = {"0-100": 100.0, "0-1": 1.0}


def _score_scale_max(scale: str) -> float:
    """Return the maximum published score for an edition's scale.

    :param scale: The ``metadata_json['score_scale']`` label (``"0-100"`` / ``"0-1"``).
    :returns: The scale's upper bound; ``100.0`` for any unrecognised label, matching
        IEEE's historical default so an unlabelled score is never silently accepted
        beyond a plausible bound.
    """
    return _SCORE_SCALE_MAX.get(scale, 100.0)


class IeeeSpectrumProvider:
    """Records IEEE Spectrum *Top Programming Languages* rank and score per profile.

    Each edition re-weights one metric set into several ranking *profiles*
    (:class:`IeeeProfile`); every profile is stored as its **own** metric pair
    (``ieee-spectrum-{profile}-rank`` / ``ieee-spectrum-{profile}-score``), so a
    query never mixes profiles into one series. The published ``score`` is IEEE's own
    figure from the edition's Flourish published data file, stored exactly as
    published (``is_derived=False``, landed in subtask 05); its scale is
    edition-specific (:data:`SCORE_SCALE_BY_YEAR` - 2022 on 0-100, 2023-2025 on 0-1)
    and is never rescaled. IEEE's data file has no rank column, so **rank** is
    computed by this project from the published scores (competition ranking, ties
    share a rank) and is therefore ``is_derived=True`` with
    ``derivation_method=`` :data:`RANK_DERIVATION_METHOD` (subtask 05). The score is
    renormalized per edition and the metric set changes between editions, so ranks
    and scores are **not comparable across editions** and only comparable within one
    edition's one profile.

    Acquisition is manual transcription only: there is no downloadable dataset and
    no network fetch (0 requests). :meth:`fetch` reads the curated bundled CSV
    (:data:`DATA_PATH`), :meth:`parse` and :meth:`normalize` turn it into per-profile
    rank/score observations, and :meth:`validate` checks them against named codes
    (subtask 06). One data-integrity note: the 2025 ``trending`` edition's data file listed ABAP
    twice with different scores, so both ambiguous rows were dropped from the curated
    CSV (other ranks unchanged).

    :ivar provider_id: Stable rating ID used across the pipeline.
    :ivar last_unmapped: IEEE labels the last :meth:`normalize` call could not resolve
        to a canonical language; skipped rather than guessed (documented
        :data:`~langrank.normalization.IEEE_UNTRACKED_LABELS` are excluded).
    """

    provider_id = _RATING_ID

    def __init__(self, cache_dir: Path) -> None:
        """Wire the provider's cache directory and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the
            ``ieee-spectrum`` subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        #: Request window stashed by :meth:`fetch` and applied in :meth:`parse`; all
        #: default to ``None`` so the ``langrank import`` path (which never calls
        #: :meth:`fetch`) imports every edition in the supplied CSV.
        self._request_since: Optional[date] = None
        self._request_until: Optional[date] = None
        self._request_years: Optional[int] = None
        #: IEEE labels the last :meth:`normalize` call could not resolve to a canonical
        #: language (documented :data:`IEEE_UNTRACKED_LABELS` are excluded); skipped
        #: rather than guessed and surfaced to validation (subtask 06).
        self.last_unmapped: list[str] = []

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: one metric pair per profile.

        Performs no network or database access.

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        metrics: list[MetricDefinition] = []
        for profile in IeeeProfile:
            weighting = _PROFILE_LABELS[profile]
            metrics.append(
                MetricDefinition(
                    id=rank_metric_id(profile),
                    rating_id=self.provider_id,
                    display_name=f"{profile.value.title()} rank",
                    unit="rank",
                    higher_is_better=False,
                    description=(
                        f"IEEE Spectrum {weighting} profile rank (1 is best) for the edition. Profiles are "
                        "different rankings and are never merged into one series; ranks are not comparable "
                        "across editions or profiles."
                    ),
                )
            )
            metrics.append(
                MetricDefinition(
                    id=score_metric_id(profile),
                    rating_id=self.provider_id,
                    display_name=f"{profile.value.title()} score",
                    unit="score",
                    higher_is_better=True,
                    description=(
                        f"IEEE Spectrum {weighting} profile relative score (top language = 100), as published "
                        "(raw, not derived). The score is renormalized per edition, so scores are not "
                        "comparable across editions or profiles."
                    ),
                )
            )
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="IEEE Spectrum",
            description=(
                "IEEE Spectrum Top Programming Languages: a composite weighted popularity index published "
                "annually as several ranking profiles (spectrum, jobs, trending). Each profile is a distinct "
                "metric pair and profiles are never merged; manual transcription only (no network fetch)."
            ),
            homepage=HOMEPAGE,
            default_metric=rank_metric_id(IeeeProfile.SPECTRUM),
            native_granularity=Granularity.YEAR,
            caveats=[
                "Composite weighted index - weights differ per profile and per edition.",
                "Profiles are different rankings, never one series.",
                "Scores are not comparable across editions (per-edition renormalization / methodology changes).",
                "Manual transcription - ranks and scores are transcribed from published text/tables, no chart "
                "extraction and no network fetch.",
            ],
            parser_version=PARSER_VERSION,
            metrics=metrics,
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version=edition.methodology_version,
                    valid_from=date(edition.year, 1, 1),
                    valid_to=date(edition.year, 12, 31),
                    description=edition.description,
                    source_url=edition.source_url,
                )
                for edition in IEEE_EDITIONS
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Read the curated IEEE Spectrum edition dataset from the bundled CSV.

        Acquisition is manual transcription only: no network request is ever issued
        (request budget 0). The bytes come from the repo-committed
        :data:`DATA_PATH`, whose integrity is assured by code review. ``--source``
        must be unset, ``auto`` or ``bundled`` - there is no network source, so any
        other value is rejected rather than guessed. The artifact ``url`` is the
        provider homepage; each row carries its own per-edition ``source_url`` for
        the parser. The ``since`` / ``until`` / ``years`` window is stashed here and
        applied to the parsed editions in :meth:`parse`, not to the raw bytes.

        :param request: Fetch parameters; only ``source`` (validated here) and
            ``no_cache`` are honoured at this stage.
        :returns: The raw curated-CSV fetch payload for the bundled edition dataset.
        :raises ProviderError: If ``--source`` is neither unset/``auto`` nor
            ``bundled`` (the only supported acquisition mode).
        """
        if request.source not in _BUNDLED_SOURCES:
            valid = ", ".join(["auto", "bundled"])
            raise ProviderError(
                f"unknown --source {request.source!r} for ieee-spectrum; the only source is the bundled, "
                f"manually transcribed dataset (valid: {valid})."
            )
        self._request_since = request.since
        self._request_until = request.until
        self._request_years = request.years
        content = DATA_PATH.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=HOMEPAGE,
            content=content,
            mime_type="text/csv",
            metadata_json={
                "mode": "bundled",
                "provenance": "manual_transcription",
                "data_origin": "flourish_published_data",
                "source_document_id": _RATING_ID,
            },
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse the curated edition CSV into per-profile rank and score records.

        The same parser backs :meth:`fetch` and the ``langrank import`` path, so it
        hardens the untrusted CSV: the stdlib ``csv`` module is used (never ``eval``);
        non-UTF-8 bytes raise a :class:`~langrank.errors.ParseError` (a UTF-8 BOM is
        tolerated); a missing required column (:data:`_REQUIRED_COLUMNS`) raises a
        ``ParseError`` naming it; and an unknown ``profile``, a non-positive ``rank``,
        an implausible ``year`` or a malformed numeric cell each raise a ``ParseError``
        naming the offending row. Each mapped row yields a **rank** record and, when the
        ``score`` cell is non-empty, a **score** record for the same ``(year, profile,
        language)`` - an empty ``score`` never fabricates a score record (the rank is
        still stored). Records are annual (:attr:`Granularity.YEAR`) and preserve the
        printed language string, the per-edition ``source_url`` and ``published_at``,
        the ``methodology_version`` and the edition's :data:`SCORE_SCALE_BY_YEAR` scale;
        ``is_derived`` is decided in :meth:`normalize`. Parsed records are finally
        trimmed to the request window (:meth:`_filter_window`).

        :param raw: The raw curated-CSV fetch payload.
        :returns: One rank record per published rank and one score record per non-empty
            published score, within the request window.
        :raises ParseError: On a decoding error, a missing required column, an unknown
            profile, or a malformed / out-of-range cell.
        """
        try:
            text = raw.content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError("ieee-spectrum CSV must be UTF-8 encoded.") from exc
        reader = csv.DictReader(text.splitlines())
        fieldnames = reader.fieldnames or []
        for column in _REQUIRED_COLUMNS:
            if column not in fieldnames:
                raise ParseError(f"ieee-spectrum CSV is missing required column {column!r}.")
        records: list[SourceRecord] = []
        for row in reader:
            records.extend(_records_from_row(row))
        return self._filter_window(records)

    def _filter_window(self, records: list[SourceRecord]) -> list[SourceRecord]:
        """Trim parsed edition records to the request window by ``period_start``.

        With no explicit ``--until`` the window ends at the latest edition present;
        with no explicit ``--since`` it spans ``--years`` (default
        :data:`_DEFAULT_YEARS`) back from that end. The ``langrank import`` path leaves
        every stashed bound at ``None``, so a decade-wide default keeps every curated
        edition. Missing editions are never synthesised - only present rows are kept.

        :param records: Records built from the curated CSV.
        :returns: The subset whose ``period_start`` falls in ``[since, until]``.
        """
        if not records:
            return records
        until = self._request_until or max(record.period_start for record in records)
        if self._request_since is not None:
            since = self._request_since
        else:
            span = self._request_years or _DEFAULT_YEARS
            since = date(until.year - span, 1, 1)
        return [record for record in records if since <= record.period_start <= until]

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize per-profile records into observations with full provenance.

        :data:`~langrank.normalization.IEEE_UNTRACKED_LABELS` are consulted **before**
        resolution, so documented markup / hardware labels (and IEEE's classic-VB
        ``Visual Basic``) are skipped silently - no observation and no
        ``unmapped_language`` warning - and never fold into ``vb.net`` via the global
        alias. Any other label that resolves to no canonical language is skipped and
        recorded in :attr:`last_unmapped` (never guessed) for validation (subtask 06).

        The published ``score`` is IEEE's own figure, emitted verbatim
        (``is_derived=False``, ``derivation_method=None``) with its edition-specific
        :data:`SCORE_SCALE_BY_YEAR` scale carried in ``metadata_json['score_scale']``
        and never rescaled. IEEE's data file publishes no rank column, so every
        **rank** is computed by this project from the published scores and is therefore
        ``is_derived=True`` with ``derivation_method=`` :data:`RANK_DERIVATION_METHOD`.
        ``source_document_id`` identifies the edition **and** profile
        (``ieee-tpl-{year}-{profile}``) so a query never conflates profiles, and
        ``source_published_at`` comes from the row's ``published_at``. Pure over its
        inputs: no network, no database.

        :param records: Parsed per-profile rank and score source records.
        :returns: One observation per mapped record; empty when none map.
        """
        self.last_unmapped = []
        observations: list[Observation] = []
        for record in records:
            label = record.language
            if label in IEEE_UNTRACKED_LABELS:
                continue
            language_id = self._normalizer.try_resolve(label, rating_id=self.provider_id)
            if language_id is None:
                if label not in self.last_unmapped:
                    self.last_unmapped.append(label)
                continue
            is_rank = record.metric_id.endswith("-rank")
            profile = str(record.metadata.get("profile", ""))
            source_document_id = f"ieee-tpl-{record.period_start.year}-{profile}"
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
                    parser_version=PARSER_VERSION,
                    retrieved_at=self._retrieved_at,
                    is_derived=is_rank,
                    derivation_method=RANK_DERIVATION_METHOD if is_rank else None,
                    source_document_id=source_document_id,
                    source_published_at=source_published_at,
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named, profile-aware codes.

        Emits a :class:`~langrank.models.ValidationReport` without ever mutating or
        dropping an observation. A report carrying only WARNINGs stays ``ok`` and its
        observations persist; any ERROR blocks the upsert in
        :class:`~langrank.services.fetch.FetchService`. Every message names the
        profile, language and edition so an operator can locate the row.

        Codes:

        - ``rank_positive`` (ERROR): a rank observation whose ``rank`` is at or below
          zero.
        - ``score_range`` (ERROR): a score observation outside its edition's scale
          (``0..100`` or ``0..1`` per :data:`SCORE_SCALE_BY_YEAR`), read from the
          observation's ``metadata_json['score_scale']`` - never a fixed 0..100.
        - ``derivation_flag`` (ERROR): a rank observation not flagged ``is_derived``
          (ranks are computed by competition ranking) or a score observation flagged
          ``is_derived`` (published scores are raw). This mirrors the as-built pairing
          from subtask 05.
        - ``duplicate_language_period`` (ERROR): a repeated
          ``(language_id, period_start, metric_id)`` triple - the same language, year
          and metric twice.
        - ``duplicate_rank`` (ERROR): two languages sharing a rank within one
          ``(year, profile)`` whose scores differ. A legitimate competition-ranking
          tie shares a rank *and* an equal score, so only a score mismatch is flagged;
          rank gaps from ties are never flagged.
        - ``profile_not_in_edition`` (ERROR): an observation whose ``(year, profile)``
          is absent from :data:`EDITION_PROFILES` (the source-note edition table).
        - ``mixed_profile`` (ERROR): one metric id carrying more than one profile;
          profiles are never merged into a single series.
        - ``top_score_not_100`` (WARNING): the maximum score in a ``(year, profile)``
          does not reach the edition scale's top value (100 for a 0-100 edition, 1 for
          a 0-1 edition). WARNING-only, so it never blocks the upsert.
        - ``unmapped_language`` (WARNING): one per IEEE label the last
          :meth:`normalize` call could not resolve.

        :param observations: Observations to validate.
        :returns: A validation report; WARNING-only reports remain ``ok``.
        """
        report = ValidationReport()
        seen: set[tuple[str, date, str]] = set()
        profiles_by_metric: dict[str, set[str]] = {}
        rank_groups: dict[tuple[int, str, int], set[str]] = {}
        score_by_key: dict[tuple[int, str, str], float] = {}
        score_groups: dict[tuple[int, str], list[float]] = {}
        score_scale_of: dict[tuple[int, str], str] = {}
        for item in observations:
            year = item.period_start.year
            profile = str(item.metadata_json.get("profile", ""))
            is_rank = item.metric_id.endswith("-rank")
            is_score = item.metric_id.endswith("-score")
            label = f"{profile} {item.language_id} at {item.period_label}"
            profiles_by_metric.setdefault(item.metric_id, set()).add(profile)
            key = (item.language_id, item.period_start, item.metric_id)
            if key in seen:
                report.add(Severity.ERROR, "duplicate_language_period", f"duplicate {label} ({item.metric_id})")
            seen.add(key)
            allowed = EDITION_PROFILES.get(year)
            if allowed is None or profile not in {member.value for member in allowed}:
                report.add(
                    Severity.ERROR,
                    "profile_not_in_edition",
                    f"{label}: profile {profile!r} is not in the {year} edition",
                )
            if is_rank:
                if item.rank is not None and item.rank <= 0:
                    report.add(Severity.ERROR, "rank_positive", f"{label}: rank {item.rank} must be positive")
                if not item.is_derived:
                    report.add(
                        Severity.ERROR,
                        "derivation_flag",
                        f"{label}: rank is derived (competition ranking) and must set is_derived",
                    )
                if item.rank is not None:
                    rank_groups.setdefault((year, profile, item.rank), set()).add(item.language_id)
            if is_score:
                if item.is_derived:
                    report.add(
                        Severity.ERROR,
                        "derivation_flag",
                        f"{label}: score is published raw and must not set is_derived",
                    )
                scale = str(item.metadata_json.get("score_scale", ""))
                top = _score_scale_max(scale)
                if item.value is not None and not 0 <= item.value <= top:
                    report.add(
                        Severity.ERROR,
                        "score_range",
                        f"{label}: score {item.value} is outside 0..{top} (scale {scale!r})",
                    )
                if item.value is not None:
                    score_by_key[(year, profile, item.language_id)] = item.value
                    score_groups.setdefault((year, profile), []).append(item.value)
                    score_scale_of[(year, profile)] = scale
        for metric_id, profiles in sorted(profiles_by_metric.items()):
            if len(profiles) > 1:
                report.add(
                    Severity.ERROR,
                    "mixed_profile",
                    f"metric {metric_id} mixes profiles {sorted(profiles)}; profiles are never merged",
                )
        for (year, profile, rank), languages in sorted(rank_groups.items()):
            if len(languages) < 2:
                continue
            scores = {
                score_by_key[(year, profile, lang)] for lang in languages if (year, profile, lang) in score_by_key
            }
            if len(scores) > 1:
                report.add(
                    Severity.ERROR,
                    "duplicate_rank",
                    f"{profile} {year}: languages {sorted(languages)} share rank {rank} with differing scores",
                )
        for (year, profile), values in sorted(score_groups.items()):
            top = _score_scale_max(score_scale_of[(year, profile)])
            if max(values) != top:
                report.add(
                    Severity.WARNING,
                    "top_score_not_100",
                    f"{profile} {year}: top score {max(values)} does not reach the edition scale top {top}",
                )
        for name in self.last_unmapped:
            report.add(
                Severity.WARNING,
                "unmapped_language",
                f"ieee-spectrum label {name!r} did not map to a canonical language",
            )
        return report


def _records_from_row(row: dict[str, Any]) -> list[SourceRecord]:
    """Build the rank record and optional score record for one curated CSV row.

    One row is one ``(year, profile, language)`` cell. It always yields a **rank**
    record (metric ``ieee-spectrum-{profile}-rank``); it additionally yields a
    **score** record (metric ``ieee-spectrum-{profile}-score``) only when the ``score``
    cell is non-empty - an empty score is left missing, never fabricated. The score
    record carries no ``rank`` (the two metrics stay independent) and both records
    carry the edition's provenance so ``is_derived`` can be decided in
    :meth:`IeeeSpectrumProvider.normalize`.

    :param row: A curated CSV row keyed by column name.
    :returns: ``[rank_record]`` or ``[rank_record, score_record]``.
    :raises ParseError: If the profile is unknown, the rank is not a positive integer,
        the year is implausible, or a numeric cell is malformed.
    """
    try:
        year = int(row["year"])
        profile = IeeeProfile(row["profile"])
        rank = int(row["rank"])
        language = row["language"]
        score_raw = (row["score"] or "").strip()
        source_url = row["source_url"]
        published_at = row["published_at"]
        methodology_version = row["methodology_version"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"ieee-spectrum row is malformed: {row!r}") from exc
    if rank <= 0:
        raise ParseError(f"ieee-spectrum rank must be positive: {row!r}")
    if not 2000 <= year <= 2100:
        raise ParseError(f"ieee-spectrum year is implausible: {row!r}")
    period_start = date(year, 1, 1)
    period_end = date(year, 12, 31)
    period_label = str(year)
    base_metadata: dict[str, Any] = {
        "profile": profile.value,
        "methodology_version": methodology_version,
        "provenance": _PROVENANCE,
        "published_at": published_at,
    }
    records = [
        SourceRecord(
            rating_id=_RATING_ID,
            metric_id=rank_metric_id(profile),
            language=language,
            period_start=period_start,
            period_end=period_end,
            period_label=period_label,
            granularity=Granularity.YEAR,
            rank=rank,
            value=float(rank),
            unit="rank",
            source_url=source_url,
            metadata=dict(base_metadata),
        )
    ]
    if score_raw:
        try:
            score = float(score_raw)
        except ValueError as exc:
            raise ParseError(f"ieee-spectrum score is malformed: {row!r}") from exc
        scale = SCORE_SCALE_BY_YEAR.get(year)
        if scale is None:
            raise ParseError(
                f"ieee-spectrum edition {year} has no recorded score scale; add it to SCORE_SCALE_BY_YEAR "
                "(and IEEE_EDITIONS / the source note) before importing its scores."
            )
        records.append(
            SourceRecord(
                rating_id=_RATING_ID,
                metric_id=score_metric_id(profile),
                language=language,
                period_start=period_start,
                period_end=period_end,
                period_label=period_label,
                granularity=Granularity.YEAR,
                rank=None,
                value=score,
                unit="score",
                source_url=source_url,
                metadata={**base_metadata, "score_scale": scale},
            )
        )
    return records
