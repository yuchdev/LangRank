"""Unit tests for the JetBrains raw-data import (subtask 04.0/06).

Covers the spec behaviours (unweighted respondent-share math, ``-raw`` derived
metrics, year detection, non-respondent exclusion) and the HIGH threat-model
requirements JB-SEC-1..7 and JB-SEC-9
(``docs/security/2026-09-26-jetbrains-import.md``).

Every fixture here is a **tiny synthetic** CSV that only mimics the real 2024 dump's
column layout (one ``<parent>::<Option label>`` column per multi-select answer, the
option label as the selected-cell value, empty otherwise). No verbatim JetBrains
response row is committed (JB-SEC-5).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from langrank.errors import ParseError
from langrank.providers import jetbrains
from langrank.providers.base import SupportsRawImport
from langrank.providers.jetbrains import (
    JetBrainsProvider,
    _detect_survey_year,
    _parse_raw,
)
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
)

#: A PII-like free-text value dropped into a non-language column of every fixture.
#: JB-SEC-4/JB-SEC-9 tests assert it never reaches a record, an observation, or an
#: error message.
_PII = "alice.secret@example.com wrote a long confession"

#: Synthetic 2024-layout header: two non-language columns (one free-text), the three
#: language-question multi-select groups with ``::`` per-option columns. ``Other`` and
#: ``I don't use programming languages`` are JetBrains meta-answers.
_HEADER = [
    "respondent_id",
    "employment_status",
    "proglang::Python",
    "proglang::Java",
    "proglang::C++",
    "proglang::Other",
    "proglang::I don't use programming languages",
    "feedback_freetext",
    "primary_lang::Python",
    "primary_lang::Java",
    "adopt_proglang::Rust",
    "adopt_proglang::Go",
]


def _row(
    respondent_id: str,
    *,
    prog: tuple[str, ...] = (),
    primary: tuple[str, ...] = (),
    adopt: tuple[str, ...] = (),
    freetext: str = "",
) -> list[str]:
    """Build one synthetic respondent row: a cell holds the option label if selected."""

    def cell(label: str, selected: tuple[str, ...]) -> str:
        return label if label in selected else ""

    return [
        respondent_id,
        "Employed",
        cell("Python", prog),
        cell("Java", prog),
        cell("C++", prog),
        cell("Other", prog),
        cell("I don't use programming languages", prog),
        freetext,
        cell("Python", primary),
        cell("Java", primary),
        cell("Rust", adopt),
        cell("Go", adopt),
    ]


#: Six synthetic respondents. R4 selects nothing anywhere (a full non-respondent that
#: must fall out of every denominator); R6 selects only meta-answers.
_ROWS: list[list[str]] = [
    _row("1", prog=("Python", "Java"), primary=("Python",), adopt=("Rust",), freetext=_PII),
    _row("2", prog=("Python",), primary=("Python",), adopt=("Rust", "Go")),
    _row("3", prog=("Java", "C++")),
    _row("4"),
    _row("5", prog=("Python", "C++"), primary=("Java",)),
    _row("6", prog=("Other", "I don't use programming languages")),
]


def _csv_bytes(header: list[str] = _HEADER, rows: list[list[str]] = _ROWS) -> bytes:
    """Serialise a synthetic header + rows to UTF-8 CSV bytes (proper quoting)."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _write(tmp_path: Path, content: bytes, name: str = "raw.csv") -> Path:
    """Write ``content`` to a throwaway file and return its path."""
    path = tmp_path / name
    path.write_bytes(content)
    return path


def _record(records: list, metric_id: str, language: str):
    """Return the single record for ``(metric_id, language)``."""
    return next(r for r in records if r.metric_id == metric_id and r.language == language)


# --------------------------------------------------------------------------- spec


def test_jetbrains_raw_share_math() -> None:
    """Unweighted per-language shares match the hand-computed counts / denominators."""
    records = _parse_raw(_csv_bytes())

    used = METRIC_USED_LAST_12_MONTHS + "-raw"
    # proglang denominator = R1,R2,R3,R5,R6 = 5 (R4 selected nothing).
    assert _record(records, used, "Python").value == pytest.approx(60.0)  # R1,R2,R5
    assert _record(records, used, "Java").value == pytest.approx(40.0)  # R1,R3
    assert _record(records, used, "C++").value == pytest.approx(40.0)  # R3,R5
    assert _record(records, used, "Python").metadata["denominator"] == 5
    assert _record(records, used, "Python").metadata["respondent_count"] == 3

    primary = METRIC_PRIMARY_LANGUAGE + "-raw"
    # primary denominator = R1,R2,R5 = 3.
    assert _record(records, primary, "Python").value == pytest.approx(200 / 3)  # 2/3
    assert _record(records, primary, "Java").value == pytest.approx(100 / 3)  # 1/3

    adopt = METRIC_PLANNED_ADOPTION + "-raw"
    # adopt denominator = R1,R2 = 2.
    assert _record(records, adopt, "Rust").value == pytest.approx(100.0)  # R1,R2
    assert _record(records, adopt, "Go").value == pytest.approx(50.0)  # R2


def test_jetbrains_raw_is_derived(tmp_path: Path) -> None:
    """Raw observations are derived, carry the method, and use distinct -raw IDs."""
    provider = JetBrainsProvider(tmp_path)
    observations = provider.normalize(provider.import_path(_write(tmp_path, _csv_bytes())))

    assert observations, "expected derived observations"
    assert all(o.is_derived for o in observations)
    assert all(o.derivation_method == "unweighted_respondent_share" for o in observations)
    assert all(o.metric_id.endswith("-raw") for o in observations)
    # Success criterion: raw metric IDs never collide with the published family.
    assert not (set(jetbrains.PUBLISHED_METRICS) & {o.metric_id for o in observations})
    python = next(o for o in observations if o.language_id == "python" and o.metric_id.startswith("jetbrains-used"))
    assert python.sample_size == 5  # denominator stored as sample_size (JB-SEC-6)
    assert python.metadata_json["denominator"] == 5
    assert python.source_document_id == "jetbrains-devecosystem-2024-raw"
    # 2024 used-in-12-months wording is verified verbatim in the registry.
    assert python.metadata_json["wording_verified"] is True


def test_jetbrains_raw_year_detection() -> None:
    """Year is detected from the header prefixes; a header matching two years raises."""
    assert _detect_survey_year(_HEADER) == 2024

    # A header carrying no known language-question prefix cannot be attributed.
    with pytest.raises(ParseError, match="could not detect"):
        _detect_survey_year(["respondent_id", "employment_status"])

    # Two registry years sharing a prefix fingerprint -> ambiguous, refuse to guess.
    ambiguous = {2024: {"used": "proglang::"}, 2099: {"used": "proglang::"}}
    with pytest.raises(ParseError, match="ambiguous"):
        _detect_survey_year(_HEADER, year_prefixes=ambiguous)


def test_jetbrains_raw_non_respondents_excluded() -> None:
    """The all-blank respondent (R4) is in no denominator; a meta-only answer counts."""
    records = _parse_raw(_csv_bytes())

    used = METRIC_USED_LAST_12_MONTHS + "-raw"
    # Denominator is 5 (R1,R2,R3,R5,R6), never 6: R4 selected nothing at all.
    assert _record(records, used, "Python").metadata["denominator"] == 5
    # R6 answered the question with meta-answers only, so it is counted in the
    # denominator, but those meta-answers normalize to no observation.
    assert _record(records, used, "Other").metadata["respondent_count"] == 1


# ---------------------------------------------------------------- threat model


def test_jb_sec_1_oversized_file_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JB-SEC-1: a file over the byte cap is refused before it is parsed."""
    monkeypatch.setattr(jetbrains, "_MAX_IMPORT_BYTES", 8)
    provider = JetBrainsProvider(tmp_path)
    with pytest.raises(ParseError, match="over the"):
        provider.import_path(_write(tmp_path, _csv_bytes()))


def test_jb_sec_1_row_cap_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JB-SEC-1: a file exceeding the row cap is refused while streaming."""
    monkeypatch.setattr(jetbrains, "_MAX_IMPORT_ROWS", 2)
    provider = JetBrainsProvider(tmp_path)
    with pytest.raises(ParseError, match="row cap"):
        provider.import_path(_write(tmp_path, _csv_bytes()))


def test_jb_sec_1_import_never_touches_cache(tmp_path: Path) -> None:
    """JB-SEC-1/5: streaming import reads the file in place, never caching a copy."""
    cache_dir = tmp_path / "cache"
    provider = JetBrainsProvider(cache_dir)
    provider.import_path(_write(tmp_path, _csv_bytes()))
    # The provider never wrote the raw bytes (or any copy) under the cache dir.
    assert not cache_dir.exists()


def test_jb_sec_2_zip_rejected(tmp_path: Path) -> None:
    """JB-SEC-2: a .zip (by magic bytes) is refused with an extract-it message."""
    zip_bytes = b"PK\x03\x04" + b"\x00" * 64
    with pytest.raises(ParseError, match="extract"):
        _parse_raw(zip_bytes)
    provider = JetBrainsProvider(tmp_path)
    with pytest.raises(ParseError, match="extract"):
        provider.import_path(_write(tmp_path, zip_bytes, name="RawData.zip"))


def test_jb_sec_3_non_utf8_rejected_and_bom_tolerated() -> None:
    """JB-SEC-3: non-UTF-8 bytes raise; a UTF-8 BOM is tolerated."""
    header = [*_HEADER]
    header[0] = "respondent_id_ñ"
    latin1 = _csv_bytes(header=header).decode("utf-8").encode("latin-1")
    with pytest.raises(ParseError):
        _parse_raw(latin1)

    bom = b"\xef\xbb\xbf" + _csv_bytes()
    assert _parse_raw(bom), "BOM-prefixed content must still parse"


def test_jb_sec_3_field_size_limit_enforced_and_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    """JB-SEC-3: an over-limit field is rejected and the global limit is restored."""
    # Small enough to reject the giant field below, large enough for the longest
    # legitimate header/label field (~48 chars).
    monkeypatch.setattr(jetbrains, "_CSV_FIELD_SIZE_LIMIT", 200)
    before = csv.field_size_limit()
    giant_row = _row("7", prog=("Python",), freetext="x" * 500)
    content = _csv_bytes(rows=[*_ROWS, giant_row])

    with pytest.raises(ParseError, match="malformed CSV line") as excinfo:
        _parse_raw(content)

    # The giant free-text cell is never echoed into the error (JB-SEC-9).
    assert "x" * 500 not in str(excinfo.value)
    # The process-wide limit is restored, so other providers are unaffected.
    assert csv.field_size_limit() == before


def test_jb_sec_3_malformed_row_names_index_only() -> None:
    """JB-SEC-3/9: a row of unexpected width raises, naming the index, not the cell."""
    short_row = ["1", "Employed"]  # far fewer than the header's 12 columns
    content = _csv_bytes(rows=[short_row])
    with pytest.raises(ParseError, match="row 2 has 2 fields") as excinfo:
        _parse_raw(content)
    assert "Employed" not in str(excinfo.value)


def test_jb_sec_4_freetext_never_stored(tmp_path: Path) -> None:
    """JB-SEC-4: only the language-question columns are read; free-text never persists."""
    provider = JetBrainsProvider(tmp_path)
    records = provider.import_path(_write(tmp_path, _csv_bytes()))
    observations = provider.normalize(records)

    # The PII free-text appears in no source string, no value, no metadata anywhere.
    assert all(_PII not in r.language for r in records)
    assert all(_PII not in str(r.metadata) for r in records)
    assert all(_PII not in o.source_language_name for o in observations)
    assert all(_PII not in str(o.metadata_json) for o in observations)
    # Only the three language questions produced records - no employment/free-text column.
    assert {r.metric_id for r in records} <= {
        METRIC_USED_LAST_12_MONTHS + "-raw",
        METRIC_PRIMARY_LANGUAGE + "-raw",
        METRIC_PLANNED_ADOPTION + "-raw",
    }


def test_jb_sec_6_denominator_and_distinct_series(tmp_path: Path) -> None:
    """JB-SEC-6: raw records carry the denominator and never share a published series."""
    provider = JetBrainsProvider(tmp_path)
    records = provider.import_path(_write(tmp_path, _csv_bytes()))

    assert all(r.metadata["denominator"] > 0 for r in records)
    assert all(r.metadata["provenance"] == "raw_respondent_share" for r in records)
    assert all(r.metric_id.endswith("-raw") for r in records)
    # No raw record's metric ID equals any published metric ID (distinct series).
    assert not ({r.metric_id for r in records} & set(jetbrains.PUBLISHED_METRICS))


def test_jb_sec_7_raw_fetch_stays_network_free() -> None:
    """JB-SEC-7: raw acquisition is import-only; fetch() never runs the raw path."""
    provider = JetBrainsProvider(Path("/tmp/does-not-matter"))
    # The provider exposes the streaming import capability for the CLI to dispatch to.
    assert isinstance(provider, SupportsRawImport)
    # fetch(--source raw-data) does not silently download; raw data only enters via import.
    from langrank.models import FetchRequest

    with pytest.raises(NotImplementedError):
        provider.fetch(FetchRequest(source="raw-data"))


def test_capability_is_opt_in() -> None:
    """The raw-import capability is structural: a bare object is not misdetected."""

    class _Bare:
        provider_id = "bare"

    assert not isinstance(_Bare(), SupportsRawImport)


def test_jb_sec_1_single_huge_line_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    legitimate = _csv_bytes()
    longest = max(len(line) for line in legitimate.decode("utf-8").splitlines(keepends=True))
    monkeypatch.setattr(jetbrains, "_MAX_LINE_CHARS", longest)
    # Every real line fits the cap; only the appended crafted line exceeds it.
    JetBrainsProvider(tmp_path).import_path(_write(tmp_path, legitimate, name="ok.csv"))
    crafted = legitimate + b"x" * (longest + 1) + b"\n"
    with pytest.raises(ParseError, match="character cap") as excinfo:
        JetBrainsProvider(tmp_path).import_path(_write(tmp_path, crafted))
    assert "xxxx" not in str(excinfo.value)


def test_jb_sec_1_hyper_wide_header_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jetbrains, "_MAX_COLUMNS", 3)
    path = _write(tmp_path, _csv_bytes())
    with pytest.raises(ParseError, match="columns"):
        JetBrainsProvider(tmp_path).import_path(path)


def test_jb_sec_1_non_regular_file_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-file.csv"
    directory.mkdir()
    with pytest.raises(ParseError, match="not a regular file"):
        JetBrainsProvider(tmp_path).import_path(directory)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"\xff\xfe\xfd not utf-8\n", id="non-utf8"),
        pytest.param(b"unrelated,columns\n1,2\n", id="no-detectable-year"),
    ],
)
def test_jb_sec_3_field_size_limit_restored_on_error_paths(tmp_path: Path, content: bytes) -> None:
    before = csv.field_size_limit()
    with pytest.raises(ParseError):
        JetBrainsProvider(tmp_path).import_path(_write(tmp_path, content))
    assert csv.field_size_limit() == before


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_bounded_lines_accepts_line_exactly_at_cap(monkeypatch: pytest.MonkeyPatch, terminator: str) -> None:
    monkeypatch.setattr(jetbrains, "_MAX_LINE_CHARS", 8)
    at_cap = "a" * 8 + terminator
    assert list(jetbrains._bounded_lines(io.StringIO(at_cap + "b" + terminator))) == [at_cap, "b" + terminator]
    with pytest.raises(ParseError, match="character cap"):
        list(jetbrains._bounded_lines(io.StringIO("a" * 9 + terminator)))
