from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional

import pytest

from langrank.errors import NormalizationError, ParseError
from langrank.models import Observation, RawArtifact
from langrank.providers.base import FetchPayload
from langrank.providers.stackoverflow_tags import (
    METRIC_QUESTIONS,
    METRIC_RANK,
    METRIC_SHARE,
    StackOverflowTagsProvider,
    _to_epoch,
)


def _provider(tmp_path: Path) -> StackOverflowTagsProvider:
    return StackOverflowTagsProvider(tmp_path)


def _api_payload(months: list[dict[str, object]], *, artifact: Optional[RawArtifact] = None) -> FetchPayload:
    document = {"source": "api", "denominator": "all_questions", "months": months}
    return FetchPayload(artifact=artifact, content=json.dumps(document).encode("utf-8"))


def _sede_payload(rows: str) -> FetchPayload:
    header = "month,tag,questions,union_total\n"
    return FetchPayload(artifact=None, content=(header + rows).encode("utf-8"))


def _by_metric(observations: list[Observation], metric_id: str) -> list[Observation]:
    return [obs for obs in observations if obs.metric_id == metric_id]


def test_share_is_derived_with_denominator_method(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    payload = _api_payload([{"month": "2024-01", "total": 1000, "tags": {"python": 250}}])

    observations = provider.normalize(provider.parse(payload))

    (share,) = _by_metric(observations, METRIC_SHARE)
    assert share.is_derived is True
    assert share.derivation_method == "question_share:all_questions"
    assert share.value == pytest.approx(25.0)
    assert share.unit == "percent"
    assert share.source_document_id == "api:2024-01"
    assert share.parser_version == "stackoverflow-tags-v1"
    assert share.raw_record_hash

    (questions,) = _by_metric(observations, METRIC_QUESTIONS)
    assert questions.is_derived is False
    assert questions.derivation_method is None
    assert questions.value == pytest.approx(250.0)


def test_zero_denominator_emits_no_share(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    payload = _api_payload([{"month": "2024-01", "total": 0, "tags": {"python": 5}}])

    observations = provider.normalize(provider.parse(payload))

    assert _by_metric(observations, METRIC_SHARE) == []
    assert _by_metric(observations, METRIC_RANK) == []
    (questions,) = _by_metric(observations, METRIC_QUESTIONS)
    assert questions.value == pytest.approx(5.0)


def test_rank_ties_share_rank(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    # python and java tie on 300/1000; go trails on 100/1000.
    payload = _api_payload([{"month": "2024-01", "total": 1000, "tags": {"python": 300, "java": 300, "go": 100}}])

    observations = provider.normalize(provider.parse(payload))

    ranks = {obs.language_id: obs.rank for obs in _by_metric(observations, METRIC_RANK)}
    assert ranks["python"] == 1
    assert ranks["java"] == 1
    # The tie skips rank 2; the next distinct share lands on rank 3.
    assert ranks["go"] == 3
    rank_obs = _by_metric(observations, METRIC_RANK)[0]
    assert rank_obs.is_derived is True
    assert rank_obs.derivation_method == "rank_by_question_share:all_questions"
    assert rank_obs.value == pytest.approx(float(rank_obs.rank))


def test_period_end_is_last_day_of_month(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    payload = _api_payload([{"month": "2024-02", "total": 1000, "tags": {"python": 10}}])

    observations = provider.normalize(provider.parse(payload))

    for obs in observations:
        assert obs.period_start == date(2024, 2, 1)
        assert obs.period_end == date(2024, 2, 29)  # 2024 is a leap year


def test_sede_duplicate_language_month_raises(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    # "cpp" and "c++" both resolve to the canonical c++ in the same month.
    payload = _sede_payload("2024-01,cpp,100,1000\n2024-01,c++,50,1000\n")

    with pytest.raises(NormalizationError) as excinfo:
        provider.normalize(provider.parse(payload))

    assert "double count" in str(excinfo.value)


def test_unmapped_tag_is_skipped_and_recorded(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    payload = _api_payload([{"month": "2024-01", "total": 1000, "tags": {"python": 200, "brainfuck": 3}}])

    observations = provider.normalize(provider.parse(payload))

    languages = {obs.language_id for obs in observations}
    assert "python" in languages
    assert "brainfuck" not in languages
    # Recorded once despite appearing in both the questions and share records.
    assert provider.last_unmapped == ["brainfuck"]


def test_shares_may_exceed_100_in_total(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    # Multi-tag questions: three languages each take 60% of the union - sums to 180%.
    payload = _sede_payload("2024-01,python,600,1000\n2024-01,java,600,1000\n2024-01,go,600,1000\n")

    observations = provider.normalize(provider.parse(payload))

    total_share = sum(obs.value or 0.0 for obs in _by_metric(observations, METRIC_SHARE))
    assert total_share > 100.0  # documented, not a validation error


def test_retrieved_at_taken_from_artifact_when_present(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    retrieved = datetime(2020, 5, 1, 12, 0, tzinfo=UTC)
    artifact = RawArtifact(
        id="a1",
        rating_id="stackoverflow-tags",
        url="https://api.stackexchange.com/2.3/questions",
        retrieved_at=retrieved,
        sha256="0" * 64,
        mime_type="application/json",
        local_path=str(tmp_path / "cached.json"),
    )
    payload = _api_payload([{"month": "2024-01", "total": 1000, "tags": {"python": 10}}], artifact=artifact)

    observations = provider.normalize(provider.parse(payload))

    assert all(obs.retrieved_at == retrieved for obs in observations)


def test_sede_source_document_id_hashes_content(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    payload = _sede_payload("2024-01,python,100,1000\n")

    observations = provider.normalize(provider.parse(payload))

    doc_ids = {obs.source_document_id for obs in observations}
    assert len(doc_ids) == 1
    (doc_id,) = doc_ids
    assert doc_id is not None and doc_id.startswith("sede:")


def test_sede_non_utf8_raises_parse_error(tmp_path: Path) -> None:
    payload = FetchPayload(
        artifact=None, content="month,tag,questions,union_total\n2024-01,caf\u00e9,1,1\n".encode("latin-1")
    )
    with pytest.raises(ParseError, match="UTF-8"):
        _provider(tmp_path).parse(payload)


def test_sede_utf8_bom_is_accepted(tmp_path: Path) -> None:
    payload = FetchPayload(artifact=None, content=b"\xef\xbb\xbfmonth,tag,questions,union_total\n2024-01,python,5,10\n")
    records = _provider(tmp_path).parse(payload)
    assert records


def test_to_epoch_day_bounds() -> None:
    day = date(2024, 2, 29)
    start = _to_epoch(day, end_of_day=False)
    end = _to_epoch(day, end_of_day=True)
    assert start == int(datetime(2024, 2, 29, tzinfo=UTC).timestamp())
    assert end - start == 86_399
