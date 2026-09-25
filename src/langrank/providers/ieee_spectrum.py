from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
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

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "ieee-spectrum"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "ieee-spectrum-v1"

#: Landing page for the latest verified IEEE Spectrum edition; each curated CSV
#: row carries its own per-edition ``source_url`` (subtask 04), so this is only
#: the artifact-level provenance URL.
HOMEPAGE = "https://spectrum.ieee.org/top-programming-languages-2025"


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


class IeeeSpectrumProvider:
    """Records IEEE Spectrum *Top Programming Languages* rank and score per profile.

    Each edition re-weights one metric set into several ranking *profiles*
    (:class:`IeeeProfile`); every profile is stored as its **own** metric pair
    (``ieee-spectrum-{profile}-rank`` / ``ieee-spectrum-{profile}-score``), so a
    query never mixes profiles into one series. The published score is IEEE's own
    relative figure (top language = 100) and is stored raw (``is_derived=False``,
    landed in subtask 05). The score is renormalized per edition and the metric set
    changes between editions, so ranks and scores are **not comparable across
    editions** and only comparable within one edition's one profile.

    Acquisition is manual transcription only: there is no downloadable dataset and
    no network fetch (0 requests). The curated bundled CSV and the
    ``langrank import`` path land in subtask 04; the pipeline methods here are
    honest stubs until then.

    :ivar provider_id: Stable rating ID used across the pipeline.
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
        """Read the curated IEEE Spectrum edition dataset (lands in subtask 04).

        Acquisition is manual transcription only - a bundled CSV read with no
        network request - but the curated dataset and its reader land in subtask 04.

        :param request: Fetch parameters (unused until subtask 04).
        :returns: The raw curated-CSV fetch payload.
        :raises NotImplementedError: Until subtask 04 lands the bundled dataset.
        """
        raise NotImplementedError("ieee-spectrum fetch lands in subtask 04.")

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse the curated edition CSV into per-profile source records (subtask 05).

        :param raw: The raw curated-CSV fetch payload.
        :returns: One source record per published rank/score.
        :raises NotImplementedError: Until subtask 05 lands the parser.
        """
        raise NotImplementedError("ieee-spectrum parse lands in subtask 05.")

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize per-profile records into observations (lands in subtask 05).

        The normalizer will consult :data:`~langrank.normalization.IEEE_UNTRACKED_LABELS`
        **before** attempting resolution so documented markup / hardware labels (and
        IEEE's classic-VB ``Visual Basic``) are skipped without emitting an
        ``unmapped_language`` warning and without folding into ``vb.net``.

        :param records: Parsed per-profile source records.
        :returns: One observation per mapped record.
        :raises NotImplementedError: Until subtask 05 lands normalization.
        """
        raise NotImplementedError("ieee-spectrum normalize lands in subtask 05.")

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named codes (lands in subtask 06).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Until subtask 06 lands validation.
        """
        raise NotImplementedError("ieee-spectrum validate lands in subtask 06.")
