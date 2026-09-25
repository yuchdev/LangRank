from __future__ import annotations

from pathlib import Path

import pytest

from langrank.errors import ParseError, ProviderError
from langrank.models import FetchRequest, Granularity
from langrank.providers.github import (
    METRIC_IG_PUSHERS,
    METRIC_OCTOVERSE_RANK,
    OCTOVERSE_CHART_SOURCE,
    GitHubProvider,
    GitHubSource,
    OctoverseBasis,
    _parse_octoverse,
)

#: A minimal well-formed curated CSV covering two distinct ranking bases.
_CSV = (
    "year,rank,language,ranking_basis,source_url,published_at\n"
    "2024,1,Python,contributors,https://example.invalid/octoverse-2024/,2024-10-29\n"
    "2024,2,JavaScript,contributors,https://example.invalid/octoverse-2024/,2024-10-29\n"
    "2025,1,TypeScript,monthly_contributors,https://example.invalid/octoverse-2025/,2025-10-28\n"
).encode("utf-8")


def _provider(tmp_path: Path) -> GitHubProvider:
    """Build a provider rooted at a throwaway cache dir (no network for Octoverse)."""
    return GitHubProvider(tmp_path)


def test_octoverse_parse_ranks() -> None:
    """Parsing yields one annual record per row with the ranking basis in metadata."""
    records = _parse_octoverse(_CSV)

    assert [(r.period_start.year, r.rank, r.language) for r in records] == [
        (2024, 1, "Python"),
        (2024, 2, "JavaScript"),
        (2025, 1, "TypeScript"),
    ]
    first = records[0]
    assert first.metric_id == METRIC_OCTOVERSE_RANK
    assert first.granularity is Granularity.YEAR
    assert first.value == 1.0
    assert first.period_label == "2024"
    assert first.metadata["ranking_basis"] == OctoverseBasis.CONTRIBUTORS.value
    assert first.metadata["provenance"] == "manual_curation"
    assert records[-1].metadata["ranking_basis"] == OctoverseBasis.MONTHLY_CONTRIBUTORS.value


def test_octoverse_methodology_notes_per_basis(tmp_path: Path) -> None:
    """The bundled dataset yields exactly one methodology note per distinct basis."""
    provider = _provider(tmp_path)
    records = _parse_octoverse(provider._octoverse_data_path.read_bytes())
    distinct_bases = {str(record.metadata["ranking_basis"]) for record in records}

    octoverse_notes = [
        note for note in provider.metadata().methodology_notes if note.methodology_version.startswith("octoverse-")
    ]

    assert len(octoverse_notes) == len(distinct_bases)
    versions = {note.methodology_version for note in octoverse_notes}
    assert versions == {f"octoverse-{basis}-v1" for basis in distinct_bases}
    for note in octoverse_notes:
        assert note.valid_from is not None
        assert note.valid_to is not None
        assert note.valid_from <= note.valid_to


def test_octoverse_values_not_derived(tmp_path: Path) -> None:
    """Published ranks normalize to raw observations: is_derived is False."""
    provider = _provider(tmp_path)
    records = _parse_octoverse(_CSV)

    observations = provider.normalize(records)

    assert observations, "expected mapped observations"
    assert all(obs.is_derived is False for obs in observations)
    assert all(obs.derivation_method is None for obs in observations)
    assert all(obs.metric_id == METRIC_OCTOVERSE_RANK for obs in observations)
    python = next(obs for obs in observations if obs.language_id == "python")
    assert python.rank == 1
    assert python.source_published_at is not None
    assert python.source_document_id == "https://example.invalid/octoverse-2024/"


def test_octoverse_chart_source_refused(tmp_path: Path) -> None:
    """Requesting chart-pixel extraction is refused with a ProviderError."""
    provider = _provider(tmp_path)
    with pytest.raises(ProviderError, match="chart"):
        provider.fetch(FetchRequest(source=OCTOVERSE_CHART_SOURCE))


def test_octoverse_fetch_parse_roundtrip_is_offline(tmp_path: Path) -> None:
    """fetch() reads the bundled CSV with zero network and parse() routes to Octoverse."""
    provider = _provider(tmp_path)

    payload = provider.fetch(FetchRequest(source=GitHubSource.OCTOVERSE.value))
    assert payload.artifact is not None
    assert payload.artifact.metadata_json["variant"] == GitHubSource.OCTOVERSE.value
    assert payload.artifact.metadata_json["provenance"] == "manual_curation"

    records = provider.parse(payload)
    assert records
    assert all(record.metric_id == METRIC_OCTOVERSE_RANK for record in records)
    assert all(record.granularity is Granularity.YEAR for record in records)


def test_octoverse_unmapped_language_recorded_non_language_suppressed(tmp_path: Path) -> None:
    """An unknown name goes to last_unmapped; a documented non-language is silent."""
    provider = _provider(tmp_path)
    csv = (
        "year,rank,language,ranking_basis,source_url,published_at\n"
        "2024,1,Python,contributors,https://example.invalid/o/,2024-10-29\n"
        "2024,2,Jupyter Notebook,contributors,https://example.invalid/o/,2024-10-29\n"
        "2024,3,Brainfuck,contributors,https://example.invalid/o/,2024-10-29\n"
    ).encode("utf-8")

    observations = provider.normalize(_parse_octoverse(csv))

    assert {obs.language_id for obs in observations} == {"python"}
    assert provider.last_unmapped == ["Brainfuck"]


def test_octoverse_parse_missing_column_raises() -> None:
    """A missing required column raises ParseError naming the column."""
    csv = b"year,rank,language,ranking_basis,source_url\n2024,1,Python,contributors,https://x.invalid/\n"
    with pytest.raises(ParseError, match="published_at"):
        _parse_octoverse(csv)


@pytest.mark.parametrize(
    "bad_row",
    [
        "2024,0,Python,contributors,https://x.invalid/,2024-10-29",
        "2024,-1,Python,contributors,https://x.invalid/,2024-10-29",
        "2024,x,Python,contributors,https://x.invalid/,2024-10-29",
        "1999,1,Python,contributors,https://x.invalid/,2024-10-29",
        "2024,1,Python,weekly_stargazers,https://x.invalid/,2024-10-29",
    ],
)
def test_octoverse_parse_rejects_malformed_cells(bad_row: str) -> None:
    """Non-positive rank, non-numeric rank, implausible year, unknown basis all fail."""
    csv = ("year,rank,language,ranking_basis,source_url,published_at\n" + bad_row + "\n").encode("utf-8")
    with pytest.raises(ParseError):
        _parse_octoverse(csv)


def test_octoverse_normalize_refuses_mixed_variants(tmp_path: Path) -> None:
    """Mixing Octoverse and Innovation Graph records is refused, never conflated."""
    provider = _provider(tmp_path)
    octoverse = _parse_octoverse(_CSV)
    ig_like = octoverse[0].__class__(
        rating_id=octoverse[0].rating_id,
        metric_id=METRIC_IG_PUSHERS,
        language="Python",
        period_start=octoverse[0].period_start,
        period_end=octoverse[0].period_end,
        period_label=octoverse[0].period_label,
        granularity=Granularity.QUARTER,
        rank=None,
        value=1.0,
        unit="count",
        source_url="https://x.invalid/",
    )
    with pytest.raises(ProviderError, match="mix variants"):
        provider.normalize([*octoverse, ig_like])
