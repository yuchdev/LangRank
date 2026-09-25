from __future__ import annotations

import csv
from collections.abc import Sequence
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
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import JETBRAINS_NON_LANGUAGE_ANSWERS, LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import build_observation, payload_from_content
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
    RAW_METRIC_SUFFIX,
    question_for,
    wording_changes,
)

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "jetbrains"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "jetbrains-v1"

#: Latest verified *State of Developer Ecosystem* report landing page; each
#: curated row carries its own per-edition ``source_url`` (subtask 05), so this is
#: only the artifact-level provenance URL for the provider's metadata.
HOMEPAGE = "https://devecosystem-2025.jetbrains.com/"

#: Curated, repo-committed published-percentages dataset read at
#: :meth:`JetBrainsProvider.fetch` time in the default ``published`` mode (0 network
#: requests). Every value is a figure JetBrains itself ships as chart data for its
#: edition pages; integrity is assured by code review. Columns:
#: ``year,metric,language,percent,sample_size,population,source_url,published_at``.
DATA_PATH = Path(__file__).parent / "data" / "jetbrains.csv"

#: Exact curated-CSV header the published parser requires; a missing column raises a
#: :class:`~langrank.errors.ParseError` so a malformed file never lands miscolumned.
_REQUIRED_COLUMNS: tuple[str, ...] = (
    "year",
    "metric",
    "language",
    "percent",
    "sample_size",
    "population",
    "source_url",
    "published_at",
)

#: ``metadata['provenance']`` stamped on every published record: the value is
#: JetBrains' own weighted percentage taken from the edition's shipped chart data.
_PUBLISHED_PROVENANCE = "published_chart_data"

#: Inclusive percent bounds. JetBrains ships whole-percent figures and prints ``0``
#: values (kept, never dropped); anything outside ``0..100`` is a malformed cell.
_PERCENT_MIN = 0.0
_PERCENT_MAX = 100.0

#: Unit shared by every JetBrains metric: a self-reported percentage. Published
#: percentages are JetBrains' own weighted figures; ``-raw`` percentages are
#: LangRank-derived unweighted respondent shares. The two are never comparable and
#: are kept on separate metric IDs so they never share a series.
_UNIT_PERCENT = "percent"

#: ``derivation_method`` stamped on every ``-raw`` observation (subtask 06). Raw-mode
#: percentages are unweighted per-language respondent shares computed by LangRank over
#: the anonymized response dump, distinct from JetBrains' published weighted figures.
RAW_DERIVATION_METHOD = "unweighted_respondent_share"

#: The three published, weighted metric IDs (``is_derived=False``). Ordered
#: ``used_last_12_months`` first so it can be the default metric. ``primary_language``
#: and ``used_last_12_months`` answer **different** survey questions and are never
#: merged into one series.
PUBLISHED_METRICS: tuple[str, ...] = (
    METRIC_USED_LAST_12_MONTHS,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_PLANNED_ADOPTION,
)

#: The three derived, unweighted metric IDs, each the matching published ID plus the
#: ``-raw`` suffix (``is_derived=True``, ``derivation_method=`` :data:`RAW_DERIVATION_METHOD`).
#: A ``-raw`` metric never shares a series with its published counterpart.
RAW_METRICS: tuple[str, ...] = tuple(metric_id + RAW_METRIC_SUFFIX for metric_id in PUBLISHED_METRICS)

#: Per published metric: display name and the human-readable question it answers.
#: Reused to build both the published and the ``-raw`` metric definition so the two
#: stay described identically apart from the weighting/derivation distinction.
_METRIC_LABELS: dict[str, tuple[str, str]] = {
    METRIC_USED_LAST_12_MONTHS: (
        "Used in last 12 months",
        "used the language in the last 12 months",
    ),
    METRIC_PRIMARY_LANGUAGE: (
        "Primary language",
        "named the language as their primary (main) language",
    ),
    METRIC_PLANNED_ADOPTION: (
        "Planning to adopt",
        "reported planning to adopt or migrate to the language",
    ),
}


def raw_metric_id(published_metric_id: str) -> str:
    """Return the ``-raw`` metric ID for a published metric ID.

    :param published_metric_id: One of :data:`PUBLISHED_METRICS`.
    :returns: The published ID with the :data:`~langrank.providers.jetbrains_questions.RAW_METRIC_SUFFIX`
        appended (e.g. ``jetbrains-used-last-12-months-raw``).
    """
    return published_metric_id + RAW_METRIC_SUFFIX


class JetBrainsSource(StrEnum):
    """The two independently selectable JetBrains acquisition modes.

    The modes measure the same survey questions but differ in weighting and
    provenance and are **never merged**: ``published`` reads JetBrains' own
    **weighted** percentages (bundled curated CSV, ``is_derived=False``);
    ``raw-data`` imports the anonymized response dump and computes **unweighted**
    respondent shares (``is_derived=True``, ``-raw`` metric IDs). Each mode owns its
    own metric IDs, so a query never mixes weighted and unweighted values.

    :cvar PUBLISHED: JetBrains' published, weighted percentages (default; ``auto``).
    :cvar RAW_DATA: LangRank-derived unweighted shares from the imported raw dump.
    """

    PUBLISHED = "published"
    RAW_DATA = "raw-data"


#: ``--source`` values that select the default (published, weighted) mode.
_AUTO_SOURCES: frozenset[Optional[str]] = frozenset({None, "auto"})


def _resolve_source(value: Optional[str]) -> JetBrainsSource:
    """Resolve a ``--source`` value to a :class:`JetBrainsSource` mode.

    ``None`` and ``"auto"`` select :attr:`JetBrainsSource.PUBLISHED` (the bundled,
    weighted percentages preferred by ``fetch all``); ``"raw-data"`` selects the
    import mode. The modes are never merged, so an unknown value is rejected rather
    than guessed.

    :param value: The raw ``--source`` flag, or ``None`` when unset.
    :returns: The selected :class:`JetBrainsSource`.
    :raises ProviderError: If ``value`` is neither ``auto`` nor a known mode.
    """
    if value in _AUTO_SOURCES:
        return JetBrainsSource.PUBLISHED
    try:
        return JetBrainsSource(value)
    except ValueError as exc:
        valid = ", ".join(["auto", *sorted(source.value for source in JetBrainsSource)])
        raise ProviderError(f"unknown --source {value!r} for jetbrains; valid sources: {valid}.") from exc


class JetBrainsProvider:
    """Records JetBrains *State of Developer Ecosystem* language-usage percentages.

    JetBrains runs an annual self-reported survey and publishes **weighted**
    language figures for three distinct questions - ``used_last_12_months``,
    ``primary_language`` and ``planned_adoption`` - that are **never merged** into
    one series (they answer different questions on different denominators). Each
    question is one metric (:data:`PUBLISHED_METRICS`); the same three questions,
    imported from the anonymized raw response dump and re-computed by LangRank as
    **unweighted** respondent shares, are a second, distinct family of ``-raw``
    metric IDs (:data:`RAW_METRICS`). Published values are weighted
    (``is_derived=False``); ``-raw`` values are unweighted
    (``is_derived=True``, ``derivation_method=`` :data:`RAW_DERIVATION_METHOD`); the
    two families never share a series.

    Acquisition is manual-only in both modes (:class:`JetBrainsSource`):
    ``--source published`` (default / ``auto``) reads the bundled curated CSV with no
    network request, and ``--source raw-data`` imports a local file the operator
    obtained out-of-band. The bundled dataset (subtask 05) and the raw-data import
    (subtask 06) land later; the pipeline methods here are honest stubs until then.

    :ivar provider_id: Stable rating ID used across the pipeline.
    """

    provider_id = _RATING_ID

    def __init__(self, cache_dir: Path) -> None:
        """Wire the provider's cache directory and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the ``jetbrains``
            subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        #: JetBrains labels the last :meth:`normalize` call could not resolve to a
        #: canonical language (documented :data:`JETBRAINS_NON_LANGUAGE_ANSWERS` are
        #: excluded); skipped rather than guessed and surfaced to validation
        #: (subtask 07).
        self.last_unmapped: list[str] = []

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: the published and ``-raw`` families.

        Performs no network or database access. Methodology notes are built from
        :func:`~langrank.providers.jetbrains_questions.wording_changes` for each
        published metric, so only JetBrains' **verified verbatim** wordings ever feed
        a note (unverified years are skipped, never invented).

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        metrics: list[MetricDefinition] = []
        for metric_id in PUBLISHED_METRICS:
            display_name, phrasing = _METRIC_LABELS[metric_id]
            metrics.append(
                MetricDefinition(
                    id=metric_id,
                    rating_id=self.provider_id,
                    display_name=f"{display_name} (%)",
                    unit=_UNIT_PERCENT,
                    higher_is_better=True,
                    description=(
                        f"Share of respondents who {phrasing}, as JetBrains published it - a weighted "
                        "percentage (raw, not derived). Weighted published values are never comparable with "
                        "the unweighted -raw shares and never share a series."
                    ),
                )
            )
            metrics.append(
                MetricDefinition(
                    id=raw_metric_id(metric_id),
                    rating_id=self.provider_id,
                    display_name=f"{display_name} (unweighted %)",
                    unit=_UNIT_PERCENT,
                    higher_is_better=True,
                    description=(
                        f"Unweighted share of respondents who {phrasing}, derived by LangRank over the "
                        "anonymized raw response dump (is_derived, "
                        f"derivation_method={RAW_DERIVATION_METHOD!r}). It differs from JetBrains' published "
                        "weighted figure and never shares a series with it."
                    ),
                )
            )
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="JetBrains Developer Ecosystem",
            description=(
                "JetBrains State of Developer Ecosystem: an annual self-reported survey of programming-"
                "language usage and intent. Three distinct questions (used in the last 12 months, primary "
                "language, planning to adopt) are separate metrics that are never merged. The default "
                "published mode carries JetBrains' weighted percentages; --source raw-data imports the "
                "anonymized response dump and stores LangRank's unweighted respondent shares under distinct "
                "-raw metric IDs. Manual-only in both modes (no automated network fetch)."
            ),
            homepage=HOMEPAGE,
            default_metric=METRIC_USED_LAST_12_MONTHS,
            native_granularity=Granularity.YEAR,
            caveats=[
                "Self-reported survey - not comparable with activity metrics (search, GitHub, SO tags).",
                "Published values are weighted; -raw values are unweighted respondent shares - "
                "different series, never comparable.",
                "primary_language and used_last_12_months answer different questions and are never merged.",
                "Question wording and answer sets can change between years (tracked per year in "
                "metadata_json['question_wording'] and surfaced as a methodology note on change).",
                "Raw-data licence: 2024/2025 editions are CC BY-NC-SA 4.0 (non-commercial); 2022/2023 are "
                "attribution-only. Raw files are never redistributed - they stay in the operator's local cache.",
            ],
            parser_version=PARSER_VERSION,
            metrics=metrics,
            methodology_notes=self._wording_methodology_notes(),
        )

    def _wording_methodology_notes(self) -> list[MethodologyNote]:
        """Build one :class:`MethodologyNote` per **verified** question-wording change.

        Iterates :data:`PUBLISHED_METRICS` and, for each, the
        :func:`~langrank.providers.jetbrains_questions.wording_changes` for that
        metric - which returns only years whose verbatim wording JetBrains has
        confirmed - so a note is emitted only for a real, verified wording (never a
        paraphrase or an invented string). Each note's span opens at the survey year
        the wording took effect and stays open (``valid_to=None``) until the next
        confirmed change supersedes it.

        :returns: One note per verified ``(metric, year, wording)`` change, ordered by
            metric then year.
        """
        notes: list[MethodologyNote] = []
        for metric_id in PUBLISHED_METRICS:
            for year, wording in wording_changes(metric_id):
                notes.append(
                    MethodologyNote(
                        rating_id=self.provider_id,
                        methodology_version=f"jetbrains-{metric_id}-wording-{year}",
                        valid_from=date(year, 1, 1),
                        valid_to=None,
                        description=(
                            f"{metric_id} question wording confirmed for the {year} survey: {wording!r}. "
                            "Wording can change between years; only verified verbatim wording is recorded."
                        ),
                        source_url=HOMEPAGE,
                    )
                )
        return notes

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw data for the selected acquisition mode.

        Resolves ``--source`` first, so an unknown mode is rejected here. The default
        ``published`` mode reads the bundled curated CSV (:data:`DATA_PATH`) with **no
        network request** (budget 0) - its bytes' integrity is assured by code review
        and the ``--offline`` flag is a no-op for it. ``--source raw-data`` imports the
        anonymized response dump from a local file and lands in subtask 06 (still a
        stub). The artifact ``url`` is the provider homepage; each row carries its own
        per-edition ``source_url`` for the parser.

        :param request: Fetch parameters; ``source`` (validated here) and ``no_cache``
            are honoured. The published dataset covers a fixed span, so the
            ``since`` / ``until`` / ``years`` window is not applied to it.
        :returns: The raw fetch payload for the selected mode.
        :raises ProviderError: If ``--source`` names an unknown mode.
        :raises NotImplementedError: Until subtask 06 lands the raw-data import path.
        """
        source = _resolve_source(request.source)
        if source is JetBrainsSource.RAW_DATA:
            raise NotImplementedError("jetbrains raw-data import lands in subtask 06.")
        content = DATA_PATH.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=HOMEPAGE,
            content=content,
            mime_type="text/csv",
            metadata_json={
                "mode": JetBrainsSource.PUBLISHED.value,
                "provenance": _PUBLISHED_PROVENANCE,
                "source_document_id": self.provider_id,
            },
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse the curated published-percentages CSV into per-language records.

        Hardens the untrusted CSV: the stdlib ``csv`` module is used (never ``eval``);
        non-UTF-8 bytes raise a :class:`~langrank.errors.ParseError` (a UTF-8 BOM is
        tolerated); a missing required column (:data:`_REQUIRED_COLUMNS`) raises a
        ``ParseError`` naming it; and an unknown ``metric``, an implausible ``year``, a
        percent outside ``0..100``, a non-positive ``sample_size`` or a blank
        ``population`` each raise a ``ParseError`` naming the offending row. A row for a
        ``(year, metric)`` the registry says was **not** asked
        (:func:`~langrank.providers.jetbrains_questions.question_for` is ``None``) is
        rejected too, so a mis-yeared row never lands. Each mapped row yields one
        percentage record (no rank metric - JetBrains publishes percentages only); the
        row's ``question_wording`` / ``wording_verified``, ``sample_size``,
        ``population``, ``source_url`` and ``published_at`` are carried for
        :meth:`normalize`. Records are annual (:attr:`Granularity.YEAR`).

        :param raw: The raw curated-CSV fetch payload.
        :returns: One percentage record per curated row.
        :raises ParseError: On a decoding error, a missing required column, an unknown
            or unasked ``(year, metric)``, or a malformed / out-of-range cell.
        """
        try:
            text = raw.content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError("jetbrains CSV must be UTF-8 encoded.") from exc
        reader = csv.DictReader(text.splitlines())
        fieldnames = reader.fieldnames or []
        for column in _REQUIRED_COLUMNS:
            if column not in fieldnames:
                raise ParseError(f"jetbrains CSV is missing required column {column!r}.")
        return [_record_from_row(row) for row in reader]

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations with full provenance.

        :data:`~langrank.normalization.JETBRAINS_NON_LANGUAGE_ANSWERS` is consulted
        **before** resolution, so markup / meta-answers (``HTML / CSS``, ``Other``,
        ``GraphQL`` ...) and JetBrains' classic-VB ``Visual Basic`` are skipped
        silently - no observation, no ``unmapped_language`` warning - and never fold
        into ``vb.net`` via the global alias. Any other label that resolves to no
        canonical language is skipped and recorded in :attr:`last_unmapped` (never
        guessed) for validation (subtask 07).

        Published values are JetBrains' own weighted percentages, emitted verbatim
        (``is_derived=False``, ``derivation_method=None``, ``unit='percent'``). The
        edition identifies the document (``source_document_id=jetbrains-devecosystem-{year}``);
        the survey year is the period; ``sample_size`` and ``population`` come from the
        row; and ``metadata_json`` carries the registry ``question_wording`` (``None``
        when unverified - never invented) plus ``wording_verified``. Pure over its
        inputs: no network, no database.

        :param records: Parsed per-language source records.
        :returns: One observation per mapped record; empty when none map.
        """
        self.last_unmapped = []
        observations: list[Observation] = []
        for record in records:
            label = record.language
            if label in JETBRAINS_NON_LANGUAGE_ANSWERS:
                continue
            language_id = self._normalizer.try_resolve(label, rating_id=self.provider_id)
            if language_id is None:
                if label not in self.last_unmapped:
                    self.last_unmapped.append(label)
                continue
            observations.append(
                build_observation(
                    record=record,
                    language_id=language_id,
                    parser_version=PARSER_VERSION,
                    retrieved_at=self._retrieved_at,
                    is_derived=False,
                    derivation_method=None,
                    source_document_id=f"jetbrains-devecosystem-{record.period_start.year}",
                    source_published_at=_published_at(record.metadata.get("published_at")),
                    sample_size=record.metadata.get("sample_size"),
                    population=record.metadata.get("population"),
                )
            )
        return observations

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named codes (lands in subtask 07).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Until subtask 07 lands validation.
        """
        raise NotImplementedError("jetbrains validate lands in subtask 07.")


def _published_at(value: object) -> Optional[datetime]:
    """Parse a curated ``published_at`` cell into an aware UTC datetime.

    JetBrains prints no publication date for any edition, so the column is empty
    throughout; an empty (or missing) cell therefore yields ``None`` rather than a
    fabricated date.

    :param value: The row's ``published_at`` cell (``str`` or ``None``).
    :returns: The date at UTC midnight, or ``None`` when the cell is blank.
    """
    text = str(value or "").strip()
    if not text:
        return None
    return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)


def _record_from_row(row: dict[str, Any]) -> SourceRecord:
    """Build one percentage :class:`~langrank.models.SourceRecord` from a curated row.

    The row's ``metric`` must be one of :data:`PUBLISHED_METRICS`, its ``year`` must be
    plausible and asked for that metric (:func:`~langrank.providers.jetbrains_questions.question_for`),
    its ``percent`` must lie in ``0..100`` (JetBrains ships whole-percent figures and
    prints ``0`` values, which are kept), its ``sample_size`` must be a positive integer
    and its ``population`` must be non-empty. The verified/registry ``question_wording``
    and ``wording_verified`` flag are attached to the record metadata here (from the pure
    registry) so they travel into ``metadata_json`` unchanged; wording is never invented.

    :param row: A curated CSV row keyed by column name.
    :returns: The percentage record for the ``(year, metric, language)`` cell.
    :raises ParseError: If the metric is unknown, the year implausible or unasked, or a
        numeric / required cell is malformed.
    """
    try:
        year = int(row["year"])
        metric_id = row["metric"]
        language = row["language"]
        percent = float(row["percent"])
        sample_size = int(row["sample_size"])
        population = (row["population"] or "").strip()
        source_url = row["source_url"]
        published_at = (row["published_at"] or "").strip()
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"jetbrains row is malformed: {row!r}") from exc
    if metric_id not in PUBLISHED_METRICS:
        raise ParseError(f"jetbrains row has unknown metric {metric_id!r}: {row!r}")
    if not 2000 <= year <= 2100:
        raise ParseError(f"jetbrains year is implausible: {row!r}")
    question = question_for(year, metric_id)
    if question is None:
        raise ParseError(f"jetbrains metric {metric_id!r} was not asked in {year}: {row!r}")
    if not _PERCENT_MIN <= percent <= _PERCENT_MAX:
        raise ParseError(f"jetbrains percent must be in 0..100: {row!r}")
    if sample_size <= 0:
        raise ParseError(f"jetbrains sample_size must be positive: {row!r}")
    if not population:
        raise ParseError(f"jetbrains population must not be empty: {row!r}")
    metadata: dict[str, Any] = {
        "provenance": _PUBLISHED_PROVENANCE,
        "sample_size": sample_size,
        "population": population,
        "published_at": published_at,
        "question_wording": question.wording,
        "wording_verified": question.wording_verified,
    }
    return SourceRecord(
        rating_id=_RATING_ID,
        metric_id=metric_id,
        language=language,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=None,
        value=percent,
        unit=_UNIT_PERCENT,
        source_url=source_url,
        metadata=metadata,
    )
