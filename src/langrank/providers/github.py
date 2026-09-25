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

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "github"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "github-v1"

#: Homepage for the GitHub language-data landing page.
HOMEPAGE = "https://innovationgraph.github.com/global-metrics/programming-languages"

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

    def __init__(self, cache_dir: Path) -> None:
        """Wire the provider's cache directory and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the ``github``
            subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)

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
        """Fetch raw data for the selected variant (implemented in subtasks 05/07).

        Resolves ``--source`` to a variant first, so an unknown source is rejected
        here; the actual per-variant fetch lands later.

        :param request: Fetch parameters (date window, source mode, cache flags).
        :returns: The raw fetch payload whose artifact metadata carries the variant.
        :raises ProviderError: If ``--source`` names an unknown variant.
        :raises NotImplementedError: For a known variant, until subtasks 05/07 land
            the Innovation Graph and Octoverse fetchers.
        """
        source = _resolve_source(request.source)
        if source is GitHubSource.INNOVATION_GRAPH:
            raise NotImplementedError("github innovation-graph fetch lands in subtask 05.")
        raise NotImplementedError("github octoverse fetch lands in subtask 07.")

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw payload into source records (implemented in subtasks 05/07).

        Dispatches on the payload's variant, set by :meth:`fetch`.

        :param raw: The raw fetch payload.
        :returns: Parsed source records.
        :raises NotImplementedError: Always, until subtasks 05/07 land the parsers.
        """
        raise NotImplementedError("github parse lands in subtasks 05/07.")

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
