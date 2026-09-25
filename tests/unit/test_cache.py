from __future__ import annotations

import os
from pathlib import Path

import pytest

from langrank.errors import FetchError
from langrank.providers.common import load_cached_payload

_POISON = b'{"poisoned": true}'


def test_load_cached_payload_returns_newest_regular_file(tmp_path: Path) -> None:
    """Happy path: the newest matching regular file is replayed verbatim."""
    cache = tmp_path / "cache"
    cache.mkdir()
    older = cache / "demo-aaaaaaaaaaaa.json"
    newer = cache / "demo-bbbbbbbbbbbb.json"
    older.write_bytes(b'{"which": "older"}')
    newer.write_bytes(b'{"which": "newer"}')

    os.utime(older, (1_000, 1_000))
    os.utime(newer, (2_000, 2_000))

    payload = load_cached_payload(provider_id="demo", cache_dir=cache)

    assert payload.artifact is None
    assert payload.content == b'{"which": "newer"}'


# --- SEC-5: cache traversal / symlink defence ---------------------------------


def test_load_cached_payload_skips_symlinked_entry(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    outside = tmp_path / "outside-secret.json"
    outside.write_bytes(_POISON)
    link = cache / "demo-deadbeef0000.json"
    link.symlink_to(outside)

    # The symlink is the only candidate; it is skipped, so no artifact is found
    # and the poisoned content is never read back.
    with pytest.raises(FetchError) as excinfo:
        load_cached_payload(provider_id="demo", cache_dir=cache)

    assert "no cached artifact" in str(excinfo.value)


def test_load_cached_payload_rejects_out_of_tree_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    outside = tmp_path / "outside-secret.json"
    outside.write_bytes(_POISON)
    link = cache / "demo-deadbeef0000.json"
    link.symlink_to(outside)

    # Force the symlink guard off so the candidate reaches the containment check;
    # its resolved path escapes cache_dir and must therefore be rejected.
    monkeypatch.setattr(Path, "is_symlink", lambda self: False)

    with pytest.raises(FetchError) as excinfo:
        load_cached_payload(provider_id="demo", cache_dir=cache)

    assert "no cached artifact" in str(excinfo.value)


@pytest.mark.parametrize(
    "provider_id",
    ["../x", "a/b", "demo/../evil", "..", "UPPER", "with space", "dot.dot", ""],
)
def test_load_cached_payload_rejects_unsafe_provider_id(tmp_path: Path, provider_id: str) -> None:
    with pytest.raises(FetchError) as excinfo:
        load_cached_payload(provider_id=provider_id, cache_dir=tmp_path)

    assert "invalid provider id" in str(excinfo.value)
