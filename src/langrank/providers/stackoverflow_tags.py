from __future__ import annotations

import json
import os
from calendar import monthrange
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from time import sleep
from typing import Any, Optional

from langrank.errors import FetchError, ProviderError
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
from langrank.providers.common import load_cached_payload, payload_from_content
from langrank.util.http import HttpClientFactory

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "stackoverflow-tags-v1"

#: Environment variable holding the optional Stack Exchange application key.
STACKEXCHANGE_KEY_ENV = "LANGRANK_STACKEXCHANGE_KEY"

#: Pinned scheme+host for every keyed request (SEC-2).
API_HOST = "api.stackexchange.com"

#: The ``filter=total`` questions endpoint (secret-free base URL).
API_URL = "https://api.stackexchange.com/2.3/questions"

#: Enforced daily request ceiling with an app key (source-note gate).
KEYED_DAILY_BUDGET = 5000

#: Enforced daily request ceiling without a key (anonymous per-IP quota).
ANON_DAILY_BUDGET = 300

#: Upper bound honoured for a response ``backoff`` field, clamped to stay sane (SEC-4).
MAX_BACKOFF_SECONDS = 300.0

#: Default backfill span (years) when the request supplies no window.
DEFAULT_YEARS = 10

#: Valid ``--source`` values that select API mode.
_API_SOURCES = frozenset({None, "auto", "api"})

#: Metric ID for the raw monthly new-question count per language tag.
METRIC_QUESTIONS = "stackoverflow-tags-questions"

#: Metric ID for the derived monthly question share (percent of a stated denominator).
METRIC_SHARE = "stackoverflow-tags-question-share"

#: Metric ID for the derived monthly rank (Stack Overflow publishes no rank).
METRIC_RANK = "stackoverflow-tags-rank"

#: Homepage for the Stack Overflow tag index.
HOMEPAGE = "https://stackoverflow.com/tags"

#: Master Stack Overflow tag per canonical language.
#:
#: ``api`` mode queries exactly one master tag per language, so this map holds the
#: single tag Stack Overflow merges its synonyms into (e.g. ``cpp`` -> ``c++``,
#: ``golang`` -> ``go``). Keys are the source tag strings; values are canonical
#: language IDs. Every key resolves through
#: :meth:`LanguageNormalizer.resolve` with ``rating_id="stackoverflow-tags"``.
TAG_TO_LANGUAGE: dict[str, str] = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "c#": "c#",
    "c++": "c++",
    "c": "c",
    "php": "php",
    "go": "go",
    "rust": "rust",
    "kotlin": "kotlin",
    "swift": "swift",
    "ruby": "ruby",
    "r": "r",
    "scala": "scala",
    "dart": "dart",
    "objective-c": "objective-c",
    "perl": "perl",
    "lua": "lua",
    "haskell": "haskell",
    "elixir": "elixir",
    "julia": "julia",
    "matlab": "matlab",
    "sql": "sql",
    "assembly": "assembly",
    "groovy": "groovy",
    "powershell": "powershell",
    "bash": "shell",
    "vb.net": "vb.net",
    "fortran": "fortran",
    "cobol": "cobol",
    "ada": "ada",
    "delphi": "delphi",
    "zig": "zig",
}


class StackOverflowTagsProvider:
    """Records monthly Stack Overflow question activity per language tag.

    This provider measures *tag activity* (new-question counts) - a different
    signal from ``stackoverflow-survey`` (self-reported usage); the two are never
    conflated. It publishes a raw ``questions`` count plus a derived
    ``question-share`` (preferred for long-term comparison) and a derived ``rank``.

    :ivar provider_id: Stable rating ID used across the pipeline.
    """

    provider_id = "stackoverflow-tags"

    def __init__(self, cache_dir: Path, *, http: Optional[HttpClientFactory] = None) -> None:
        """Wire the provider's cache directory, HTTP client and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the
            ``stackoverflow-tags`` subdirectory beneath it.
        :param http: HTTP client factory; injectable so tests can supply an
            ``httpx.MockTransport``. Defaults to a real factory.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._http = http or HttpClientFactory()
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: metrics, caveats and methodology.

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Stack Overflow Tags",
            description=("Monthly Stack Overflow question activity per language tag (tag activity, not usage)."),
            homepage=HOMEPAGE,
            default_metric=METRIC_SHARE,
            native_granularity=Granularity.MONTH,
            caveats=[
                "Tag activity, not usage - not comparable with stackoverflow-survey.",
                "Shares can sum above 100% (multi-tag questions).",
                "Share denominator differs by --source.",
                "Overall SO question volume declined sharply after 2022; prefer share over counts.",
            ],
            parser_version=PARSER_VERSION,
            metrics=[
                MetricDefinition(
                    id=METRIC_QUESTIONS,
                    rating_id=self.provider_id,
                    display_name="Questions",
                    unit="count",
                    higher_is_better=True,
                    description="Monthly count of new Stack Overflow questions carrying the language's master tag.",
                ),
                MetricDefinition(
                    id=METRIC_SHARE,
                    rating_id=self.provider_id,
                    display_name="Question share (%)",
                    unit="percent",
                    higher_is_better=True,
                    description=(
                        "Derived monthly question share. Denominator depends on --source: "
                        "'api' divides by all_questions (site-wide new-question total); "
                        "'sede' divides by tracked_language_union (deduplicated union of tracked "
                        "master tags). The two denominators are never mixed in one series."
                    ),
                ),
                MetricDefinition(
                    id=METRIC_RANK,
                    rating_id=self.provider_id,
                    display_name="Rank",
                    unit="rank",
                    higher_is_better=False,
                    description="Derived monthly ordinal rank (1 is best); Stack Overflow publishes no rank.",
                ),
            ],
            methodology_notes=[
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="api-all-questions-v1",
                    valid_from=date(2008, 9, 1),
                    valid_to=None,
                    description=(
                        "'api' source: share denominator is all_questions, the site-wide new-question "
                        "total from a filter=total call with no tag "
                        "(derivation_method='question_share:all_questions')."
                    ),
                    source_url="https://api.stackexchange.com/2.3/questions",
                ),
                MethodologyNote(
                    rating_id=self.provider_id,
                    methodology_version="sede-tracked-union-v1",
                    valid_from=date(2008, 9, 1),
                    valid_to=None,
                    description=(
                        "'sede' source: share denominator is tracked_language_union, the deduplicated "
                        "union of questions carrying any tracked master tag "
                        "(derivation_method='question_share:tracked_language_union')."
                    ),
                    source_url="https://data.stackexchange.com/",
                ),
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw monthly tag activity from the Stack Exchange API, or replay cache.

        API mode issues one ``filter=total`` call per tracked tag per complete
        month plus one denominator (``all_questions``) call per month. The daily
        request budget is checked *before* the first call and no partial fetch is
        performed on overflow. ``--offline`` replays the newest cached artifact and
        constructs no HTTP client.

        :param request: Fetch parameters (date window, source mode, cache flags).
        :returns: The raw JSON fetch payload.
        :raises ProviderError: For an invalid or ``sede`` ``--source``.
        :raises FetchError: When the request budget would be exceeded, the window
            is empty, or the API call fails.
        """
        source = request.source
        if source not in _API_SOURCES:
            if source == "sede":
                raise ProviderError(
                    "the 'sede' source is a manual import; run "
                    "`langrank import --rating stackoverflow-tags <csv>` instead."
                )
            raise ProviderError(f"unknown --source {source!r}; valid sources: auto, api, sede.")

        if request.offline:
            return load_cached_payload(provider_id=self.provider_id, cache_dir=self._cache_dir)

        since, until = self._resolve_window(request)
        months = _month_windows(since, until)
        if not months:
            raise FetchError("no complete month in the requested window; nothing to fetch.")

        key = os.environ.get(STACKEXCHANGE_KEY_ENV) or None
        daily_budget = KEYED_DAILY_BUDGET if key else ANON_DAILY_BUDGET
        tags = sorted(TAG_TO_LANGUAGE)
        client = StackExchangeClient(self._http, key, daily_budget)
        planned = len(months) * (len(tags) + 1)
        client.ensure_budget(planned)

        month_entries: list[dict[str, Any]] = []
        for start, end in months:
            total = client.count_questions(None, start, end)
            tag_counts = {tag: client.count_questions(tag, start, end) for tag in tags}
            month_entries.append({"month": f"{start.year:04d}-{start.month:02d}", "total": total, "tags": tag_counts})

        document = {"source": "api", "denominator": "all_questions", "months": month_entries}
        content = json.dumps(document, sort_keys=True).encode("utf-8")
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=API_URL,
            content=content,
            mime_type="application/json",
            metadata_json={
                "source": "api",
                "denominator": "all_questions",
                "month_count": len(months),
                "requests_made": client.requests_made,
            },
            no_cache=request.no_cache,
        )

    def _resolve_window(self, request: FetchRequest) -> tuple[date, date]:
        """Resolve the ``[since, until]`` fetch window, capped at the last complete month.

        :param request: The fetch request whose ``since``/``until``/``years``
            narrow the default 10-year window.
        :returns: The inclusive ``(since, until)`` date window.
        """
        last_complete_end = _last_day_of_month(_previous_month(self._retrieved_at.date()))
        until = request.until or last_complete_end
        if request.since is not None:
            since = request.since
        else:
            span = request.years or DEFAULT_YEARS
            since = date(until.year - span, until.month, 1)
        return since, until

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse a raw payload into source records (implemented in subtask 05).

        :param raw: The raw fetch payload.
        :returns: Parsed source records.
        :raises NotImplementedError: Always, until subtask 05 lands the parser.
        """
        raise NotImplementedError("stackoverflow-tags parse lands in subtask 05.")

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations (implemented in subtask 05).

        :param records: Parsed source records.
        :returns: Canonical observations.
        :raises NotImplementedError: Always, until subtask 05 lands normalization.
        """
        raise NotImplementedError("stackoverflow-tags normalize lands in subtask 05.")

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations with named codes (implemented in subtask 06).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Always, until subtask 06 lands validation.
        """
        raise NotImplementedError("stackoverflow-tags validate lands in subtask 06.")


def _next_month(day: date) -> date:
    """Return the first day of the month after ``day``'s month.

    :param day: Any date.
    :returns: The first day of the following month.
    """
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _previous_month(day: date) -> date:
    """Return the first day of the month before ``day``'s month.

    :param day: Any date.
    :returns: The first day of the preceding month.
    """
    if day.month == 1:
        return date(day.year - 1, 12, 1)
    return date(day.year, day.month - 1, 1)


def _last_day_of_month(day: date) -> date:
    """Return the last calendar day of ``day``'s month.

    :param day: Any date.
    :returns: The month's final day.
    """
    return date(day.year, day.month, monthrange(day.year, day.month)[1])


def _month_windows(since: date, until: date) -> list[tuple[date, date]]:
    """Enumerate ``(month_start, month_end)`` windows for every complete month in range.

    A month is included only when its final day falls on or before ``until``, so a
    partial trailing month - in particular the current, incomplete month when
    ``until`` is today - is excluded.

    :param since: Inclusive lower bound; its month is the first candidate.
    :param until: Inclusive upper bound.
    :returns: Chronologically ordered ``(first_day, last_day)`` month windows.
    """
    windows: list[tuple[date, date]] = []
    cursor = date(since.year, since.month, 1)
    while cursor <= until:
        month_end = _last_day_of_month(cursor)
        if month_end <= until:
            windows.append((cursor, month_end))
        cursor = _next_month(cursor)
    return windows


def _to_epoch(day: date, *, end_of_day: bool) -> int:
    """Convert a UTC calendar day to a Unix timestamp at the day's first or last second.

    :param day: The calendar day.
    :param end_of_day: When ``True`` use ``23:59:59``; otherwise ``00:00:00``.
    :returns: The corresponding Unix epoch seconds.
    """
    moment = datetime(day.year, day.month, day.day, 23, 59, 59 if end_of_day else 0, tzinfo=UTC)
    if not end_of_day:
        moment = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=UTC)
    return int(moment.timestamp())


class StackExchangeClient:
    """Budget-aware Stack Exchange ``filter=total`` question counter.

    Counts issued requests, refuses to start when the plan exceeds the daily
    budget (SEC-6), pins every request to ``api.stackexchange.com`` (SEC-2),
    validates the ``total`` field and clamps any ``backoff`` before sleeping
    (SEC-4). The optional key is passed only via query parameters (SEC-1).

    :ivar _http: Injected HTTP client factory.
    :ivar _key: Optional Stack Exchange application key.
    :ivar _daily_budget: Enforced request ceiling for this run.
    :ivar _requests_made: Count of issued requests.
    """

    def __init__(self, http: HttpClientFactory, key: Optional[str], daily_budget: int) -> None:
        """Wire the client.

        :param http: HTTP client factory used for every call.
        :param key: Optional application key; raises the daily budget when present.
        :param daily_budget: Maximum requests this run may issue.
        """
        self._http = http
        self._key = key
        self._daily_budget = daily_budget
        self._requests_made = 0

    @property
    def requests_made(self) -> int:
        """Number of API requests issued so far.

        :returns: The running request count.
        """
        return self._requests_made

    def ensure_budget(self, planned_requests: int) -> None:
        """Refuse to start when the planned request count exceeds the daily budget.

        :param planned_requests: Total calls the fetch intends to make.
        :raises FetchError: If ``planned_requests`` exceeds the daily budget; no
            request has been issued at this point (SEC-6).
        """
        if planned_requests > self._daily_budget:
            raise FetchError(
                f"planned {planned_requests} Stack Exchange requests exceed the daily budget "
                f"of {self._daily_budget}; narrow the window (--since/--until/--years) "
                f"{'or set ' + STACKEXCHANGE_KEY_ENV if self._key is None else ''}".strip()
            )

    def count_questions(self, tag: Optional[str], start: date, end: date) -> int:
        """Return the ``filter=total`` question count for a tag (or all questions) in a month.

        :param tag: Master tag to count, or ``None`` for the site-wide denominator.
        :param start: First day of the month (inclusive).
        :param end: Last day of the month (inclusive).
        :returns: The non-negative question total.
        :raises FetchError: On a malformed response ``total``.
        """
        params: dict[str, str] = {
            "site": "stackoverflow",
            "filter": "total",
            "fromdate": str(_to_epoch(start, end_of_day=False)),
            "todate": str(_to_epoch(end, end_of_day=True)),
        }
        if tag is not None:
            params["tagged"] = tag
        if self._key is not None:
            params["key"] = self._key

        data = self._http.get_json(API_URL, params=params, allowed_host=API_HOST)
        self._requests_made += 1
        if not isinstance(data, dict):
            raise FetchError("Stack Exchange response was not a JSON object.")
        total = data.get("total")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise FetchError("Stack Exchange response 'total' was not a non-negative integer.")
        self._honour_backoff(data.get("backoff"))
        return total

    @staticmethod
    def _honour_backoff(backoff: Any) -> None:
        """Sleep for a clamped ``backoff`` interval when the response requests one (SEC-4).

        :param backoff: The response ``backoff`` field, if any.
        """
        if isinstance(backoff, bool) or not isinstance(backoff, (int, float)):
            return
        if backoff <= 0:
            return
        sleep(min(float(backoff), MAX_BACKOFF_SECONDS))
