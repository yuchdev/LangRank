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


def test_question_registry_unique_keys() -> None:
    keys = [(q.year, q.metric_id) for q in QUESTION_REGISTRY]
    assert len(keys) == len(set(keys)), "duplicate (year, metric_id) in QUESTION_REGISTRY"


def test_registry_covers_all_used_last_12_months_years() -> None:
    covered = {q.year for q in QUESTION_REGISTRY if q.metric_id == METRIC_USED_LAST_12_MONTHS}
    assert covered == set(_SURVEY_YEARS)


def test_question_for_missing_year_returns_none() -> None:
    # Planned adoption was not asked in the first (2017) edition, and no survey
    # ran in 2099.
    assert question_for(2017, METRIC_PLANNED_ADOPTION) is None
    assert question_for(2099, METRIC_USED_LAST_12_MONTHS) is None


def test_planned_adoption_asked_from_2018() -> None:
    for year in _SURVEY_YEARS:
        question = question_for(year, METRIC_PLANNED_ADOPTION)
        if year == 2017:
            assert question is None
        else:
            assert isinstance(question, SurveyQuestion)


def test_wording_changes_detected() -> None:
    changes = wording_changes(METRIC_USED_LAST_12_MONTHS)
    assert (2024, _VERBATIM_2024) in changes
    # Only verbatim-confirmed years are reported; nothing is fabricated.
    assert all(isinstance(year, int) and isinstance(text, str) for year, text in changes)


def test_wording_changes_empty_when_no_verified_wording() -> None:
    assert wording_changes(METRIC_PRIMARY_LANGUAGE) == []


def test_unverified_years_have_no_wording() -> None:
    for question in QUESTION_REGISTRY:
        if not question.wording_verified:
            assert question.wording is None, f"unverified {question.year}/{question.metric_id} has wording"
        else:
            assert question.wording is not None


def test_only_2024_used_last_12_months_is_verified() -> None:
    verified = {(q.year, q.metric_id) for q in QUESTION_REGISTRY if q.wording_verified}
    assert verified == {(2024, METRIC_USED_LAST_12_MONTHS)}


def test_raw_metric_resolves_to_published_question() -> None:
    published = question_for(2024, METRIC_USED_LAST_12_MONTHS)
    raw = question_for(2024, f"{METRIC_USED_LAST_12_MONTHS}-raw")
    assert published is not None
    assert raw is published


def test_raw_column_prefix_unset_pending_subtask_06() -> None:
    assert all(q.raw_column_prefix is None for q in QUESTION_REGISTRY)


def test_survey_question_is_frozen() -> None:
    question = question_for(2024, METRIC_USED_LAST_12_MONTHS)
    assert question is not None
    try:
        question.wording = "mutated"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("SurveyQuestion should be immutable")
