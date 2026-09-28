from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from langrank.errors import ProviderError
from langrank.models import FetchRequest
from langrank.providers.ieee_spectrum import DATA_PATH, IeeeSpectrumProvider

#: The exact curated-CSV header the bundled dataset and every ``langrank import``
#: CSV must carry (subtask 05 rejects a mismatch).
_EXPECTED_HEADER = "year,profile,rank,language,score,source_url,published_at,methodology_version"


@pytest.mark.parametrize("source", [None, "auto", "bundled"])
def test_ieee_fetch_reads_bundled_csv(tmp_path: Path, source: Optional[str]) -> None:
    """A supported source reads the bundled CSV byte-for-byte with no network."""
    provider = IeeeSpectrumProvider(tmp_path)
    payload = provider.fetch(FetchRequest(source=source))

    assert payload.content == DATA_PATH.read_bytes()
    assert payload.artifact is not None
    assert payload.artifact.url == "https://spectrum.ieee.org/top-programming-languages-2025"
    assert payload.artifact.metadata_json["mode"] == "bundled"
    assert payload.artifact.metadata_json["provenance"] == "manual_transcription"


def test_ieee_fetch_unknown_source_raises(tmp_path: Path) -> None:
    """An unsupported ``--source`` is rejected - there is no network source to guess."""
    provider = IeeeSpectrumProvider(tmp_path)
    with pytest.raises(ProviderError):
        provider.fetch(FetchRequest(source="scrape"))


def test_ieee_bundled_csv_header(tmp_path: Path) -> None:
    """The bundled CSV carries the exact spec header the parser expects."""
    provider = IeeeSpectrumProvider(tmp_path)
    payload = provider.fetch(FetchRequest())

    first_line = payload.content.decode("utf-8").splitlines()[0]
    assert first_line == _EXPECTED_HEADER
