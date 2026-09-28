"""Contract tests for the IEEE Spectrum provider (fixture-driven, no network).

The fixture (``tests/fixtures/ieee-spectrum/sample.csv``) is a verbatim subset of
the bundled edition dataset - two editions on different published-score scales
(2022 = ``0-100``, 2024 = ``0-1``), all three profiles, five languages including
the untracked ``HTML`` label and an ``Ada``/``Haskell`` competition-ranking tie.
See ``tests/fixtures/ieee-spectrum/SOURCE.md`` for the selection rule.

Every assertion targets a downstream-visible field so a silently mis-normalized
value fails loudly: profiles are never merged, ranks are derived while scores are
raw, each edition's score scale is preserved, untracked labels vanish without a
warning, and the raw record hash is deterministic.
"""

from __future__ import annotations

from pathlib import Path

from _golden import assert_matches_golden

from langrank.models import Observation, Severity
from langrank.providers.base import FetchPayload
from langrank.providers.ieee_spectrum import (
    PARSER_VERSION,
    RANK_DERIVATION_METHOD,
    IeeeProfile,
    IeeeSpectrumProvider,
    rank_metric_id,
    score_metric_id,
)

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "ieee-spectrum"

#: Every rank/score metric id owned by each profile; the three sets must be
#: pairwise disjoint so a query for one profile can never return another's rows.
_PROFILE_METRICS: dict[IeeeProfile, frozenset[str]] = {
    profile: frozenset({rank_metric_id(profile), score_metric_id(profile)}) for profile in IeeeProfile
}


def _payload(name: str) -> FetchPayload:
    """Build an artifact-free payload from a fixture file (no network).

    :param name: Fixture filename under ``tests/fixtures/ieee-spectrum``.
    :returns: A :class:`FetchPayload` wrapping the fixture bytes.
    """
    return FetchPayload(artifact=None, content=(_FIXTURES / name).read_bytes())


def _provider(tmp_path: Path) -> IeeeSpectrumProvider:
    """Construct the provider with an isolated, never-touched cache dir.

    :param tmp_path: pytest-provided temp directory.
    :returns: A fresh provider instance.
    """
    return IeeeSpectrumProvider(tmp_path)


def _observations(tmp_path: Path) -> tuple[IeeeSpectrumProvider, list[Observation]]:
    """Return the provider and its normalized observations for the sample fixture."""
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(_payload("sample.csv")))
    return provider, observations


def test_ieee_spectrum_matches_golden(tmp_path: Path) -> None:
    """The sample fixture normalizes to the golden output, field for field.

    Guards every downstream-visible field (``language_id``, ``metric_id``,
    ``rank``, ``value``, ``unit``, ``is_derived``, ``derivation_method``,
    ``source_document_id``, ``source_published_at``, ``raw_record_hash`` and the
    per-edition ``score_scale`` in ``metadata_json``) against silent drift.
    """
    _, observations = _observations(tmp_path)
    assert_matches_golden(observations, _FIXTURES / "expected_observations.json")


def test_ieee_spectrum_profiles_write_disjoint_metrics(tmp_path: Path) -> None:
    """Each profile emits only its own metric ids and the three id sets are disjoint.

    Profile is baked into every metric id precisely so a query can never silently
    merge the ``spectrum``, ``jobs`` and ``trending`` rankings onto one axis; if a
    metric leaked across profiles the three different weightings would be conflated.
    """
    _, observations = _observations(tmp_path)

    metrics_by_profile: dict[str, set[str]] = {}
    for observation in observations:
        profile = str(observation.metadata_json["profile"])
        metrics_by_profile.setdefault(profile, set()).add(observation.metric_id)

    assert set(metrics_by_profile) == {profile.value for profile in IeeeProfile}
    for profile in IeeeProfile:
        assert metrics_by_profile[profile.value] == set(_PROFILE_METRICS[profile])
    # Every metric id carries exactly one profile; no id appears under two profiles.
    all_pairs = [(profile, metric) for profile, metrics in metrics_by_profile.items() for metric in metrics]
    assert len({metric for _, metric in all_pairs}) == len(all_pairs)


def test_ieee_spectrum_rank_is_derived_score_is_raw(tmp_path: Path) -> None:
    """Ranks are derived by competition ranking; scores are published raw.

    Protects the provenance invariant: IEEE's data file has no rank column, so a
    rank is a reconstruction and must be flagged ``is_derived`` with the named
    method, while the published score must never be flagged derived or a
    reconstruction would be presented as source data.
    """
    _, observations = _observations(tmp_path)

    ranks = [o for o in observations if o.metric_id.endswith("-rank")]
    scores = [o for o in observations if o.metric_id.endswith("-score")]
    assert len(ranks) == 24
    assert len(scores) == 24

    assert all(o.is_derived is True and o.derivation_method == RANK_DERIVATION_METHOD for o in ranks)
    assert all(o.unit == "rank" and o.rank is not None and o.rank > 0 for o in ranks)
    assert all(o.is_derived is False and o.derivation_method is None for o in scores)
    assert {o.unit for o in scores} == {"score"}
    assert all(o.parser_version == PARSER_VERSION for o in observations)


def test_ieee_spectrum_score_scale_preserved_per_edition(tmp_path: Path) -> None:
    """Each edition's published-score scale is carried and never rescaled.

    2022 scores live on a ``0-100`` scale (top language = 100) and 2024 on ``0-1``
    (top language = 1). Mixing the two axes - e.g. rescaling 100 to 1 - would
    fabricate values, so the scale label and the raw score are asserted exactly.
    """
    _, observations = _observations(tmp_path)
    scores = [o for o in observations if o.metric_id.endswith("-score")]

    scale_2022 = {o.metadata_json["score_scale"] for o in scores if o.period_start.year == 2022}
    scale_2024 = {o.metadata_json["score_scale"] for o in scores if o.period_start.year == 2024}
    assert scale_2022 == {"0-100"}
    assert scale_2024 == {"0-1"}

    def score(year: int, profile: IeeeProfile, language_id: str) -> float:
        match = next(
            o
            for o in scores
            if o.period_start.year == year and o.metric_id == score_metric_id(profile) and o.language_id == language_id
        )
        assert match.value is not None
        return match.value

    # Top language keeps its published top-of-scale value under each edition's scale.
    assert score(2022, IeeeProfile.SPECTRUM, "python") == 100.0
    assert score(2024, IeeeProfile.SPECTRUM, "python") == 1.0
    # A mid-list published score is stored verbatim on its own edition scale.
    assert score(2022, IeeeProfile.SPECTRUM, "c++") == 88.58016118
    assert score(2024, IeeeProfile.TRENDING, "c++") == 0.430457737


def test_ieee_spectrum_untracked_label_produces_no_observation_or_warning(tmp_path: Path) -> None:
    """The untracked ``HTML`` label yields no observation and no warning.

    ``HTML`` is a documented ``IEEE_UNTRACKED_LABELS`` markup label: it is skipped
    before resolution, so it must never become an observation, never appear in
    ``last_unmapped``, and never raise an ``unmapped_language`` warning - it is a
    known non-language, not a mapping failure.
    """
    provider, observations = _observations(tmp_path)

    # HTML is present six times in the fixture (once per edition/profile) yet maps
    # to nothing: only the four mappable languages survive.
    assert {o.language_id for o in observations} == {"python", "c++", "ada", "haskell"}
    assert provider.last_unmapped == []

    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.code == "unmapped_language"]


def test_ieee_spectrum_competition_tie_shares_rank_without_error(tmp_path: Path) -> None:
    """Ada and Haskell share rank 44 in 2024 jobs with equal scores; validate is ok.

    A legitimate competition-ranking tie shares a rank *and* an equal score, so it
    must not raise ``duplicate_rank`` (only a shared rank with differing scores is
    an error). Both languages must still appear with the same rank and score.
    """
    provider, observations = _observations(tmp_path)

    jobs_rank = rank_metric_id(IeeeProfile.JOBS)
    jobs_score = score_metric_id(IeeeProfile.JOBS)
    tied_ranks = {
        o.language_id: o.rank
        for o in observations
        if o.metric_id == jobs_rank and o.period_start.year == 2024 and o.language_id in {"ada", "haskell"}
    }
    tied_scores = {
        o.language_id: o.value
        for o in observations
        if o.metric_id == jobs_score and o.period_start.year == 2024 and o.language_id in {"ada", "haskell"}
    }
    assert tied_ranks == {"ada": 44, "haskell": 44}
    assert tied_scores == {"ada": 0.0, "haskell": 0.0}

    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.code == "duplicate_rank"]


#: A synthetic curated-CSV row with an empty ``score`` cell, appended in-test only
#: (never written to the verbatim fixture): every bundled row carries a score, so
#: the "missing score" path needs an explicit stand-in. Rust is a mappable label
#: absent from the fixture, so the assertion is unambiguous.
_SYNTHETIC_MISSING_SCORE_ROW = b"2024,spectrum,99,Rust,,https://spectrum.ieee.org/top-programming-languages-2024,2024-08-22,ieee-2024-manual-8metrics\n"


def test_ieee_spectrum_missing_score_yields_rank_but_no_score(tmp_path: Path) -> None:
    """An empty ``score`` cell stores the rank but never fabricates a score.

    Missing data stays missing: a row with no published score must still yield a
    rank observation (the rank is published) yet produce no score observation - a
    fabricated score would invent a measurement that was never published.
    """
    provider = _provider(tmp_path)
    content = (_FIXTURES / "sample.csv").read_bytes() + _SYNTHETIC_MISSING_SCORE_ROW
    observations = provider.normalize(provider.parse(FetchPayload(artifact=None, content=content)))

    rust = [o for o in observations if o.language_id == "rust"]
    assert len(rust) == 1
    (rust_rank,) = rust
    assert rust_rank.metric_id == rank_metric_id(IeeeProfile.SPECTRUM)
    assert rust_rank.rank == 99
    assert rust_rank.is_derived is True
    assert not [o for o in observations if o.language_id == "rust" and o.metric_id.endswith("-score")]
    assert provider.validate(observations).ok


def test_ieee_spectrum_source_document_id_encodes_year_and_profile(tmp_path: Path) -> None:
    """``source_document_id`` ties every row to one edition *and* one profile.

    The id is ``ieee-tpl-{year}-{profile}`` so a query can never conflate the same
    language's ``jobs`` and ``spectrum`` rows from one edition; ``source_published_at``
    keeps each value pinned to the edition it was transcribed from.
    """
    _, observations = _observations(tmp_path)

    for observation in observations:
        profile = str(observation.metadata_json["profile"])
        assert observation.source_document_id == f"ieee-tpl-{observation.period_start.year}-{profile}"

    python_2024_jobs = next(
        o
        for o in observations
        if o.language_id == "python" and o.metric_id == rank_metric_id(IeeeProfile.JOBS) and o.period_start.year == 2024
    )
    assert python_2024_jobs.source_document_id == "ieee-tpl-2024-jobs"
    assert python_2024_jobs.source_published_at is not None
    assert python_2024_jobs.source_published_at.date().isoformat() == "2024-08-22"


def test_ieee_spectrum_hash_stable_across_runs(tmp_path: Path) -> None:
    """``raw_record_hash`` is a deterministic function of the fixture bytes.

    If the hash drifted when nothing about the source changed, ``records_updated``
    would inflate on re-fetch and change detection would stop meaning anything.
    """
    _, first = _observations(tmp_path)
    _, second = _observations(tmp_path)
    first_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in first}
    second_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in second}
    assert first_hashes == second_hashes
    assert all(h for h in first_hashes.values())


def test_ieee_spectrum_validate_full_fixture_ok(tmp_path: Path) -> None:
    """The whole fixture validates with no ERROR-severity issue.

    A single ERROR would block the upsert in ``FetchService``; asserting the report
    is ok guards that the verbatim subset stays a clean, ingestible edition slice.
    """
    provider, observations = _observations(tmp_path)
    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.severity is Severity.ERROR]
