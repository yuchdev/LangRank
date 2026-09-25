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
    :ivar chart_legend: The chart legend / heading JetBrains printed above this
        metric's values, when the source note records one but the verbatim
        question text is not yet confirmed. A legend proves the metric *was*
        asked that year; it is **not** question wording and never sets
        :attr:`wording_verified`. ``None`` when no legend is on record.
    """

    year: int
    metric_id: str
    question_id: Optional[str]
    wording: Optional[str]
    wording_verified: bool
    raw_column_prefix: Optional[str]
    chart_legend: Optional[str] = None


# Verbatim question wordings confirmed by the source note / curated NOTES, keyed
# by ``(year, metric_id)``. This is the single place a transcriber edits when a
# new year's exact string is confirmed. Only full question text JetBrains
# actually printed belongs here; chart legends, group labels and headings are
# not wording and live in :data:`_CHART_LEGENDS`.
_VERBATIM_WORDINGS: dict[tuple[int, str], str] = {
    (2018, METRIC_USED_LAST_12_MONTHS): "What programming language(s) do you regularly use?",
    (2018, METRIC_PLANNED_ADOPTION): (
        "Do you plan to adopt / migrate to other language(s) in the next 12 months? If so, to which one(s)?"
    ),
    (2019, METRIC_USED_LAST_12_MONTHS): "What programming languages have you used in the last 12 months?",
    (2019, METRIC_PRIMARY_LANGUAGE): ("What are your primary programming languages? Choose no more than 3 languages."),
    (2023, METRIC_USED_LAST_12_MONTHS): (
        "Which programming, scripting, and markup languages have you used in the last 12 months?"
    ),
    (2024, METRIC_USED_LAST_12_MONTHS): "Which programming languages have you used in the last 12 months?",
}

# Chart legends / headings the source note quotes. These are **not** question
# wording (they never set ``wording_verified``); they are kept only as provenance
# that a metric was asked in a year whose verbatim question text is still
# unconfirmed - notably 2017, where the "To be adopted / migrated to soon (%)"
# legend proves the planned-adoption metric was asked.
_CHART_LEGENDS: dict[tuple[int, str], str] = {
    (2017, METRIC_USED_LAST_12_MONTHS): "Used regularly (%)",
    (2017, METRIC_PRIMARY_LANGUAGE): "Primary Programming Language (%)",
    (2017, METRIC_PLANNED_ADOPTION): "To be adopted / migrated to soon (%)",
}


def _question(year: int, metric_id: str) -> SurveyQuestion:
    """Build one registry row, attaching verbatim wording only where confirmed.

    Verbatim wording is taken from :data:`_VERBATIM_WORDINGS` (and only then is
    ``wording_verified`` set); any chart legend on record is attached for
    provenance but never treated as wording.

    :param year: Survey year.
    :param metric_id: Published metric ID.
    :returns: The :class:`SurveyQuestion` for ``(year, metric_id)``.
    """
    wording = _VERBATIM_WORDINGS.get((year, metric_id))
    return SurveyQuestion(
        year=year,
        metric_id=metric_id,
        question_id=None,
        wording=wording,
        wording_verified=wording is not None,
        raw_column_prefix=None,
        chart_legend=_CHART_LEGENDS.get((year, metric_id)),
    )


# Years JetBrains has run the survey (source note Editions table, 2017-2025).
_SURVEY_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)

# Years whose primary-language percentages JetBrains did **not** publish. 2018
# rendered "Primary programming languages" only as a rank podium (no
# percentages), so the published dataset carries no 2018 primary rows and
# ``question_for(2018, primary)`` is ``None``.
_PRIMARY_UNPUBLISHED_YEARS: frozenset[int] = frozenset({2018})


def _build_registry() -> tuple[SurveyQuestion, ...]:
    """Assemble the full registry from the source note.

    Every survey year carries a ``used_last_12_months`` and a
    ``planned_adoption`` question (planned adoption was asked from the first,
    2017, edition - its "To be adopted / migrated to soon (%)" legend proves
    it); ``primary_language`` is present for every year except those in
    :data:`_PRIMARY_UNPUBLISHED_YEARS`.

    :returns: Every known ``(year, metric)`` question, ordered by year then
        metric.
    """
    entries: list[SurveyQuestion] = []
    for year in _SURVEY_YEARS:
        entries.append(_question(year, METRIC_USED_LAST_12_MONTHS))
        if year not in _PRIMARY_UNPUBLISHED_YEARS:
            entries.append(_question(year, METRIC_PRIMARY_LANGUAGE))
        entries.append(_question(year, METRIC_PLANNED_ADOPTION))
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
