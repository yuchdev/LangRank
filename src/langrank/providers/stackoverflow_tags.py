from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

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

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "stackoverflow-tags-v1"

#: Metric ID for the raw monthly new-question count per language tag.
METRIC_QUESTIONS = "stackoverflow-tags-questions"

#: Metric ID for the derived monthly question share (percent of a stated denominator).
METRIC_SHARE = "stackoverflow-tags-question-share"

#: Metric ID for the derived monthly rank (Stack Overflow publishes no rank).
METRIC_RANK = "stackoverflow-tags-rank"

#: Homepage for the Stack Overflow tag index.
HOMEPAGE = "https://stackoverflow.com/tags"

#: Master Stack Overflow tag per canonical language.
#:
#: ``api`` mode queries exactly one master tag per language, so this map holds the
#: single tag Stack Overflow merges its synonyms into (e.g. ``cpp`` -> ``c++``,
#: ``golang`` -> ``go``). Keys are the source tag strings; values are canonical
#: language IDs. Every key resolves through
#: :meth:`LanguageNormalizer.resolve` with ``rating_id="stackoverflow-tags"``.
TAG_TO_LANGUAGE: dict[str, str] = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "c#": "c#",
    "c++": "c++",
    "c": "c",
    "php": "php",
    "go": "go",
    "rust": "rust",
    "kotlin": "kotlin",
    "swift": "swift",
    "ruby": "ruby",
    "r": "r",
    "scala": "scala",
    "dart": "dart",
    "objective-c": "objective-c",
    "perl": "perl",
    "lua": "lua",
    "haskell": "haskell",
    "elixir": "elixir",
    "julia": "julia",
    "matlab": "matlab",
    "sql": "sql",
    "assembly": "assembly",
    "groovy": "groovy",
    "powershell": "powershell",
    "bash": "shell",
    "vb.net": "vb.net",
    "fortran": "fortran",
    "cobol": "cobol",
    "ada": "ada",
    "delphi": "delphi",
    "zig": "zig",
}


class StackOverflowTagsProvider:
    """Records monthly Stack Overflow question activity per language tag.

    This provider measures *tag activity* (new-question counts) - a different
    signal from ``stackoverflow-survey`` (self-reported usage); the two are never
    conflated. It publishes a raw ``questions`` count plus a derived
    ``question-share`` (preferred for long-term comparison) and a derived ``rank``.

    :ivar provider_id: Stable rating ID used across the pipeline.
    """

    provider_id = "stackoverflow-tags"

    def __init__(self, cache_dir: Path) -> None:
        """Wire the provider's cache directory and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the
            ``stackoverflow-tags`` subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: metrics, caveats and methodology.

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Stack Overflow Tags",
            description=("Monthly Stack Overflow question activity per language tag (tag activity, not usage)."),
            homepage=HOMEPAGE,
            default_metric=METRIC_SHARE,
            native_granularity=Granularity.MONTH,
            caveats=[
                "Tag activity, not usage - not comparable with stackoverflow-survey.",
                "Shares can sum above 100% (multi-tag questions).",
                "Share denominator differs by --source.",
                "Overall SO question volume declined sharply after 2022; prefer share over counts.",
            ],
            parser_version=PARSER_VERSION,
            metrics=[
                MetricDefinition(
                    id=METRIC_QUESTIONS,
                    rating_id=self.provider_id,
                    display_name="Questions",
                    unit="count",
                    higher_is_better=True,
                    description="Monthly count of new Stack Overflow questions carrying the language's master tag.",
                ),
                MetricDefinition(
                    id=METRIC_SHARE,
                    rating_id=self.provider_id,
                    display_name="Question share (%)",
                    unit="percent",
                    higher_is_better=True,
                    description=(
                        "Derived monthly question share. Denominator depends on --source: "
                        "'api' divides by all_questions (site-wide new-question total); "
                        "'sede' divides by tracked_language_union (deduplicated union of tracked "
                        "master tags). The two denominators are never mixed in one series."
                    ),
                ),
                MetricDefinition(
                    id=METRIC_RANK,
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Derived monthly ordinal rank (1 is best); Stack Overflow publishes no rank.",
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="api-all-questions-v1",
                    valid_from=date(2008, 9, 1),
                    valid_to=None,
                    description=(
                        "'api' source: share denominator is all_questions, the site-wide new-question "
                        "total from a filter=total call with no tag "
                        "(derivation_method='question_share:all_questions')."
                    ),
                    source_url="https://api.stackexchange.com/2.3/questions",
                ),
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="sede-tracked-union-v1",
                    valid_from=date(2008, 9, 1),
                    valid_to=None,
                    description=(
                        "'sede' source: share denominator is tracked_language_union, the deduplicated "
                        "union of questions carrying any tracked master tag "
                        "(derivation_method='question_share:tracked_language_union')."
                    ),
                    source_url="https://data.stackexchange.com/",
                ),
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw tag activity (implemented in subtask 04).

        :param request: Fetch parameters (date window, source mode, cache flags).
        :returns: The raw fetch payload.
        :raises NotImplementedError: Always, until subtask 04 lands the fetcher.
        """
        raise NotImplementedError("stackoverflow-tags fetch lands in subtask 04.")

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw payload into source records (implemented in subtask 05).

        :param raw: The raw fetch payload.
        :returns: Parsed source records.
        :raises NotImplementedError: Always, until subtask 05 lands the parser.
        """
        raise NotImplementedError("stackoverflow-tags parse lands in subtask 05.")

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations (implemented in subtask 05).

        :param records: Parsed source records.
        :returns: Canonical observations.
        :raises NotImplementedError: Always, until subtask 05 lands normalization.
        """
        raise NotImplementedError("stackoverflow-tags normalize lands in subtask 05.")

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations with named codes (implemented in subtask 06).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Always, until subtask 06 lands validation.
        """
        raise NotImplementedError("stackoverflow-tags validate lands in subtask 06.")
