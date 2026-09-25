from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
import pytest

from langrank.errors import FetchError, ParseError
from langrank.models import FetchRequest, Granularity
from langrank.providers.github import (
    API_HOST,
    GITHUB_TOKEN_ENV,
    IG_MAX_CSV_BYTES,
    IG_REQUEST_BUDGET,
    METRIC_IG_PUSHERS,
    RAW_HOST,
    GitHubProvider,
    GitHubSource,
    _ensure_request_budget,
    _parse_innovation_graph,
    _resolve_commit_sha,
    _validate_commit_sha,
)
from langrank.util.http import HttpClientFactory, HttpClientOptions, _scrub_message

#: A syntactically valid 40-hex commit SHA used across the mocked tests.
VALID_SHA = "0123456789abcdef0123456789abcdef01234567"

#: A distinctive fake token that must never survive into persistence or errors.
_FAKE_TOKEN = "ghp_SEKRET0123456789abcdefSEKRET01234567"

_CSV = (
    "num_pushers,language,language_type,iso2_code,year,quarter\n"
    "1200,Python,programming,US,2024,1\n"
    "800,Python,programming,GB,2024,1\n"
    "600,Rust,programming,US,2024,2\n"
    "100,Go,programming,DE,2023,4\n"
).encode("utf-8")


def _make_transport(
    calls: list[httpx.Request],
    *,
    sha: object = VALID_SHA,
    csv_bytes: bytes = _CSV,
    raw_status: int = 200,
    raw_redirect_to: Optional[str] = None,
) -> httpx.MockTransport:
    """Build a MockTransport routing by host: commits API vs raw CSV download."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == API_HOST:
            return httpx.Response(200, json=[{"sha": sha}])
        if raw_redirect_to is not None:
            return httpx.Response(302, headers={"Location": raw_redirect_to})
        return httpx.Response(raw_status, content=csv_bytes)

    return httpx.MockTransport(handler)


def _provider(tmp_path: Path, transport: Optional[httpx.MockTransport] = None) -> GitHubProvider:
    http = None
    if transport is not None:
        http = HttpClientFactory(HttpClientOptions(retries=1), transport=transport)
    return GitHubProvider(tmp_path, http=http)


# --- fetch: SHA pinning + artifact metadata -----------------------------------


def test_ig_fetch_pins_commit_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))

    payload = provider.fetch(FetchRequest(source="innovation-graph"))

    assert payload.artifact is not None
    assert VALID_SHA in payload.artifact.url
    assert payload.artifact.metadata_json["commit_sha"] == VALID_SHA
    assert payload.artifact.metadata_json["variant"] == GitHubSource.INNOVATION_GRAPH.value
    assert "csv_sha256" in payload.artifact.metadata_json


# --- GH-SEC-6: exactly two requests + budget refusal --------------------------


def test_ig_fetch_issues_exactly_two_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))

    provider.fetch(FetchRequest())

    assert len(calls) == IG_REQUEST_BUDGET
    assert calls[0].url.host == API_HOST
    assert calls[1].url.host == RAW_HOST


def test_ensure_request_budget_refuses_over_ceiling() -> None:
    with pytest.raises(FetchError) as excinfo:
        _ensure_request_budget(61, ceiling=60, has_token=False)

    message = str(excinfo.value)
    assert "hourly ceiling" in message
    assert GITHUB_TOKEN_ENV in message  # unauthenticated guidance mentions the token


# --- GH-SEC-1: token header-only, never persisted, scrubbed from errors --------


def test_ig_token_only_on_api_host_and_never_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, _FAKE_TOKEN)
    calls: list[httpx.Request] = []
    provider = _provider(tmp_path, _make_transport(calls))

    payload = provider.fetch(FetchRequest())

    api_request, raw_request = calls
    # The token rides only the api.github.com Authorization header...
    assert api_request.url.host == API_HOST
    assert api_request.headers.get("Authorization") == f"Bearer {_FAKE_TOKEN}"
    # ...and never touches the raw host or any URL.
    assert raw_request.url.host == RAW_HOST
    assert raw_request.headers.get("Authorization") is None
    assert _FAKE_TOKEN not in str(api_request.url)
    assert _FAKE_TOKEN not in str(raw_request.url)
    # ...and never lands in the artifact or the cache.
    assert payload.artifact is not None
    assert _FAKE_TOKEN not in payload.artifact.url
    assert _FAKE_TOKEN not in payload.artifact.local_path
    assert _FAKE_TOKEN not in json.dumps(payload.artifact.metadata_json)
    assert _FAKE_TOKEN.encode() not in payload.content
    for cached in (tmp_path / "github").iterdir():
        assert _FAKE_TOKEN not in cached.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "message",
    [
        "GET failed with Authorization: Bearer ghp_liveTOKENvalue123456",
        "headers were {'authorization': 'token ghp_liveTOKENvalue123456'}",
        "leaked Bearer ghp_liveTOKENvalue123456 in trace",
        "leaked token ghp_liveTOKENvalue123456 in trace",
    ],
)
def test_scrub_message_redacts_authorization_and_bearer(message: str) -> None:
    scrubbed = _scrub_message(message)

    assert "ghp_liveTOKENvalue123456" not in scrubbed
    assert "REDACTED" in scrubbed


# --- GH-SEC-2: commit SHA validation ------------------------------------------


@pytest.mark.parametrize(
    "bad_sha",
    [
        "../../etc/passwd",
        "main",
        "0123456789abcdef",  # too short
        "0123456789abcdef0123456789abcdef012345678",  # 41 chars
        "0123456789ABCDEF0123456789abcdef01234567",  # uppercase
        "0123456789abcdef0123456789abcdef0123456g",  # non-hex
        "https://raw.githubusercontent.com/evil",
    ],
)
def test_validate_commit_sha_rejects_malformed(bad_sha: str) -> None:
    with pytest.raises(FetchError):
        _validate_commit_sha(bad_sha)


def test_resolve_commit_sha_rejects_non_hex_from_api(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []
    factory = HttpClientFactory(HttpClientOptions(retries=1), transport=_make_transport(calls, sha="not-a-sha"))

    with pytest.raises(FetchError):
        _resolve_commit_sha(factory)


# --- GH-SEC-3: raw download host-pinned, no-redirect, size-capped -------------


def test_get_capped_bytes_refuses_off_host() -> None:
    calls: list[httpx.Request] = []
    factory = HttpClientFactory(HttpClientOptions(retries=1), transport=_make_transport(calls))

    with pytest.raises(FetchError) as excinfo:
        factory.get_capped_bytes("https://evil.example/languages.csv", allowed_host=RAW_HOST)

    assert "unexpected host" in str(excinfo.value)
    assert calls == []


def test_ig_fetch_refuses_raw_redirect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    calls: list[httpx.Request] = []
    transport = _make_transport(calls, raw_redirect_to="https://evil.example/steal")
    provider = _provider(tmp_path, transport)

    with pytest.raises(FetchError) as excinfo:
        provider.fetch(FetchRequest())

    assert "redirect" in str(excinfo.value).lower()
    # The redirect target is never fetched: only the pinned hosts were contacted.
    assert all(request.url.host in (API_HOST, RAW_HOST) for request in calls)


def test_get_capped_bytes_rejects_oversized_body() -> None:
    calls: list[httpx.Request] = []
    factory = HttpClientFactory(
        HttpClientOptions(retries=1, max_response_bytes=1_000_000),
        transport=_make_transport(calls, csv_bytes=b"x" * 50),
    )

    with pytest.raises(FetchError) as excinfo:
        factory.get_capped_bytes(f"https://{RAW_HOST}/f.csv", allowed_host=RAW_HOST, max_bytes=10)

    assert "byte ceiling" in str(excinfo.value)


def test_ig_max_csv_bytes_has_headroom() -> None:
    # The CSV cap is generously above the default 10 MB JSON cap (file grows quarterly).
    assert IG_MAX_CSV_BYTES > 10_000_000


# --- GH-SEC-4: pinned-commit integrity via sidecar ----------------------------


def test_ig_offline_uses_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    calls: list[httpx.Request] = []
    online = _provider(tmp_path, _make_transport(calls))
    online_payload = online.fetch(FetchRequest())

    def _forbidden(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("offline fetch must not touch the network")

    offline = _provider(tmp_path, httpx.MockTransport(_forbidden))
    replayed = offline.fetch(FetchRequest(offline=True))

    assert replayed.artifact is None
    assert replayed.content == online_payload.content
    # The commit SHA survives the replay and reaches parse.
    records = offline.parse(replayed)
    assert records
    assert all(record.metadata["commit_sha"] == VALID_SHA for record in records)


def test_ig_offline_detects_tampered_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    calls: list[httpx.Request] = []
    online = _provider(tmp_path, _make_transport(calls))
    online.fetch(FetchRequest())

    sidecars = list((tmp_path / "github").glob("github-*.meta"))
    assert len(sidecars) == 1
    sidecars[0].write_text(json.dumps({"commit_sha": VALID_SHA, "csv_sha256": "deadbeef"}), encoding="utf-8")

    offline = _provider(tmp_path, _make_transport([]))
    with pytest.raises(FetchError) as excinfo:
        offline.fetch(FetchRequest(offline=True))

    assert "integrity" in str(excinfo.value)


def test_ig_offline_without_sidecar_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    online = _provider(tmp_path, _make_transport([]))
    online.fetch(FetchRequest())
    for sidecar in (tmp_path / "github").glob("github-*.meta"):
        sidecar.unlink()

    offline = _provider(tmp_path, _make_transport([]))
    with pytest.raises(FetchError) as excinfo:
        offline.fetch(FetchRequest(offline=True))

    assert "sidecar" in str(excinfo.value)


# --- parse: rows -> records + GH-SEC-5 shape/numeric validation ---------------


def test_ig_parse_rows_to_records() -> None:
    records = _parse_innovation_graph(_CSV, commit_sha=VALID_SHA)

    assert len(records) == 4
    first = records[0]
    assert first.metric_id == METRIC_IG_PUSHERS
    assert first.language == "Python"
    assert first.value == 1200.0
    assert first.unit == "count"
    assert first.granularity is Granularity.QUARTER
    assert (first.period_start, first.period_end) == (date(2024, 1, 1), date(2024, 3, 31))
    assert first.period_label == "2024-Q1"
    assert first.metadata == {
        "iso2_code": "US",
        "commit_sha": VALID_SHA,
        "variant": GitHubSource.INNOVATION_GRAPH.value,
    }
    # Per-economy: same language/quarter, distinct economy is a distinct record.
    assert records[1].metadata["iso2_code"] == "GB"
    assert records[3].period_label == "2023-Q4"


def test_ig_parse_missing_column_raises() -> None:
    content = b"language,iso2_code,year,quarter\nPython,US,2024,1\n"

    with pytest.raises(ParseError) as excinfo:
        _parse_innovation_graph(content, commit_sha=VALID_SHA)

    assert "num_pushers" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad_row",
    [
        "-5,Python,programming,US,2024,1",  # negative count
        "abc,Python,programming,US,2024,1",  # non-numeric count
        "10,Python,programming,US,2024,5",  # quarter out of range
        "10,Python,programming,US,1999,1",  # implausible year
        "10,Python,programming,US,notayear,1",  # non-numeric year
    ],
)
def test_ig_parse_rejects_malformed_cells(bad_row: str) -> None:
    content = ("num_pushers,language,language_type,iso2_code,year,quarter\n" + bad_row + "\n").encode("utf-8")

    with pytest.raises(ParseError):
        _parse_innovation_graph(content, commit_sha=VALID_SHA)


def test_ig_parse_rejects_non_utf8() -> None:
    content = b"num_pushers,language,language_type,iso2_code,year,quarter\n1,\xff,programming,US,2024,1\n"

    with pytest.raises(ParseError) as excinfo:
        _parse_innovation_graph(content, commit_sha=VALID_SHA)

    assert "UTF-8" in str(excinfo.value)


# --- parse: window filtering --------------------------------------------------


def test_ig_parse_window_filters_by_period_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    provider = _provider(tmp_path, _make_transport([]))
    payload = provider.fetch(FetchRequest(since=date(2024, 1, 1), until=date(2024, 12, 31)))

    records = provider.parse(payload)

    # The 2023-Q4 row falls outside the requested window and is dropped.
    assert {record.period_label for record in records} == {"2024-Q1", "2024-Q2"}
