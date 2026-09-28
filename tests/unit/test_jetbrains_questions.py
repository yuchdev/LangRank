from __future__ import annotations

from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
    QUESTION_REGISTRY,
    SurveyQuestion,
    question_for,
    wording_changes,
)

_SURVEY_YEARS = tuple(range(2017, 2026))
_VERBATIM_2024 = "Which programming languages have you used in the last 12 months?"

#: The ``(year, metric_id)`` pairs whose verbatim wording the source note / curated
#: NOTES confirm. Everything else is still ``wording_verified=False`` (never invented).
_VERIFIED_KEYS = {
    (2018, METRIC_USED_LAST_12_MONTHS),
    (2018, METRIC_PLANNED_ADOPTION),
    (2019, METRIC_USED_LAST_12_MONTHS),
    (2019, METRIC_PRIMARY_LANGUAGE),
    (2023, METRIC_USED_LAST_12_MONTHS),
    (2024, METRIC_USED_LAST_12_MONTHS),
}


def test_question_registry_unique_keys() -> None:
    keys = [(q.year, q.metric_id) for q in QUESTION_REGISTRY]
    assert len(keys) == len(set(keys)), "duplicate (year, metric_id) in QUESTION_REGISTRY"


def test_registry_covers_all_used_last_12_months_years() -> None:
    covered = {q.year for q in QUESTION_REGISTRY if q.metric_id == METRIC_USED_LAST_12_MONTHS}
    assert covered == set(_SURVEY_YEARS)


def test_question_for_missing_year_returns_none() -> None:
    # 2018 primary was rendered only as a rank podium (no published percentages),
    # so it is absent from the published registry, and no survey ran in 2099.
    assert question_for(2018, METRIC_PRIMARY_LANGUAGE) is None
    assert question_for(2099, METRIC_USED_LAST_12_MONTHS) is None


def test_planned_adoption_asked_every_survey_year() -> None:
    # Planned adoption was asked from the first (2017) edition on - the 2017 chart's
    # "To be adopted / migrated to soon (%)" legend proves it.
    for year in _SURVEY_YEARS:
        assert isinstance(question_for(year, METRIC_PLANNED_ADOPTION), SurveyQuestion)


def test_2017_planned_adoption_asked_but_wording_unverified() -> None:
    question = question_for(2017, METRIC_PLANNED_ADOPTION)
    assert isinstance(question, SurveyQuestion)
    # Asked (legend on record) but the verbatim question text is not confirmed, so
    # no wording is invented.
    assert question.wording is None
    assert question.wording_verified is False
    assert question.chart_legend == "To be adopted / migrated to soon (%)"


def test_primary_absent_for_2018_only() -> None:
    covered = {q.year for q in QUESTION_REGISTRY if q.metric_id == METRIC_PRIMARY_LANGUAGE}
    assert covered == set(_SURVEY_YEARS) - {2018}


def test_wording_changes_detected() -> None:
    changes = wording_changes(METRIC_USED_LAST_12_MONTHS)
    assert (2024, _VERBATIM_2024) in changes
    # The confirmed used-in-12-months wordings land as changes in ascending order.
    assert changes == [
        (2018, "What programming language(s) do you regularly use?"),
        (2019, "What programming languages have you used in the last 12 months?"),
        (2023, "Which programming, scripting, and markup languages have you used in the last 12 months?"),
        (2024, _VERBATIM_2024),
    ]
    # Only verbatim-confirmed years are reported; nothing is fabricated.
    assert all(isinstance(year, int) and isinstance(text, str) for year, text in changes)


def test_wording_changes_empty_when_no_verified_wording() -> None:
    # An unknown metric has no confirmed wording, so nothing is reported.
    assert wording_changes("jetbrains-does-not-exist") == []


def test_primary_and_planned_have_single_verified_wording() -> None:
    assert wording_changes(METRIC_PRIMARY_LANGUAGE) == [
        (2019, "What are your primary programming languages? Choose no more than 3 languages.")
    ]
    assert wording_changes(METRIC_PLANNED_ADOPTION) == [
        (
            2018,
            "Do you plan to adopt / migrate to other language(s) in the next 12 months? If so, to which one(s)?",
        )
    ]


def test_unverified_years_have_no_wording() -> None:
    for question in QUESTION_REGISTRY:
        if not question.wording_verified:
            assert question.wording is None, f"unverified {question.year}/{question.metric_id} has wording"
        else:
            assert question.wording is not None


def test_verified_wording_set_matches_source_note() -> None:
    verified = {(q.year, q.metric_id) for q in QUESTION_REGISTRY if q.wording_verified}
    assert verified == _VERIFIED_KEYS


def test_raw_metric_resolves_to_published_question() -> None:
    published = question_for(2024, METRIC_USED_LAST_12_MONTHS)
    raw = question_for(2024, f"{METRIC_USED_LAST_12_MONTHS}-raw")
    assert published is not None
    assert raw is published


def test_raw_column_prefix_set_for_verified_2024_only() -> None:
    # Subtask 06 verified the 2024 raw dump layout only: its three language questions
    # carry a ``<parent>::`` column prefix; every other year stays None (unverified,
    # never invented). 2025 is deliberately omitted - its dump reuses 2024's prefixes,
    # which would make year detection permanently ambiguous.
    prefixes = {(q.year, q.metric_id): q.raw_column_prefix for q in QUESTION_REGISTRY}
    assert prefixes[(2024, METRIC_USED_LAST_12_MONTHS)] == "proglang::"
    assert prefixes[(2024, METRIC_PRIMARY_LANGUAGE)] == "primary_lang::"
    assert prefixes[(2024, METRIC_PLANNED_ADOPTION)] == "adopt_proglang::"
    assert all(q.raw_column_prefix is None for q in QUESTION_REGISTRY if q.year != 2024), (
        "only 2024 raw layout is verified in subtask 06"
    )


def test_survey_question_is_frozen() -> None:
    question = question_for(2024, METRIC_USED_LAST_12_MONTHS)
    assert question is not None
    try:
        question.wording = "mutated"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("SurveyQuestion should be immutable")
