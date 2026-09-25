"""Per-year, per-metric JetBrains survey question registry.

Encodes, for each *State of Developer Ecosystem* survey year and language
metric, the question identifier and wording, so that every observation the
JetBrains provider emits can carry the exact question it answers (into
``metadata_json["question_wording"]``) and so wording drift can be surfaced as a
``MethodologyNote``.

The registry is a **pure data module**: no I/O, no network, no DB access. It is
transcribed from ``docs/source-notes/jetbrains.md`` (the Editions table).

Wording is only ever stored when JetBrains publishes the **verbatim** question
string; where the source note has not yet confirmed verbatim wording for a
year, ``wording`` is ``None`` and :attr:`SurveyQuestion.wording_verified` is
``False``. Wording is never invented - as the parallel transcription confirms
more years, add or update the corresponding :class:`SurveyQuestion` entries and
flip ``wording_verified`` to ``True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Metric IDs (published, weighted percentages). The raw-data mode reuses these
#: with a ``-raw`` suffix; both modes answer the *same* survey question, so
#: :func:`question_for` resolves a ``-raw`` metric to its published question.
METRIC_USED_LAST_12_MONTHS = "jetbrains-used-last-12-months"
METRIC_PRIMARY_LANGUAGE = "jetbrains-primary-language"
METRIC_PLANNED_ADOPTION = "jetbrains-planned-adoption"

#: Suffix distinguishing derived, unweighted respondent-share metric IDs.
RAW_METRIC_SUFFIX = "-raw"


@dataclass(frozen=True)
class SurveyQuestion:
    """A single JetBrains survey question for one year and one metric.

    :ivar year: Survey year (the survey ``period``, e.g. ``2024``).
    :ivar metric_id: Published metric ID this question feeds (one of the
        ``METRIC_*`` constants; the ``-raw`` variants share the same question).
    :ivar question_id: JetBrains' own question/field identifier when known,
        else ``None`` (not yet transcribed).
    :ivar wording: Exact verbatim question text, or ``None`` when JetBrains'
        verbatim wording for this year has not been confirmed. Never a
        paraphrase or invented text.
    :ivar wording_verified: ``True`` only when :attr:`wording` is JetBrains'
        confirmed verbatim string; ``False`` when unverified (then
        :attr:`wording` is ``None``).
    :ivar raw_column_prefix: Column-name prefix locating this question's
        answers in the raw-data dump (used by subtask 06), or ``None`` when the
        raw schema for the year has not been transcribed.
    """

    year: int
    metric_id: str
    question_id: Optional[str]
    wording: Optional[str]
    wording_verified: bool
    raw_column_prefix: Optional[str]


# Verbatim wordings confirmed by the source note. Keep this the single place a
# transcriber edits when a new year's exact string is confirmed.
_VERBATIM_USED_LAST_12_MONTHS_2024 = "Which programming languages have you used in the last 12 months?"


def _used_last_12_months(year: int) -> SurveyQuestion:
    """Build the ``used_last_12_months`` question row for ``year``.

    :param year: Survey year.
    :returns: The :class:`SurveyQuestion`, with verbatim wording only where the
        source note confirms it.
    """
    if year == 2024:
        return SurveyQuestion(
            year=year,
            metric_id=METRIC_USED_LAST_12_MONTHS,
            question_id=None,
            wording=_VERBATIM_USED_LAST_12_MONTHS_2024,
            wording_verified=True,
            raw_column_prefix=None,
        )
    return SurveyQuestion(
        year=year,
        metric_id=METRIC_USED_LAST_12_MONTHS,
        question_id=None,
        wording=None,
        wording_verified=False,
        raw_column_prefix=None,
    )


def _unverified(year: int, metric_id: str) -> SurveyQuestion:
    """Build an as-yet-unverified question row.

    :param year: Survey year.
    :param metric_id: Published metric ID.
    :returns: A :class:`SurveyQuestion` with ``wording=None`` and
        ``wording_verified=False``.
    """
    return SurveyQuestion(
        year=year,
        metric_id=metric_id,
        question_id=None,
        wording=None,
        wording_verified=False,
        raw_column_prefix=None,
    )


# Years JetBrains has run the survey (source note Editions table, 2017-2025).
_SURVEY_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)

# The first edition (2017) had no "planning to adopt" question.
_PLANNED_ADOPTION_FIRST_YEAR = 2018


def _build_registry() -> tuple[SurveyQuestion, ...]:
    """Assemble the full registry from the source note.

    :returns: Every known ``(year, metric)`` question, ordered by year then
        metric.
    """
    entries: list[SurveyQuestion] = []
    for year in _SURVEY_YEARS:
        entries.append(_used_last_12_months(year))
        entries.append(_unverified(year, METRIC_PRIMARY_LANGUAGE))
        if year >= _PLANNED_ADOPTION_FIRST_YEAR:
            entries.append(_unverified(year, METRIC_PLANNED_ADOPTION))
    return tuple(entries)


#: The full registry, transcribed from ``docs/source-notes/jetbrains.md``.
QUESTION_REGISTRY: tuple[SurveyQuestion, ...] = _build_registry()

# ``(year, metric_id) -> SurveyQuestion`` lookup, keyed by published metric ID.
_BY_KEY: dict[tuple[int, str], SurveyQuestion] = {(q.year, q.metric_id): q for q in QUESTION_REGISTRY}


def base_metric_id(metric_id: str) -> str:
    """Return the published metric ID underlying a possibly ``-raw`` metric ID.

    :param metric_id: A published (``jetbrains-...``) or derived
        (``jetbrains-...-raw``) metric ID.
    :returns: The published metric ID (``-raw`` suffix stripped).
    """
    if metric_id.endswith(RAW_METRIC_SUFFIX):
        return metric_id[: -len(RAW_METRIC_SUFFIX)]
    return metric_id


def question_for(year: int, metric_id: str) -> Optional[SurveyQuestion]:
    """Look up the survey question for ``year`` and ``metric_id``.

    A ``-raw`` metric ID resolves to its published question, since both
    acquisition modes answer the same survey question.

    :param year: Survey year.
    :param metric_id: Published or ``-raw`` metric ID.
    :returns: The :class:`SurveyQuestion`, or ``None`` when the question was not
        asked that year (e.g. planned-adoption in 2017).
    """
    return _BY_KEY.get((year, base_metric_id(metric_id)))


def wording_changes(metric_id: str) -> list[tuple[int, str]]:
    """Years where the **verified** wording for a metric changed.

    Considers only entries whose wording is confirmed verbatim
    (``wording_verified=True``); unverified years (``wording is None``) are
    skipped so that no fabricated wording ever feeds a methodology note. The
    first confirmed wording is reported as a change (it establishes the
    baseline); each later confirmed wording that differs from the previous
    confirmed one is reported too.

    :param metric_id: Published or ``-raw`` metric ID.
    :returns: ``(year, wording)`` pairs in ascending year order.
    """
    base = base_metric_id(metric_id)
    changes: list[tuple[int, str]] = []
    previous: Optional[str] = None
    for question in QUESTION_REGISTRY:
        if question.metric_id != base:
            continue
        if not question.wording_verified or question.wording is None:
            continue
        if question.wording != previous:
            changes.append((question.year, question.wording))
            previous = question.wording
    return changes
