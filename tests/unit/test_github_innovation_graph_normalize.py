from __future__ import annotations

from pathlib import Path

from langrank.models import Granularity, Observation, SourceRecord
from langrank.providers.common import quarter_period
from langrank.providers.github import (
    IG_POPULATION,
    IG_RANK_METHOD,
    IG_SHARE_METHOD,
    IG_SUM_METHOD,
    IG_SUPPRESSION_THRESHOLD,
    METRIC_IG_PUSHERS,
    METRIC_IG_RANK,
    METRIC_IG_SHARE,
    GitHubProvider,
    GitHubSource,
    _aggregate_global,
)

#: A syntactically valid 40-hex commit SHA the records are pinned to.
VALID_SHA = "0123456789abcdef0123456789abcdef01234567"


def _record(language: str, iso2: str, year: int, quarter: int, pushers: int) -> SourceRecord:
    """Build one per-economy Innovation Graph source record for a language/quarter."""
    period_start, period_end, period_label = quarter_period(year, quarter)
    return SourceRecord(
        rating_id="github",
        metric_id=METRIC_IG_PUSHERS,
        language=language,
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        granularity=Granularity.QUARTER,
        rank=None,
        value=float(pushers),
        unit="count",
        source_url="https://raw.githubusercontent.com/github/innovationgraph/x/data/languages.csv",
        metadata={"iso2_code": iso2, "commit_sha": VALID_SHA, "variant": GitHubSource.INNOVATION_GRAPH.value},
    )


def _by_metric(observations: list[Observation], metric_id: str) -> list[Observation]:
    return [item for item in observations if item.metric_id == metric_id]


def test_ig_global_sum_is_derived(tmp_path: Path) -> None:
    provider = GitHubProvider(tmp_path)
    records = [
        _record("Python", "US", 2024, 1, 1200),
        _record("Python", "GB", 2024, 1, 800),
    ]

    observations = provider.normalize(records)

    pushers = _by_metric(observations, METRIC_IG_PUSHERS)
    assert len(pushers) == 1
    obs = pushers[0]
    assert obs.language_id == "python"
    assert obs.value == 2000.0  # 1200 + 800 summed over economies
    assert obs.is_derived is True
    assert obs.derivation_method == IG_SUM_METHOD
    assert obs.population == IG_POPULATION
    assert obs.metadata_json["economies_count"] == 2
    assert obs.metadata_json["suppression_threshold"] == IG_SUPPRESSION_THRESHOLD
    assert obs.source_document_id == f"innovationgraph@{VALID_SHA[:12]}"


def test_ig_share_denominator_includes_unmapped(tmp_path: Path) -> None:
    provider = GitHubProvider(tmp_path)
    records = [
        _record("Python", "US", 2024, 1, 1000),
        _record("MadeUpLang", "US", 2024, 1, 500),  # unmapped, still in denominator
        _record("HTML", "US", 2024, 1, 500),  # non-language, still in denominator
    ]

    observations = provider.normalize(records)

    shares = _by_metric(observations, METRIC_IG_SHARE)
    # Only the mapped language yields a share observation...
    assert len(shares) == 1
    share = shares[0]
    assert share.language_id == "python"
    # ...but the denominator sums every published language: 1000 + 500 + 500 = 2000.
    assert share.value == 50.0  # 100 * 1000 / 2000
    assert share.derivation_method == IG_SHARE_METHOD
    assert share.is_derived is True
    assert share.metadata_json["denominator_count"] == 2000.0
    # The genuinely unknown name is reported; the documented non-language is suppressed.
    assert provider.last_unmapped == ["MadeUpLang"]


def test_ig_rank_ties(tmp_path: Path) -> None:
    provider = GitHubProvider(tmp_path)
    records = [
        _record("Python", "US", 2024, 1, 1000),
        _record("Rust", "US", 2024, 1, 1000),
        _record("Go", "US", 2024, 1, 500),
    ]

    observations = provider.normalize(records)

    ranks = {obs.language_id: obs for obs in _by_metric(observations, METRIC_IG_RANK)}
    # Equal shares tie at rank 1; the next distinct share skips to rank 3.
    assert ranks["python"].rank == 1
    assert ranks["rust"].rank == 1
    assert ranks["go"].rank == 3
    for obs in ranks.values():
        assert obs.value == float(obs.rank)
        assert obs.is_derived is True
        assert obs.derivation_method == IG_RANK_METHOD
        assert obs.population == IG_POPULATION


def test_ig_rank_hash_reflects_rank_not_share(tmp_path: Path) -> None:
    # A rank-only change must alter raw_record_hash, so the rank hash is distinct
    # from its share hash (Task 01.0 review caveat).
    provider = GitHubProvider(tmp_path)
    records = [
        _record("Python", "US", 2024, 1, 1000),
        _record("Rust", "US", 2024, 1, 500),
    ]

    observations = provider.normalize(records)

    share = next(o for o in _by_metric(observations, METRIC_IG_SHARE) if o.language_id == "python")
    rank = next(o for o in _by_metric(observations, METRIC_IG_RANK) if o.language_id == "python")
    assert rank.raw_record_hash != share.raw_record_hash


def test_ig_hash_changes_with_economy_count(tmp_path: Path) -> None:
    provider = GitHubProvider(tmp_path)
    single = provider.normalize([_record("Python", "US", 2024, 1, 1200)])
    # Same 1200 total, but split across two economies.
    split = provider.normalize(
        [
            _record("Python", "US", 2024, 1, 600),
            _record("Python", "GB", 2024, 1, 600),
        ]
    )

    single_obs = _by_metric(single, METRIC_IG_PUSHERS)[0]
    split_obs = _by_metric(split, METRIC_IG_PUSHERS)[0]
    assert single_obs.value == split_obs.value == 1200.0
    assert single_obs.metadata_json["economies_count"] == 1
    assert split_obs.metadata_json["economies_count"] == 2
    # Identical totals but different inputs must not collide on the change-detection hash.
    assert single_obs.raw_record_hash != split_obs.raw_record_hash


def test_ig_normalize_empty_returns_empty(tmp_path: Path) -> None:
    provider = GitHubProvider(tmp_path)

    assert provider.normalize([]) == []


def test_aggregate_global_sums_per_quarter_and_language(tmp_path: Path) -> None:
    records = [
        _record("Python", "US", 2024, 1, 1000),
        _record("Python", "GB", 2024, 1, 200),
        _record("Python", "US", 2024, 2, 300),
    ]

    aggregated = _aggregate_global(records)

    # One aggregate per (quarter, language); Q1 sums two economies, Q2 stands alone.
    by_label = {rec.period_label: rec for rec in aggregated}
    assert by_label["2024-Q1"].value == 1200.0
    assert by_label["2024-Q1"].metadata["economies_count"] == 2
    assert by_label["2024-Q2"].value == 300.0
    assert by_label["2024-Q2"].metadata["economies_count"] == 1
    assert all("iso2_code" not in rec.metadata for rec in aggregated)
