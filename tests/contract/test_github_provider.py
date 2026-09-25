from __future__ import annotations

from pathlib import Path

import pytest
from _golden import assert_matches_golden

from langrank.errors import ProviderError
from langrank.models import Observation
from langrank.providers.base import FetchPayload
from langrank.providers.github import (
    METRIC_IG_PUSHERS,
    METRIC_IG_RANK,
    METRIC_IG_SHARE,
    METRIC_OCTOVERSE_RANK,
    GitHubProvider,
    GitHubSource,
)

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "github"

#: The pinned Innovation Graph commit the fixture rows were sampled from (see
#: ``tests/fixtures/github/README.md``). It flows into every source URL,
#: ``source_document_id`` and ``raw_record_hash``, so the golden is only stable
#: when the same SHA is replayed here.
_COMMIT_SHA = "054c7dbc527518fa2ecfd316efe2aa01f3986c39"

#: Every metric id owned by each variant; the two sets must never overlap.
_OCTOVERSE_METRICS = frozenset({METRIC_OCTOVERSE_RANK})
_IG_METRICS = frozenset({METRIC_IG_PUSHERS, METRIC_IG_SHARE, METRIC_IG_RANK})


def _payload(name: str) -> FetchPayload:
    """Build an artifact-free payload from a fixture file (no network).

    :param name: Fixture filename under ``tests/fixtures/github``.
    :returns: A :class:`FetchPayload` wrapping the fixture bytes.
    """
    return FetchPayload(artifact=None, content=(_FIXTURES / name).read_bytes())


def _innovation_graph(tmp_path: Path) -> GitHubProvider:
    """Construct the provider primed to replay the Innovation Graph fixture offline.

    Mirrors the state ``fetch(--offline)`` would stash (selected variant + pinned
    commit SHA) so ``parse`` runs without any network or cache lookup.

    :param tmp_path: pytest-provided temp directory used as the (untouched) cache.
    :returns: A provider ready to parse the Innovation Graph CSV fixture.
    """
    provider = GitHubProvider(tmp_path)
    provider._source = GitHubSource.INNOVATION_GRAPH
    provider._commit_sha = _COMMIT_SHA
    return provider


def _octoverse(tmp_path: Path) -> GitHubProvider:
    """Construct the provider primed to parse the Octoverse fixture (no network).

    :param tmp_path: pytest-provided temp directory used as the (untouched) cache.
    :returns: A provider ready to parse the Octoverse CSV fixture.
    """
    provider = GitHubProvider(tmp_path)
    provider._source = GitHubSource.OCTOVERSE
    return provider


def _ig_observations(tmp_path: Path) -> tuple[GitHubProvider, list[Observation]]:
    """Return the provider and its normalized Innovation Graph observations."""
    provider = _innovation_graph(tmp_path)
    observations = provider.normalize(provider.parse(_payload("innovation_graph_languages.csv")))
    return provider, observations


def test_github_innovation_graph_matches_golden(tmp_path: Path) -> None:
    """The Innovation Graph fixture normalizes to the golden output, field for field.

    Guards every downstream-visible field (``language_id``, ``metric_id``,
    ``value``, ``unit``, ``is_derived``, ``derivation_method``, ``rank``,
    ``source_document_id``, ``raw_record_hash``) of the derived global series
    against silent drift.
    """
    _, observations = _ig_observations(tmp_path)
    assert_matches_golden(observations, _FIXTURES / "expected_innovation_graph.json")


def test_github_octoverse_matches_golden(tmp_path: Path) -> None:
    """The Octoverse fixture normalizes to the golden output, field for field."""
    provider = _octoverse(tmp_path)
    observations = provider.normalize(provider.parse(_payload("octoverse.csv")))
    assert_matches_golden(observations, _FIXTURES / "expected_octoverse.json")


def test_github_variants_write_disjoint_metrics(tmp_path: Path) -> None:
    """Each variant emits only its own metric ids, and the two id sets are disjoint.

    Variant is part of every metric id precisely so a query can never silently mix
    the annual Octoverse ranking with the quarterly Innovation Graph series; if a
    metric leaked across variants the two measures would land on one axis.
    """
    _, ig = _ig_observations(tmp_path)
    octoverse = _octoverse(tmp_path)
    oct_obs = octoverse.normalize(octoverse.parse(_payload("octoverse.csv")))

    ig_metrics = {o.metric_id for o in ig}
    oct_metrics = {o.metric_id for o in oct_obs}
    assert ig_metrics == _IG_METRICS
    assert oct_metrics == _OCTOVERSE_METRICS
    assert ig_metrics.isdisjoint(oct_metrics)


def test_github_innovation_graph_flags_derived_and_records_denominator(tmp_path: Path) -> None:
    """Every Innovation Graph value is derived and names its derivation method.

    Protects the provenance invariant: a reconstruction (global sum / share / rank)
    must never be presented as published source data. The share denominator is
    recorded so the aggregation stays traceable and undercount-aware.
    """
    _, observations = _ig_observations(tmp_path)

    pushers = [o for o in observations if o.metric_id == METRIC_IG_PUSHERS]
    shares = [o for o in observations if o.metric_id == METRIC_IG_SHARE]
    ranks = [o for o in observations if o.metric_id == METRIC_IG_RANK]
    assert pushers and shares and ranks
    assert all(o.is_derived for o in observations)
    assert all(o.derivation_method == "sum_over_economies:suppressed_below_100" for o in pushers)
    assert all(o.derivation_method == "share_of_all_published_language_pushers" for o in shares)
    assert all(o.derivation_method == "rank_by_global_pushers" for o in ranks)
    assert {o.unit for o in pushers} == {"count"}
    assert {o.unit for o in shares} == {"percent"}
    assert {o.unit for o in ranks} == {"rank"}
    assert all(o.population == "global (economies ≥100 developers)" for o in observations)
    # The suppression floor is carried on every aggregate so the undercount is traceable.
    assert all(o.metadata_json.get("suppression_threshold") == 100 for o in pushers)
    assert all(o.metadata_json.get("denominator_count", 0) > 0 for o in shares)


def test_github_innovation_graph_global_pushers_are_sum_over_economies(tmp_path: Path) -> None:
    """The global pusher count is the exact sum of the three fixture economies.

    Asserts the real summed values (US+IN+BR) rather than merely a non-empty
    result, and that the economy count is recorded so the aggregate hash changes
    when the contributing economies change.
    """
    _, observations = _ig_observations(tmp_path)
    q4 = {o.language_id: o for o in observations if o.metric_id == METRIC_IG_PUSHERS and o.period_label == "2025-Q4"}
    # US + IN + BR raw num_pushers for 2025-Q4, summed by the provider.
    assert q4["python"].value == 506798.0 + 556208.0 + 129908.0
    assert q4["javascript"].value == 541307.0 + 833212.0 + 245996.0
    assert q4["c++"].value == 124540.0 + 106637.0 + 27510.0
    assert all(o.metadata_json.get("economies_count") == 3 for o in q4.values())


def test_github_innovation_graph_rank_orders_by_share(tmp_path: Path) -> None:
    """The derived global rank orders mapped languages by descending pusher share.

    In both fixture quarters JavaScript > Python > C++ by pushers, so the ranks
    must be 1/2/3 respectively; a mis-ordered rank would silently rewrite a
    language's history.
    """
    _, observations = _ig_observations(tmp_path)
    for quarter in ("2025-Q4", "2026-Q1"):
        ranks = {
            o.language_id: o.rank for o in observations if o.metric_id == METRIC_IG_RANK and o.period_label == quarter
        }
        assert ranks == {"javascript": 1, "python": 2, "c++": 3}


def test_github_innovation_graph_share_denominator_includes_all_published(tmp_path: Path) -> None:
    """Shares divide by total pushers across *all* published names, mapped or not.

    Unmapped (Solidity) and non-language (HTML, Jupyter Notebook) rows never become
    observations, yet they must remain in the share denominator so shares are
    comparable across quarters and never overstated.
    """
    _, observations = _ig_observations(tmp_path)
    published_2025q4 = (
        (506798 + 556208 + 129908)  # Python
        + (541307 + 833212 + 245996)  # JavaScript
        + (124540 + 106637 + 27510)  # C++
        + (142793 + 180703 + 27940)  # Jupyter Notebook (non-language)
        + (615740 + 992413 + 287881)  # HTML (non-language)
        + (6453 + 11814 + 1240)  # Solidity (unmapped)
    )
    python_share = next(
        o
        for o in observations
        if o.metric_id == METRIC_IG_SHARE and o.language_id == "python" and o.period_label == "2025-Q4"
    )
    expected = round(100.0 * (506798 + 556208 + 129908) / published_2025q4, 4)
    assert python_share.value == expected
    assert python_share.metadata_json["denominator_count"] == float(published_2025q4)
    # A share can never exceed 100 %, and no non-language leaked in as a language id.
    ids = {o.language_id for o in observations}
    assert ids == {"python", "javascript", "c++"}


def test_github_innovation_graph_reports_unmapped_suppresses_non_languages(tmp_path: Path) -> None:
    """Solidity is reported unmapped; HTML / Jupyter Notebook are silently excluded.

    A genuinely unlisted Linguist name must surface as an ``unmapped_language``
    warning (never silently dropped), while documented non-language formats are
    excluded without noise. Either way none of them becomes a language observation.
    """
    provider, observations = _ig_observations(tmp_path)
    assert provider.last_unmapped == ["Solidity"]
    report = provider.validate(observations)
    assert report.ok  # unmapped is a WARNING, not an ERROR
    unmapped_codes = [issue for issue in report.issues if issue.code == "unmapped_language"]
    assert len(unmapped_codes) == 1
    assert "Solidity" in unmapped_codes[0].message
    assert "HTML" not in provider.last_unmapped
    assert "Jupyter Notebook" not in provider.last_unmapped


def test_github_innovation_graph_hash_stable_across_runs(tmp_path: Path) -> None:
    """``raw_record_hash`` is a deterministic function of the fixture bytes and SHA.

    If the hash drifted when nothing about the source changed, ``records_updated``
    would inflate and change detection would stop meaning anything.
    """
    _, first = _ig_observations(tmp_path)
    _, second = _ig_observations(tmp_path)
    first_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in first}
    second_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in second}
    assert first_hashes == second_hashes
    assert all(h for h in first_hashes.values())


def test_github_octoverse_ranks_are_raw_not_derived(tmp_path: Path) -> None:
    """Octoverse ranks are transcribed verbatim: raw, non-derived, traceable.

    The published rank must never be flagged derived, and each rank must carry the
    edition's ``source_document_id`` and ``source_published_at`` so it stays tied to
    the report it came from.
    """
    provider = _octoverse(tmp_path)
    observations = provider.normalize(provider.parse(_payload("octoverse.csv")))

    assert all(o.metric_id == METRIC_OCTOVERSE_RANK for o in observations)
    assert all(o.is_derived is False and o.derivation_method is None for o in observations)
    assert all(o.unit == "rank" for o in observations)
    ranks_2025 = {o.language_id: o.rank for o in observations if o.period_label == "2025"}
    assert ranks_2025 == {"typescript": 1, "python": 2, "javascript": 3}
    typescript = next(o for o in observations if o.language_id == "typescript" and o.period_label == "2025")
    assert typescript.source_document_id and "octoverse" in typescript.source_document_id
    assert typescript.source_published_at is not None
    assert typescript.source_published_at.date().isoformat() == "2025-10-28"
    assert provider.last_unmapped == []


def test_github_normalize_refuses_to_mix_variants(tmp_path: Path) -> None:
    """Feeding both variants' records into ``normalize`` raises, never merges.

    The two variants measure different things; a batch mixing Octoverse rank
    records with Innovation Graph pusher records must be refused rather than
    silently conflated onto one series.
    """
    ig = _innovation_graph(tmp_path)
    ig_records = ig.parse(_payload("innovation_graph_languages.csv"))
    oct_provider = _octoverse(tmp_path)
    oct_records = oct_provider.parse(_payload("octoverse.csv"))

    with pytest.raises(ProviderError, match="cannot mix variants"):
        ig.normalize([*ig_records, *oct_records])
