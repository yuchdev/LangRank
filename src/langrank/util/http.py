from __future__ import annotations

import json
import re
from dataclasses import dataclass
from time import sleep
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from langrank.errors import FetchError

#: Retryable upstream status codes (rate limit + transient server errors).
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

#: Query-parameter names whose values are secrets and must be redacted from any
#: error text before it can reach a log sink or stack trace (SEC-1).
_SECRET_QUERY_KEYS = frozenset({"key", "access_token"})

#: Matches an ``http(s)`` URL embedded anywhere in a free-form error message.
_URL_RE = re.compile(r"https?://[^\s'\"]+")

#: Matches a bare ``key=...`` / ``access_token=...`` pair as a defence-in-depth
#: fallback for error text that is not a well-formed URL.
_SECRET_PARAM_RE = re.compile(r"(?i)\b(key|access_token)=[^&\s'\"]+")


def _scrub_url(url: str) -> str:
    """Redact secret query parameters from a single URL.

    :param url: A candidate URL, possibly carrying a ``key``/``access_token``.
    :returns: The URL with secret query values replaced by ``REDACTED``; the
        input is returned unchanged when it has no query string or cannot be
        parsed.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.query:
        return url
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    scrubbed = [(name, "REDACTED" if name.lower() in _SECRET_QUERY_KEYS else value) for name, value in pairs]
    return urlunsplit(parts._replace(query=urlencode(scrubbed)))


def _scrub_message(message: str) -> str:
    """Strip secret query values from every URL (and bare secret pair) in ``message``.

    :param message: Free-form error text that may embed a request URL.
    :returns: The message with any ``key``/``access_token`` values redacted (SEC-1).
    """
    scrubbed = _URL_RE.sub(lambda match: _scrub_url(match.group(0)), message)
    return _SECRET_PARAM_RE.sub(lambda match: f"{match.group(1)}=REDACTED", scrubbed)


@dataclass(frozen=True)
class HttpClientOptions:
    timeout: float = 20.0
    user_agent: str = "langrank/0.1.0"
    retries: int = 3
    backoff_seconds: float = 0.5
    max_response_bytes: int = 10_000_000


class HttpClientFactory:
    """Builds retrying ``httpx`` clients and reads bytes/JSON with secret-safe errors.

    :ivar _options: Timeout, retry and size-cap policy.
    :ivar _transport: Optional injected transport (tests use ``httpx.MockTransport``).
    """

    def __init__(
        self,
        options: Optional[HttpClientOptions] = None,
        *,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        """Wire the client factory.

        :param options: Client policy; defaults to :class:`HttpClientOptions`.
        :param transport: Optional transport override for offline testing; never
            used to reach the network in production.
        """
        self._options = options or HttpClientOptions()
        self._transport = transport

    def build(self, *, follow_redirects: bool = True) -> httpx.Client:
        """Construct an ``httpx.Client`` honouring the configured policy.

        :param follow_redirects: Whether the client follows 3xx redirects; the
            JSON path disables this so a key-bearing request is never replayed to
            another host (SEC-2).
        :returns: A configured, not-yet-entered client.
        """
        return httpx.Client(
            timeout=self._options.timeout,
            headers={"User-Agent": self._options.user_agent},
            follow_redirects=follow_redirects,
            transport=self._transport,
        )

    def get_bytes(self, url: str) -> bytes:
        last_error: Optional[Exception] = None
        with self.build() as client:
            for attempt in range(self._options.retries):
                try:
                    response = client.get(url)
                    if response.status_code in _RETRYABLE_STATUS:
                        raise FetchError(f"temporary upstream status {response.status_code}")
                    response.raise_for_status()
                    return response.content
                except (httpx.HTTPError, FetchError) as exc:
                    last_error = exc
                    if attempt < self._options.retries - 1:
                        sleep(self._options.backoff_seconds * (2**attempt))
            assert last_error is not None
            raise (self.map_error(last_error) if isinstance(last_error, httpx.HTTPError) else last_error)

    def get_json(
        self,
        url: str,
        params: Optional[dict[str, str]] = None,
        *,
        allowed_host: Optional[str] = None,
    ) -> Any:
        """GET ``url`` with retry, size cap and secret-safe errors, returning parsed JSON.

        Secrets are passed only via ``params`` and never string-formatted into
        ``url`` (SEC-1). The request scheme must be HTTPS and, when
        ``allowed_host`` is given, the host must match exactly; redirects are not
        followed so a key is never replayed cross-host (SEC-2). The response body
        is read with a hard post-decompression byte ceiling (SEC-3).

        :param url: Absolute HTTPS URL, free of any secret query parameter.
        :param params: Query parameters (may include the API key) sent by ``httpx``.
        :param allowed_host: Expected ``netloc`` to pin the request to.
        :returns: The parsed JSON body.
        :raises FetchError: On non-HTTPS/off-host targets, redirects, oversized
            bodies, malformed JSON, or exhausted retries.
        """
        parsed = urlsplit(url)
        if parsed.scheme != "https":
            raise FetchError(f"refusing non-HTTPS request to {_scrub_url(url)}")
        if allowed_host is not None and parsed.netloc != allowed_host:
            raise FetchError(f"refusing request to unexpected host {parsed.netloc!r}")

        last_error: Optional[Exception] = None
        with self.build(follow_redirects=False) as client:
            for attempt in range(self._options.retries):
                try:
                    raw = self._read_capped(client, url, params)
                except (httpx.HTTPError, FetchError) as exc:
                    last_error = exc
                    if attempt < self._options.retries - 1:
                        sleep(self._options.backoff_seconds * (2**attempt))
                    continue
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    raise FetchError("Stack Exchange response body was not valid JSON") from None
            assert last_error is not None
            raise (self.map_error(last_error) if isinstance(last_error, httpx.HTTPError) else last_error)

    def _read_capped(
        self,
        client: httpx.Client,
        url: str,
        params: Optional[dict[str, str]],
    ) -> bytes:
        """Stream a GET response, aborting past the post-decompression byte ceiling.

        :param client: An entered client.
        :param url: Target URL (secret-free).
        :param params: Query parameters sent by ``httpx``.
        :returns: The full response body as bytes.
        :raises FetchError: On retryable status, a refused redirect, or overflow.
        """
        with client.stream("GET", url, params=params) as response:
            if response.status_code in _RETRYABLE_STATUS:
                raise FetchError(f"temporary upstream status {response.status_code}")
            if response.is_redirect:
                raise FetchError("refusing to follow redirect from api.stackexchange.com")
            response.raise_for_status()
            buffer = bytearray()
            for chunk in response.iter_bytes():
                buffer.extend(chunk)
                if len(buffer) > self._options.max_response_bytes:
                    raise FetchError(f"response exceeded {self._options.max_response_bytes} byte ceiling")
            return bytes(buffer)

    @staticmethod
    def map_error(error: httpx.HTTPError) -> FetchError:
        return FetchError(_scrub_message(str(error)))
