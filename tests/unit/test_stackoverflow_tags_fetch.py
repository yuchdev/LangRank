from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
import pytest

from langrank.errors import FetchError, ProviderError
from langrank.models import FetchRequest
from langrank.providers.stackoverflow_tags import (
    MAX_BACKOFF_SECONDS,
    STACKEXCHANGE_KEY_ENV,
    TAG_TO_LANGUAGE,
    StackExchangeClient,
    StackOverflowTagsProvider,
    _month_windows,
)
from langrank.util.http import HttpClientFactory

_SLEEP_TARGET = "langrank.providers.stackoverflow_tags.sleep"

_FAKE_KEY = "do-not-log-me-0001"


def _make_transport(
    calls: list[httpx.Request],
    *,
    denominator_total: int = 1000,
    tag_total: int = 42,
    backoff: Optional[float] = None,
    status: int = 200,
) -> httpx.MockTransport:
    """Build a MockTransport recording every request and returning canned counts."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json={})
        params = dict(request.url.params)
        body: dict[str, object] = {"total": tag_total if "tagged" in params else denominator_total}
        if backoff is not None:
            body["backoff"] = backoff
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def _provider(
    tmp_path: Path,
    transport: Optional[httpx.MockTransport] = None,
) -> StackOverflowTagsProvider:
    http = HttpClientFactory(transport=transport) if transport is not None else None
    return StackOverflowTagsProvider(tmp_path, http=http)


def test_month_windows_excludes_current_month() -> None:
    windows = _month_windows(date(2024, 1, 1), date(2024, 5, 15))

    assert windows[0] == (date(2024, 1, 1), date(2024, 1, 31))
    assert windows[-1] == (date(2024, 4, 1), date(2024, 4, 30))
    assert all(end <= date(2024, 5, 15) for _, end in windows)
    # The incomplete May window (ends 2024-05-31) is dropped.
    assert (date(2024, 5, 1), date(2024, 5, 31)) not in windows


def test_fetch_api_builds_payload_from_mocked_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STACKEXCHANGE_KEY_ENV, raising=False)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls, denominator_total=1000, tag_total=42))

    payload = provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 2, 29)))

    document = json.loads(payload.content)
    assert document["source"] == "api"
    assert document["denominator"] == "all_questions"
    months = {entry["month"]: entry for entry in document["months"]}
    assert set(months) == {"2024-01", "2024-02"}
    for entry in months.values():
        assert entry["total"] == 1000
        assert set(entry["tags"]) == set(TAG_TO_LANGUAGE)
        assert entry["tags"]["python"] == 42
    # 2 months * (34 tags + 1 denominator) requests issued.
    assert len(calls) == 2 * (len(TAG_TO_LANGUAGE) + 1)


def test_fetch_budget_exceeded_raises_before_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STACKEXCHANGE_KEY_ENV, raising=False)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))

    with pytest.raises(FetchError) as excinfo:
        provider.fetch(FetchRequest())  # default 10-year window vastly exceeds the 300/day anon budget

    assert "budget" in str(excinfo.value).lower()
    assert calls == []


def test_fetch_honours_backoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STACKEXCHANGE_KEY_ENV, raising=False)
    slept: list[float] = []
    monkeypatch.setattr(
        "langrank.providers.stackoverflow_tags.sleep",
        lambda seconds: slept.append(seconds),
    )
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls, backoff=2))

    provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 1, 31)))

    assert 2.0 in slept


def test_api_key_not_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STACKEXCHANGE_KEY_ENV, _FAKE_KEY)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))

    payload = provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 1, 31)))

    assert payload.artifact is not None
    artifact = payload.artifact
    assert _FAKE_KEY not in artifact.url
    assert _FAKE_KEY not in artifact.local_path
    assert _FAKE_KEY not in json.dumps(artifact.metadata_json)
    assert _FAKE_KEY.encode() not in payload.content
    # The key did reach the wire (via params), proving it is scrubbed only from persistence.
    assert any("key" in dict(request.url.params) for request in calls)


def test_api_key_scrubbed_from_error_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STACKEXCHANGE_KEY_ENV, _FAKE_KEY)
    monkeypatch.setattr("langrank.util.http.sleep", lambda _seconds: None)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls, status=404))

    with pytest.raises(FetchError) as excinfo:
        provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 1, 31)))

    message = str(excinfo.value)
    assert _FAKE_KEY not in message
    assert "REDACTED" in message


def test_offline_uses_cached_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STACKEXCHANGE_KEY_ENV, raising=False)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))
    online = provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 1, 31)))

    def _forbidden(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("offline fetch must not touch the network")

    offline_provider = _provider(tmp_path, httpx.MockTransport(_forbidden))
    replayed = offline_provider.fetch(FetchRequest(offline=True))

    assert replayed.artifact is None
    assert replayed.content == online.content


def test_offline_without_cache_raises(tmp_path: Path) -> None:
    provider = _provider(tmp_path)

    with pytest.raises(FetchError):
        provider.fetch(FetchRequest(offline=True))


def _single_response_client(
    *,
    body: Optional[dict[str, object]] = None,
    content: Optional[bytes] = None,
    key: Optional[str] = None,
) -> StackExchangeClient:
    """Build a StackExchangeClient over a MockTransport returning one canned body."""

    def handler(_request: httpx.Request) -> httpx.Response:
        if content is not None:
            return httpx.Response(200, content=content)
        return httpx.Response(200, json=body if body is not None else {})

    factory = HttpClientFactory(transport=httpx.MockTransport(handler))
    return StackExchangeClient(factory, key, daily_budget=300)


# --- SEC-4: backoff clamp and untrusted-JSON shape validation -----------------


def test_honour_backoff_clamps_to_max(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(_SLEEP_TARGET, lambda seconds: slept.append(seconds))

    StackExchangeClient._honour_backoff(10_000)

    assert slept == [MAX_BACKOFF_SECONDS]


@pytest.mark.parametrize("backoff", [True, False, "5", None, -1, 0, [], {}])
def test_honour_backoff_ignores_malformed_or_nonpositive(monkeypatch: pytest.MonkeyPatch, backoff: object) -> None:
    slept: list[float] = []
    monkeypatch.setattr(_SLEEP_TARGET, lambda seconds: slept.append(seconds))

    StackExchangeClient._honour_backoff(backoff)

    assert slept == []


@pytest.mark.parametrize(
    "body",
    [
        {},  # missing total
        {"total": -1},  # negative
        {"total": True},  # bool masquerading as int
        {"total": "5"},  # string
        {"total": 1.0},  # float, not int
        {"total": None},  # explicit null
    ],
)
def test_count_questions_rejects_malformed_total(body: dict[str, object]) -> None:
    client = _single_response_client(body=body)

    with pytest.raises(FetchError) as excinfo:
        client.count_questions(None, date(2024, 1, 1), date(2024, 1, 31))

    assert "total" in str(excinfo.value).lower()
    # The request was issued (counted) before the shape check rejected the body.
    assert client.requests_made == 1


def test_count_questions_rejects_non_dict_body() -> None:
    client = _single_response_client(content=b"[1, 2, 3]")

    with pytest.raises(FetchError) as excinfo:
        client.count_questions(None, date(2024, 1, 1), date(2024, 1, 31))

    assert "JSON object" in str(excinfo.value)


def test_count_questions_rejects_non_json_body() -> None:
    client = _single_response_client(content=b"<html>not json</html>")

    with pytest.raises(FetchError) as excinfo:
        client.count_questions(None, date(2024, 1, 1), date(2024, 1, 31))

    assert "not valid JSON" in str(excinfo.value)
    # A body that never parsed is not counted as a completed request.
    assert client.requests_made == 0


def test_count_questions_accepts_valid_total(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_SLEEP_TARGET, lambda _seconds: None)
    client = _single_response_client(body={"total": 7})

    assert client.count_questions("python", date(2024, 1, 1), date(2024, 1, 31)) == 7
    assert client.requests_made == 1


def test_fetch_sede_source_directs_to_import(tmp_path: Path) -> None:
    provider = _provider(tmp_path)

    with pytest.raises(ProviderError) as excinfo:
        provider.fetch(FetchRequest(source="sede"))

    assert "langrank import" in str(excinfo.value)


def test_fetch_unknown_source_lists_valid_sources(tmp_path: Path) -> None:
    provider = _provider(tmp_path)

    with pytest.raises(ProviderError) as excinfo:
        provider.fetch(FetchRequest(source="bogus"))

    assert "api" in str(excinfo.value)
