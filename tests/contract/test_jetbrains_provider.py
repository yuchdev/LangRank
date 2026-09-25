"""Contract tests for the JetBrains provider (fixture-driven, no network).

Two fixtures drive the real ``parse`` / ``import_path`` -> ``normalize`` pipeline
with no network and (for the golden tests) no database:

- ``tests/fixtures/jetbrains/published_sample.csv`` - a **verbatim** subset of the
  bundled ``src/langrank/providers/data/jetbrains.csv`` (3 survey years spanning a
  wording change - 2017, 2019, 2024 - x all three metrics x a fixed label set that
  includes the ``HTML / CSS`` non-language answer and the drifting shell-scripting
  label). Values are JetBrains' published weighted percentages: ``is_derived=False``.
- ``tests/fixtures/jetbrains/raw_sample.csv`` - a tiny **synthetic** wide CSV in the
  verified 2024 raw layout (``proglang::`` / ``primary_lang::`` / ``adopt_proglang::``
  per-option columns), carrying a free-text column that must never surface and an
  all-blank respondent that must fall out of every denominator. LangRank's unweighted
  respondent shares: ``is_derived=True``. No real JetBrains response row is committed
  (JB-SEC-5; the 2024 edition is CC BY-NC-SA 4.0).

Every assertion targets a downstream-visible field so a silently mis-normalized value
fails loudly: the published and ``-raw`` families never share a metric id and carry the
opposite ``is_derived`` flag; ``primary_language`` and ``used_last_12_months`` stay
distinct series; the registry ``question_wording`` / ``wording_verified`` metadata is
exact; the ``HTML / CSS`` non-language answer yields no observation; and the raw
free-text never reaches any record, value or metadata field.

See ``tests/fixtures/jetbrains/SOURCE.md`` for both selection rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _golden import assert_matches_golden

from langrank.db import Database
from langrank.models import FetchRequest, Observation, QueryFilters, Severity
from langrank.providers.base import FetchPayload
from langrank.providers.jetbrains import (
    PARSER_VERSION,
    PUBLISHED_METRICS,
    RAW_DERIVATION_METHOD,
    RAW_METRICS,
    JetBrainsProvider,
    raw_metric_id,
)
from langrank.providers.jetbrains_questions import (
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
)
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "jetbrains"

#: The JetBrains meta-answer present in the published fixture that must never map to a
#: canonical language (documented ``JETBRAINS_NON_LANGUAGE_ANSWERS`` markup label).
_NON_LANGUAGE_LABEL = "HTML / CSS"

#: The PII / injection-shaped free-text seeded into the raw fixture's ``comment_freetext``
#: column. JB-SEC-4/JB-SEC-9: it must never reach a record, an observation, or metadata.
_RAW_FREE_TEXT_NEEDLE = "alice.secret@example.com"


def _provider(tmp_path: Path) -> JetBrainsProvider:
    """Construct the provider with an isolated cache dir (never touched offline)."""
    return JetBrainsProvider(tmp_path / "cache")


def _published(tmp_path: Path) -> tuple[JetBrainsProvider, list[Observation]]:
    """Return the provider and normalized observations for the published fixture."""
    provider = _provider(tmp_path)
    payload = FetchPayload(artifact=None, content=(_FIXTURES / "published_sample.csv").read_bytes())
    return provider, provider.normalize(provider.parse(payload))


def _raw(tmp_path: Path) -> tuple[JetBrainsProvider, list[Observation]]:
    """Return the provider and normalized observations for the synthetic raw fixture."""
    provider = _provider(tmp_path)
    records = provider.import_path(_FIXTURES / "raw_sample.csv")
    return provider, provider.normalize(records)


def test_jetbrains_published_matches_golden(tmp_path: Path) -> None:
    """The published fixture normalizes to the golden output, field for field.

    Guards every downstream-visible field (``language_id``, ``metric_id``, ``value``,
    ``unit``, ``is_derived``, ``sample_size``, ``source_document_id`` and the
    ``question_wording`` / ``wording_verified`` metadata) against silent drift; a
    changed golden means a changed observation.
    """
    _, observations = _published(tmp_path)
    assert_matches_golden(observations, _FIXTURES / "expected_published.json")


def test_jetbrains_raw_matches_golden(tmp_path: Path) -> None:
    """The synthetic raw fixture normalizes to the golden output, field for field.

    The golden pins the derived unweighted shares (``is_derived=True``,
    ``derivation_method``), the per-metric denominator stored as ``sample_size``, and
    the ``-raw`` metric ids, so a wrong denominator or a leaked series fails loudly.
    """
    _, observations = _raw(tmp_path)
    assert_matches_golden(observations, _FIXTURES / "expected_raw.json")


def test_jetbrains_published_and_raw_families_are_disjoint_and_opposite_derived(tmp_path: Path) -> None:
    """Published and ``-raw`` observations never share a metric id and invert ``is_derived``.

    JetBrains' published percentages are weighted raw source data (``is_derived=False``,
    ``derivation_method=None``); the ``-raw`` shares are LangRank-derived unweighted
    figures (``is_derived=True``, named derivation method). If a metric id leaked across
    the two families, a weighted and an unweighted value would silently share one series.
    """
    _, published = _published(tmp_path)
    _, raw = _raw(tmp_path)

    published_metrics = {o.metric_id for o in published}
    raw_metrics = {o.metric_id for o in raw}
    assert published_metrics <= set(PUBLISHED_METRICS)
    assert raw_metrics <= set(RAW_METRICS)
    assert published_metrics.isdisjoint(raw_metrics)
    assert set(PUBLISHED_METRICS).isdisjoint(RAW_METRICS)

    assert all(o.is_derived is False and o.derivation_method is None for o in published)
    assert all(o.unit == "percent" for o in published)
    assert all(o.is_derived is True and o.derivation_method == RAW_DERIVATION_METHOD for o in raw)
    assert all(o.unit == "percent" for o in raw)
    assert all(o.parser_version == PARSER_VERSION for o in [*published, *raw])
    # Every raw metric is exactly its published counterpart plus the -raw suffix.
    assert {raw_metric_id(m) for m in published_metrics} == raw_metrics


def test_jetbrains_published_carries_registry_wording_and_verified_flag(tmp_path: Path) -> None:
    """Each published observation carries the registry wording and verified flag exactly.

    Wording is never invented: 2017 used-last-12-months has only a chart legend, so its
    ``question_wording`` is ``None`` with ``wording_verified=False`` (the key is still
    present), while 2019 and 2024 carry JetBrains' confirmed verbatim strings with
    ``wording_verified=True``. A wrong flag would let a paraphrase pass as source wording.
    """
    _, observations = _published(tmp_path)

    def one(metric_id: str, language_id: str, year: int) -> Observation:
        return next(
            o
            for o in observations
            if o.metric_id == metric_id and o.language_id == language_id and o.period_start.year == year
        )

    used = METRIC_USED_LAST_12_MONTHS
    py_2017 = one(used, "python", 2017)
    assert "question_wording" in py_2017.metadata_json
    assert py_2017.metadata_json["question_wording"] is None
    assert py_2017.metadata_json["wording_verified"] is False

    py_2019 = one(used, "python", 2019)
    assert (
        py_2019.metadata_json["question_wording"] == "What programming languages have you used in the last 12 months?"
    )
    assert py_2019.metadata_json["wording_verified"] is True

    py_2024 = one(used, "python", 2024)
    assert (
        py_2024.metadata_json["question_wording"] == "Which programming languages have you used in the last 12 months?"
    )
    assert py_2024.metadata_json["wording_verified"] is True

    # Every observation carries the wording key (value may be None) - a hard invariant
    # the validator upgrades to an ERROR when missing.
    assert all("question_wording" in o.metadata_json for o in observations)
    assert all("wording_verified" in o.metadata_json for o in observations)


def test_jetbrains_non_language_answer_yields_no_observation(tmp_path: Path) -> None:
    """``HTML / CSS`` maps to nothing in every year/metric and raises no unmapped warning.

    The label is present in the published fixture for all three metrics across 2017,
    2019 and 2024, yet it is a documented ``JETBRAINS_NON_LANGUAGE_ANSWERS`` markup
    answer: it must become no observation, never enter ``last_unmapped``, and never
    trigger an ``unmapped_language`` warning - it is a known non-language, not a mapping
    failure.
    """
    provider, observations = _published(tmp_path)

    assert _NON_LANGUAGE_LABEL not in {o.source_language_name for o in observations}
    # Only mappable labels survive; the drifting shell grouping proves the alias worked.
    assert {o.language_id for o in observations} == {"python", "java", "c++", "sql", "shell"}
    assert provider.last_unmapped == []

    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.code == "unmapped_language"]


def test_jetbrains_raw_non_language_answers_count_denominator_but_yield_no_observation(tmp_path: Path) -> None:
    """Raw meta-answers count toward the denominator yet produce no observation.

    ``Other`` and ``I don't use programming languages`` are answers to the used-languages
    question (so the two respondents that picked only them are in the denominator of 16),
    but neither is a language, so neither becomes an observation - the share denominator
    stays honest without fabricating a language row.
    """
    _, observations = _raw(tmp_path)

    used_raw = raw_metric_id(METRIC_USED_LAST_12_MONTHS)
    used = [o for o in observations if o.metric_id == used_raw]
    assert {o.language_id for o in used} == {"python", "java", "c++", "kotlin"}
    # The two meta-answer respondents (R15, R16) are inside the denominator of 16.
    assert {o.sample_size for o in used} == {16}
    # No language row was fabricated for the meta-answers.
    assert not [o for o in observations if o.language_id in {"other", "i don't use programming languages"}]


def test_jetbrains_raw_never_stores_free_text(tmp_path: Path) -> None:
    """The raw free-text column is never read into any record, value, or metadata.

    JB-SEC-4: only the language-question columns are aggregated, so the seeded PII /
    injection-shaped free-text must appear in no ``source_language_name``, no value, and
    no serialized ``metadata_json`` - a leak would persist a respondent's private text.
    """
    provider = _provider(tmp_path)
    records = provider.import_path(_FIXTURES / "raw_sample.csv")
    observations = provider.normalize(records)

    assert observations
    assert all(_RAW_FREE_TEXT_NEEDLE not in record.language for record in records)
    assert all(_RAW_FREE_TEXT_NEEDLE not in str(record.metadata) for record in records)
    assert all(_RAW_FREE_TEXT_NEEDLE not in o.source_language_name for o in observations)
    assert all(_RAW_FREE_TEXT_NEEDLE not in str(o.metadata_json) for o in observations)


def test_jetbrains_used_last_12_months_multi_year_history_validates(tmp_path: Path) -> None:
    """The fixture holds a validated used-last-12-months history spanning three years.

    The task requires at least a three-year ``used_last_12_months`` history; the
    published fixture carries 2017, 2019 and 2024. Validation stays ok (the verified
    wording change is a WARNING, never an ERROR) so the slice is ingestible.
    """
    provider, observations = _published(tmp_path)

    used = [o for o in observations if o.metric_id == METRIC_USED_LAST_12_MONTHS]
    years = {o.period_start.year for o in used}
    assert years == {2017, 2019, 2024}
    python_years = {o.period_start.year for o in used if o.language_id == "python"}
    assert python_years == {2017, 2019, 2024}

    report = provider.validate(observations)
    assert report.ok
    assert not [issue for issue in report.issues if issue.severity is Severity.ERROR]


def test_jetbrains_hash_stable_across_runs(tmp_path: Path) -> None:
    """``raw_record_hash`` is a deterministic function of each fixture's bytes.

    A drifting hash when nothing about the source changed would inflate
    ``records_updated`` on re-fetch and hollow out change detection.
    """
    _, first = _published(tmp_path)
    _, second = _published(tmp_path)
    key = lambda o: (o.metric_id, o.language_id, o.period_label)  # noqa: E731
    first_hashes = {key(o): o.raw_record_hash for o in first}
    second_hashes = {key(o): o.raw_record_hash for o in second}
    assert first_hashes == second_hashes
    assert all(h for h in first_hashes.values())


@pytest.mark.integration
def test_jetbrains_primary_and_used_are_distinct_metrics(tmp_path: Path) -> None:
    """A query for one question's metric never returns the other's rows (plan criterion).

    Seeds the published fixture through the real ``Database`` natural-key upsert, then
    queries ``used_last_12_months`` and ``primary_language`` separately. Python is in
    both, but the two are distinct series (57 used vs 35 primary in 2024), so filtering
    one must never leak a row of the other - the two questions are never merged.
    """
    database = Database(tmp_path / "langrank.sqlite")
    provider = _provider(tmp_path)
    _, observations = _published(tmp_path)
    database.upsert_provider_metadata(provider.metadata())
    fetch_run_id = database.create_fetch_run(provider.provider_id)
    report = provider.validate(observations)
    assert report.ok, [i.message for i in report.issues]
    database.upsert_observations(observations, fetch_run_id)
    service = QueryService(database)

    used = service.query(QueryFilters(rating_id="jetbrains", metric_id=METRIC_USED_LAST_12_MONTHS, year=2024))
    primary = service.query(QueryFilters(rating_id="jetbrains", metric_id=METRIC_PRIMARY_LANGUAGE, year=2024))
    assert used
    assert primary
    assert {row.metric_id for row in used} == {METRIC_USED_LAST_12_MONTHS}
    assert {row.metric_id for row in primary} == {METRIC_PRIMARY_LANGUAGE}
    used_python = next(row for row in used if row.language_id == "python")
    primary_python = next(row for row in primary if row.language_id == "python")
    assert used_python.value == 57.0
    assert primary_python.value == 35.0

    # A metric id belonging to neither question (the -raw counterpart, never published)
    # must match nothing rather than borrow the published rows.
    absent = service.query(
        QueryFilters(rating_id="jetbrains", metric_id=raw_metric_id(METRIC_USED_LAST_12_MONTHS), year=2024)
    )
    assert absent == []


@pytest.mark.integration
def test_jetbrains_published_fetch_db_query_full_history_round_trips(tmp_path: Path) -> None:
    """The bundled dataset fetches offline and yields a 2017-2025 used history per query.

    Drives the full ``FetchService`` -> ``Database`` -> ``QueryService`` pipeline on the
    committed bundled CSV (0 network requests). Python's used-last-12-months series must
    span every survey year 2017-2025, satisfying the task's multi-year-history criterion
    on the real dataset, and a query for an un-published ``-raw`` metric must be empty.
    """
    database = Database(tmp_path / "langrank.sqlite")
    summary = FetchService(database).fetch(_provider(tmp_path), FetchRequest(years=20))
    assert summary.validation_report.ok
    assert summary.records_inserted > 0

    service = QueryService(database)
    used = service.query(
        QueryFilters(rating_id="jetbrains", metric_id=METRIC_USED_LAST_12_MONTHS, language_ids=["python"])
    )
    assert {row.metric_id for row in used} == {METRIC_USED_LAST_12_MONTHS}
    assert {int(row.period_label) for row in used} == {2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025}

    # The raw family is import-only; the bundled published fetch stores none of it.
    raw = service.query(QueryFilters(rating_id="jetbrains", metric_id=raw_metric_id(METRIC_USED_LAST_12_MONTHS)))
    assert raw == []
