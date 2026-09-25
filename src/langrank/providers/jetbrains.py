from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Optional

from langrank.errors import ProviderError
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
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
    RAW_METRIC_SUFFIX,
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
        """Fetch raw data for the selected acquisition mode (lands in subtasks 05/06).

        Resolves ``--source`` first, so an unknown mode is rejected here. The default
        ``published`` mode reads the bundled curated CSV (no network) and lands in
        subtask 05; ``--source raw-data`` imports the anonymized response dump from a
        local file and lands in subtask 06. Both pipeline paths are honest stubs
        until then.

        :param request: Fetch parameters; only ``source`` (validated here) is
            consulted until the dataset paths land.
        :returns: The raw fetch payload for the selected mode.
        :raises ProviderError: If ``--source`` names an unknown mode.
        :raises NotImplementedError: Until subtask 05 (published) / 06 (raw-data)
            land the dataset paths.
        """
        source = _resolve_source(request.source)
        if source is JetBrainsSource.RAW_DATA:
            raise NotImplementedError("jetbrains raw-data import lands in subtask 06.")
        raise NotImplementedError("jetbrains published fetch lands in subtask 05.")

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw payload into per-language source records (lands in subtask 05/06).

        :param raw: The raw fetch payload.
        :returns: One source record per published percentage (published mode) or per
            respondent-share tally (raw-data mode).
        :raises NotImplementedError: Until subtask 05 (published) / 06 (raw-data)
            land the parser.
        """
        raise NotImplementedError("jetbrains parse lands in subtask 05.")

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations (lands in subtask 05/06).

        The normalizer will consult
        :data:`~langrank.normalization.JETBRAINS_NON_LANGUAGE_ANSWERS` **before**
        attempting resolution so meta-answers and JetBrains' classic-VB
        ``Visual Basic`` are skipped without folding into ``vb.net`` via the global
        alias. Published values are emitted ``is_derived=False``; ``-raw`` values are
        emitted ``is_derived=True`` with ``derivation_method=`` :data:`RAW_DERIVATION_METHOD`.

        :param records: Parsed source records.
        :returns: One observation per mapped record.
        :raises NotImplementedError: Until subtask 05 (published) / 06 (raw-data)
            land normalization.
        """
        raise NotImplementedError("jetbrains normalize lands in subtask 05.")

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named codes (lands in subtask 07).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Until subtask 07 lands validation.
        """
        raise NotImplementedError("jetbrains validate lands in subtask 07.")
