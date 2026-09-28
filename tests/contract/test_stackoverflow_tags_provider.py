from __future__ import annotations

from pathlib import Path

from _golden import assert_matches_golden

from langrank.providers.base import FetchPayload
from langrank.providers.stackoverflow_tags import (
    METRIC_QUESTIONS,
    METRIC_RANK,
    METRIC_SHARE,
    StackOverflowTagsProvider,
)

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "stackoverflow-tags"


def _payload(name: str) -> FetchPayload:
    """Build an artifact-free payload from a fixture file (no network).

    :param name: Fixture filename under ``tests/fixtures/stackoverflow-tags``.
    :returns: A :class:`FetchPayload` wrapping the fixture bytes.
    """
    return FetchPayload(artifact=None, content=(_FIXTURES / name).read_bytes())


def _provider(tmp_path: Path) -> StackOverflowTagsProvider:
    """Construct the provider with an isolated, never-touched cache dir.

    :param tmp_path: pytest-provided temp directory.
    :returns: A fresh provider instance.
    """
    return StackOverflowTagsProvider(tmp_path)


def test_stackoverflow_tags_api_fixture_matches_golden(tmp_path: Path) -> None:
    """The API fixture normalizes to the checked-in golden output, field for field.

    Guards every downstream-visible field (``language_id``, ``metric_id``,
    ``value``, ``unit``, ``is_derived``, ``derivation_method``, ``rank``,
    ``raw_record_hash``) against silent drift.
    """
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(_payload("api_sample.json")))
    assert_matches_golden(observations, _FIXTURES / "expected_observations.json")


def test_stackoverflow_tags_api_share_is_flagged_derived(tmp_path: Path) -> None:
    """Every share and rank is derived and names its denominator; counts are raw.

    Protects the provenance invariant: a reconstruction (share/rank) must never be
    presented as published source data, and the denominator must be recorded so
    ``api`` and ``sede`` series are never conflated.
    """
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(_payload("api_sample.json")))

    counts = [o for o in observations if o.metric_id == METRIC_QUESTIONS]
    shares = [o for o in observations if o.metric_id == METRIC_SHARE]
    ranks = [o for o in observations if o.metric_id == METRIC_RANK]
    assert counts and shares and ranks
    assert all(o.is_derived is False and o.derivation_method is None for o in counts)
    assert all(o.is_derived and o.derivation_method == "question_share:all_questions" for o in shares)
    assert all(o.is_derived and o.derivation_method == "rank_by_question_share:all_questions" for o in ranks)
    assert {o.unit for o in counts} == {"count"}
    assert {o.unit for o in shares} == {"percent"}
    assert {o.unit for o in ranks} == {"rank"}


def test_stackoverflow_tags_api_hash_stable_across_runs(tmp_path: Path) -> None:
    """``raw_record_hash`` is a deterministic function of the source bytes.

    If the hash drifted when nothing about the source changed, change detection
    (``records_updated``) would inflate and stop meaning anything.
    """
    provider = _provider(tmp_path)
    first = provider.normalize(provider.parse(_payload("api_sample.json")))
    second = _provider(tmp_path).normalize(provider.parse(_payload("api_sample.json")))
    first_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in first}
    second_hashes = {(o.metric_id, o.language_id, o.period_label): o.raw_record_hash for o in second}
    assert first_hashes == second_hashes


def test_stackoverflow_tags_sede_multi_tag_share(tmp_path: Path) -> None:
    """SEDE shares may sum above 100 % (multi-tag questions) yet still validate ok.

    Asserts the exact shares and that this is documented behaviour, not an error.
    """
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(_payload("sede_sample.csv")))

    shares = {o.language_id: o.value for o in observations if o.metric_id == METRIC_SHARE}
    assert shares == {"python": 60.0, "javascript": 50.0, "go": 30.0}
    assert sum(shares.values()) > 100.0
    assert all(
        o.derivation_method == "question_share:tracked_language_union"
        for o in observations
        if o.metric_id == METRIC_SHARE
    )

    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.code == "share_range"]


def test_stackoverflow_tags_rename_alias(tmp_path: Path) -> None:
    """A renamed source tag (``golang``) normalizes to canonical ``go``.

    The raw tag must be preserved as ``source_language_name`` while the canonical
    ``language_id`` is ``go``; ``golang`` must never leak through as an id and must
    not be reported unmapped.
    """
    provider = _provider(tmp_path)
    observations = provider.normalize(provider.parse(_payload("sede_sample.csv")))

    go_rows = [o for o in observations if o.language_id == "go"]
    assert go_rows
    assert all(o.source_language_name == "golang" for o in go_rows)
    assert "golang" not in {o.language_id for o in observations}
    assert provider.last_unmapped == []
    assert provider.validate(observations).ok
