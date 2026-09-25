from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from langrank.errors import FetchError
from langrank.util.http import HttpClientFactory, HttpClientOptions

API_HOST = "api.stackexchange.com"
API_URL = "https://api.stackexchange.com/2.3/questions"


def _recording_transport(
    calls: list[httpx.Request],
    response_for: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    """Build a MockTransport that records every request before answering.

    :param calls: List mutated in place with each issued request.
    :param response_for: Factory turning a request into the canned response.
    :returns: A configured :class:`httpx.MockTransport`.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return response_for(request)

    return httpx.MockTransport(handler)


def _factory(
    transport: httpx.MockTransport,
    *,
    max_response_bytes: int = 10_000_000,
) -> HttpClientFactory:
    """Build a factory with a single attempt so failures do not sleep/retry."""
    options = HttpClientOptions(retries=1, max_response_bytes=max_response_bytes)
    return HttpClientFactory(options, transport=transport)


# --- SEC-2: host/scheme pinning and redirect refusal --------------------------


def test_get_json_refuses_off_host_url() -> None:
    calls: list[httpx.Request] = []
    factory = _factory(_recording_transport(calls, lambda _r: httpx.Response(200, json={"total": 1})))

    with pytest.raises(FetchError) as excinfo:
        factory.get_json(
            "https://evil.example/2.3/questions",
            params={"key": "secret-key-off-host"},
            allowed_host=API_HOST,
        )

    message = str(excinfo.value)
    assert "unexpected host" in message
    assert "evil.example" in message
    assert "secret-key-off-host" not in message
    # No request may reach the wire when the host is wrong.
    assert calls == []


def test_get_json_refuses_non_https_url() -> None:
    calls: list[httpx.Request] = []
    factory = _factory(_recording_transport(calls, lambda _r: httpx.Response(200, json={"total": 1})))

    with pytest.raises(FetchError) as excinfo:
        factory.get_json(
            "http://api.stackexchange.com/2.3/questions",
            params={"key": "secret-key-plain"},
            allowed_host=API_HOST,
        )

    message = str(excinfo.value)
    assert "non-HTTPS" in message
    assert "secret-key-plain" not in message
    assert calls == []


def test_get_json_refuses_redirect_without_cross_host_request() -> None:
    calls: list[httpx.Request] = []
    factory = _factory(
        _recording_transport(
            calls,
            lambda _r: httpx.Response(302, headers={"Location": "https://evil.example/steal"}),
        )
    )

    with pytest.raises(FetchError) as excinfo:
        factory.get_json(
            API_URL,
            params={"site": "stackoverflow", "key": "secret-key-redirect"},
            allowed_host=API_HOST,
        )

    message = str(excinfo.value)
    assert "redirect" in message.lower()
    assert "secret-key-redirect" not in message
    # A request was issued, but only ever to the pinned host - the 3xx is refused,
    # never replayed to evil.example.
    assert calls
    assert all(request.url.host == API_HOST for request in calls)


# --- SEC-3: response size ceiling ---------------------------------------------


def test_get_json_rejects_oversized_body() -> None:
    calls: list[httpx.Request] = []
    oversized = b"x" * 500
    factory = _factory(
        _recording_transport(calls, lambda _r: httpx.Response(200, content=oversized)),
        max_response_bytes=100,
    )

    with pytest.raises(FetchError) as excinfo:
        factory.get_json(API_URL, params={"site": "stackoverflow"}, allowed_host=API_HOST)

    assert "byte ceiling" in str(excinfo.value)


def test_get_json_accepts_body_at_ceiling() -> None:
    """A body exactly at the ceiling is not rejected (boundary check)."""
    calls: list[httpx.Request] = []
    body = b'{"total": 0}'
    factory = _factory(
        _recording_transport(calls, lambda _r: httpx.Response(200, content=body)),
        max_response_bytes=len(body),
    )

    result = factory.get_json(API_URL, params={"site": "stackoverflow"}, allowed_host=API_HOST)

    assert result == {"total": 0}


# --- GH-SEC-6: only transient failures are retried ----------------------------


def _retrying_factory(transport: httpx.MockTransport, monkeypatch: pytest.MonkeyPatch) -> HttpClientFactory:
    """Build a factory with three attempts and a no-op sleep."""
    monkeypatch.setattr("langrank.util.http.sleep", lambda _seconds: None)
    return HttpClientFactory(HttpClientOptions(retries=3), transport=transport)


@pytest.mark.parametrize("status", [401, 403, 404])
def test_get_json_does_not_retry_client_errors(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[httpx.Request] = []
    factory = _retrying_factory(_recording_transport(calls, lambda _r: httpx.Response(status)), monkeypatch)
    with pytest.raises(FetchError):
        factory.get_json(API_URL, allowed_host="api.stackexchange.com")
    assert len(calls) == 1


def test_get_json_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[httpx.Request] = []

    def answer(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if len(calls) < 2 else httpx.Response(200, json={"total": 1})

    factory = _retrying_factory(_recording_transport(calls, answer), monkeypatch)
    assert factory.get_json(API_URL, allowed_host="api.stackexchange.com") == {"total": 1}
    assert len(calls) == 2


def test_get_capped_bytes_does_not_retry_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[httpx.Request] = []
    transport = _recording_transport(
        calls, lambda _r: httpx.Response(302, headers={"Location": "https://evil.example/x"})
    )
    factory = _retrying_factory(transport, monkeypatch)
    with pytest.raises(FetchError, match="redirect"):
        factory.get_capped_bytes("https://raw.githubusercontent.com/a/b", allowed_host="raw.githubusercontent.com")
    assert len(calls) == 1
