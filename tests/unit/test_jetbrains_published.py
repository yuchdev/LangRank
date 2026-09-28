from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from langrank.errors import ParseError
from langrank.models import FetchRequest, Granularity
from langrank.providers.base import FetchPayload
from langrank.providers.jetbrains import (
    DATA_PATH,
    PUBLISHED_METRICS,
    JetBrainsProvider,
)
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
)

_HEADER = "year,metric,language,percent,sample_size,population,source_url,published_at"
_URL = "https://www.jetbrains.com/lp/devecosystem-2024/"
_POP = "developers worldwide (weighted)"

#: A minimal well-formed curated CSV: one verified-wording row (2024 used), one
#: unverified-wording row (2020 used), one non-language meta-answer (``Other``) and
#: one non-general-purpose label (``GraphQL``), so a single fixture exercises both
#: the wording metadata and the skip path.
_CSV = (
    f"{_HEADER}\n"
    f"2024,{METRIC_USED_LAST_12_MONTHS},Python,57,23262,{_POP},{_URL},\n"
    f"2020,{METRIC_USED_LAST_12_MONTHS},Kotlin,9,19696,{_POP},{_URL},\n"
    f"2024,{METRIC_PRIMARY_LANGUAGE},Other,3,23262,{_POP},{_URL},\n"
    f"2024,{METRIC_PLANNED_ADOPTION},GraphQL,4,23262,{_POP},{_URL},\n"
).encode("utf-8")


def _provider(tmp_path: Path) -> JetBrainsProvider:
    """Build a provider rooted at a throwaway cache dir (no network, no database)."""
    return JetBrainsProvider(tmp_path)


def _payload(content: bytes) -> FetchPayload:
    """Wrap raw CSV bytes as an artifact-less payload."""
    return FetchPayload(artifact=None, content=content)


def test_jetbrains_published_parse(tmp_path: Path) -> None:
    """Each row yields one percentage record carrying registry wording metadata."""
    provider = _provider(tmp_path)

    records = provider.parse(_payload(_CSV))

    assert len(records) == 4
    # Percentages only - no rank metric and no rank value.
    assert all(record.rank is None and record.unit == "percent" for record in records)
    assert all(record.granularity is Granularity.YEAR for record in records)

    used_2024 = next(r for r in records if r.period_label == "2024" and r.metric_id == METRIC_USED_LAST_12_MONTHS)
    assert used_2024.value == 57.0
    assert used_2024.metadata["question_wording"] == "Which programming languages have you used in the last 12 months?"
    assert used_2024.metadata["wording_verified"] is True

    # 2020 used has no confirmed verbatim wording: it is None, never invented.
    used_2020 = next(r for r in records if r.period_label == "2020")
    assert used_2020.metadata["question_wording"] is None
    assert used_2020.metadata["wording_verified"] is False


def test_jetbrains_published_normalize_percent_raw(tmp_path: Path) -> None:
    """Published values are raw weighted percentages: is_derived False, no rank."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    # Two of the four rows are non-language answers (Other, GraphQL) and are skipped.
    assert len(observations) == 2
    assert all(not o.is_derived and o.derivation_method is None for o in observations)
    assert all(o.unit == "percent" and o.rank is None for o in observations)
    python = next(o for o in observations if o.language_id == "python")
    assert python.value == 57.0
    assert python.metric_id == METRIC_USED_LAST_12_MONTHS
    assert python.source_document_id == "jetbrains-devecosystem-2024"
    assert python.metadata_json["wording_verified"] is True


def test_jetbrains_published_sample_size_population(tmp_path: Path) -> None:
    """Every observation carries the row's sample_size and population verbatim."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    python = next(o for o in observations if o.language_id == "python")
    assert python.sample_size == 23262
    assert python.population == _POP
    # JetBrains prints no publication date, so it stays None (never fabricated).
    assert python.source_published_at is None


def test_jetbrains_published_unasked_question_raises(tmp_path: Path) -> None:
    """A row for a (year, metric) the registry says was not asked raises ParseError."""
    provider = _provider(tmp_path)
    # 2018 primary-language percentages were never published (rank podium only).
    csv_bytes = (f"{_HEADER}\n2018,{METRIC_PRIMARY_LANGUAGE},Java,43,6000,{_POP},{_URL},\n").encode("utf-8")

    with pytest.raises(ParseError, match="not asked"):
        provider.parse(_payload(csv_bytes))


def test_jetbrains_unknown_metric_raises(tmp_path: Path) -> None:
    """An unknown metric id is rejected rather than dropped or guessed."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2024,jetbrains-mystery,Python,10,23262,{_POP},{_URL},\n").encode("utf-8")

    with pytest.raises(ParseError, match="unknown metric"):
        provider.parse(_payload(csv_bytes))


def test_jetbrains_bad_percent_raises(tmp_path: Path) -> None:
    """A percent outside 0..100 is malformed and rejected; 0 is a valid kept value."""
    provider = _provider(tmp_path)
    over = (f"{_HEADER}\n2024,{METRIC_USED_LAST_12_MONTHS},Python,101,23262,{_POP},{_URL},\n").encode("utf-8")
    with pytest.raises(ParseError, match="percent"):
        provider.parse(_payload(over))

    zero = (f"{_HEADER}\n2024,{METRIC_PRIMARY_LANGUAGE},Lua,0,23262,{_POP},{_URL},\n").encode("utf-8")
    records = provider.parse(_payload(zero))
    assert records[0].value == 0.0


def test_jetbrains_non_positive_sample_size_raises(tmp_path: Path) -> None:
    """A non-positive sample_size corrupts provenance and is rejected."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2024,{METRIC_USED_LAST_12_MONTHS},Python,57,0,{_POP},{_URL},\n").encode("utf-8")

    with pytest.raises(ParseError, match="sample_size"):
        provider.parse(_payload(csv_bytes))


def test_jetbrains_missing_column_raises(tmp_path: Path) -> None:
    """A header that drops a required column raises ParseError (import guard)."""
    provider = _provider(tmp_path)
    csv_bytes = (
        "year,metric,language,percent,sample_size,source_url,published_at\n"
        f"2024,{METRIC_USED_LAST_12_MONTHS},Python,57,23262,{_URL},\n"
    ).encode("utf-8")

    with pytest.raises(ParseError, match="population"):
        provider.parse(_payload(csv_bytes))


def test_jetbrains_non_utf8_raises_and_bom_tolerated(tmp_path: Path) -> None:
    """Non-UTF-8 bytes raise ParseError; a UTF-8 BOM is tolerated."""
    provider = _provider(tmp_path)
    latin1 = f"{_HEADER}\n2024,{METRIC_USED_LAST_12_MONTHS},Naïve,5,23262,{_POP},{_URL},\n".encode("latin-1")
    with pytest.raises(ParseError):
        provider.parse(_payload(latin1))

    bom = b"\xef\xbb\xbf" + _CSV
    assert provider.parse(_payload(bom))  # BOM tolerated, rows parse.


def test_jetbrains_non_language_answers_skipped_silently(tmp_path: Path) -> None:
    """Meta-answers and non-general-purpose labels are skipped without warning."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    languages = {o.language_id for o in observations}
    assert "vb.net" not in languages  # classic Visual Basic never folds in
    assert all(o.source_language_name not in {"Other", "GraphQL"} for o in observations)
    assert provider.last_unmapped == []


def test_jetbrains_unmapped_label_recorded(tmp_path: Path) -> None:
    """A label that resolves to nothing is skipped and recorded, never guessed."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2024,{METRIC_USED_LAST_12_MONTHS},Nonesuchlang,3,23262,{_POP},{_URL},\n").encode("utf-8")

    observations = provider.normalize(provider.parse(_payload(csv_bytes)))

    assert observations == []
    assert provider.last_unmapped == ["Nonesuchlang"]


def test_jetbrains_bundled_dataset_round_trip(tmp_path: Path) -> None:
    """The whole bundled dataset runs fetch->parse->normalize with no unmapped label."""
    provider = _provider(tmp_path)
    payload = provider.fetch(FetchRequest())

    records = provider.parse(payload)
    observations = provider.normalize(records)

    assert payload.content == DATA_PATH.read_bytes()
    assert len(records) == 723
    assert provider.last_unmapped == []
    # Only the three published percentage metrics appear; no rank, all raw.
    assert set(PUBLISHED_METRICS) == {o.metric_id for o in observations}
    assert all(not o.is_derived and o.rank is None and o.unit == "percent" for o in observations)
    per_metric = Counter(o.metric_id for o in observations)
    assert per_metric == {
        METRIC_PLANNED_ADOPTION: 250,
        METRIC_USED_LAST_12_MONTHS: 238,
        METRIC_PRIMARY_LANGUAGE: 155,
    }
    # A multi-year used-in-12-months history spans every survey edition.
    used_years = {o.period_start.year for o in observations if o.metric_id == METRIC_USED_LAST_12_MONTHS}
    assert used_years == set(range(2017, 2026))
