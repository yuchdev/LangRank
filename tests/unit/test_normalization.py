from __future__ import annotations

import csv
from pathlib import Path

import pytest

from langrank.db import Database
from langrank.errors import UnknownLanguageError
from langrank.normalization import (
    GITHUB_NON_LANGUAGES,
    IEEE_UNTRACKED_LABELS,
    JETBRAINS_NON_LANGUAGE_ANSWERS,
    LanguageNormalizer,
)

#: JetBrains survey answer labels that must resolve under ``rating_id="jetbrains"``.
#: Only labels needing a scoped alias appear here; plain names (``Python``,
#: ``Kotlin`` ...) already resolve globally against the shared catalog.
JETBRAINS_ALIASES: tuple[tuple[str, str], ...] = (
    ("Shell scripting languages", "shell"),
    ("SQL(PL/SQL, T-SQL and other programming extensions of SQL)", "sql"),
    ("C/C++", "c-cpp"),
)

#: JetBrains meta-answers and markup that ``try_resolve`` must reject outright
#: (``Visual Basic`` is handled separately - see the test - because the bootstrap
#: TIOBE alias still resolves it globally to ``vb.net``).
JETBRAINS_UNMAPPED_ANSWERS: tuple[str, ...] = (
    "HTML / CSS",
    "Other",
    "I don't use programming languages",
)

#: GitHub Linguist display names that must resolve under ``rating_id="github"``.
GITHUB_LINGUIST_ALIASES: tuple[tuple[str, str], ...] = (
    ("C++", "c++"),
    ("C#", "c#"),
    ("Shell", "shell"),
    ("PowerShell", "powershell"),
    ("Visual Basic .NET", "vb.net"),
    ("Objective-C", "objective-c"),
)

#: IEEE Spectrum labels that must resolve under ``rating_id="ieee-spectrum"``.
IEEE_SPECTRUM_ALIASES: tuple[tuple[str, str], ...] = (
    ("Shell", "shell"),
    ("Assembly", "assembly"),
    ("SQL", "sql"),
)

#: Known IEEE Spectrum "Top Programming Languages" labels used to prove every
#: published label either resolves or is explicitly untracked. Kept in-test
#: because the curated dataset (``providers/data/ieee_spectrum.csv``) lands in a
#: later subtask; the test also folds in the real CSV labels once it exists.
IEEE_KNOWN_LABELS: tuple[str, ...] = (
    "Python",
    "Java",
    "C++",
    "C",
    "C#",
    "JavaScript",
    "Go",
    "Rust",
    "SQL",
    "Shell",
    "Assembly",
    "PHP",
    "Ruby",
    "R",
    "Swift",
    "Kotlin",
    "Scala",
    "MATLAB",
    "Fortran",
    "Cobol",
    "HTML",
    "Arduino",
    "Verilog",
    "VHDL",
    "Visual Basic",
)

#: Location of the curated IEEE dataset once subtask 04 adds it.
IEEE_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "langrank" / "providers" / "data" / "ieee_spectrum.csv"
)


def _ieee_dataset_labels() -> set[str]:
    """Collect IEEE labels from the curated CSV when present, else the known set.

    :returns: Distinct IEEE language labels to check for accountability.
    """
    labels = set(IEEE_KNOWN_LABELS)
    if IEEE_DATASET_PATH.exists():
        with IEEE_DATASET_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                label = (row.get("language") or row.get("source_name") or "").strip()
                if label:
                    labels.add(label)
    return labels


#: Every global alias that existed before rating-scoped aliases were introduced,
#: paired with the canonical language it must keep resolving to.
BOOTSTRAP_ALIASES: tuple[tuple[str, str], ...] = (
    ("Python", "python"),
    ("py", "python"),
    ("C", "c"),
    ("C++", "c++"),
    ("cpp", "c++"),
    ("cplusplus", "c++"),
    ("Java", "java"),
    ("JavaScript", "javascript"),
    ("js", "javascript"),
    ("Rust", "rust"),
    ("Go", "go"),
    ("golang", "go"),
    ("C#", "c#"),
    ("c sharp", "c#"),
    ("csharp", "c#"),
    ("Objective-C", "objective-c"),
    ("objective c", "objective-c"),
    ("VB.NET", "vb.net"),
    ("visual basic", "vb.net"),
    ("visual basic .net", "vb.net"),
    ("Shell", "shell"),
    ("bash", "shell"),
    ("bash/shell", "shell"),
    ("C/C++", "c-cpp"),
    ("c/c++", "c-cpp"),
)


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("cpp", "c++"),
        ("C++", "c++"),
        ("JS", "javascript"),
        ("Bash/Shell", "shell"),
        ("C/C++", "c-cpp"),
    ],
)
def test_language_alias_resolution(alias: str, canonical: str) -> None:
    normalizer = LanguageNormalizer()
    assert normalizer.resolve(alias) == canonical


def test_unknown_language_suggests_close_match() -> None:
    normalizer = LanguageNormalizer()
    with pytest.raises(UnknownLanguageError):
        normalizer.resolve("cplusplusx")


def test_resolve_rating_scoped_alias_wins_over_global() -> None:
    normalizer = LanguageNormalizer()

    # The Stack Overflow c# tag resolves under the rating scope.
    assert normalizer.resolve("c#", rating_id="stackoverflow-tags") == "c#"

    # A rating-scoped-only synonym resolves only when the rating is supplied,
    # proving the scoped table is consulted ahead of (and beyond) the global one.
    assert normalizer.resolve("objc", rating_id="stackoverflow-tags") == "objective-c"
    assert normalizer.try_resolve("objc") is None


def test_try_resolve_returns_none_for_unknown() -> None:
    normalizer = LanguageNormalizer()
    assert normalizer.try_resolve("brainfuck") is None
    assert normalizer.try_resolve("brainfuck", rating_id="stackoverflow-tags") is None


def test_bootstrap_aliases_unchanged() -> None:
    normalizer = LanguageNormalizer()
    for alias, canonical in BOOTSTRAP_ALIASES:
        assert normalizer.resolve(alias) == canonical


def test_resolve_r_is_unambiguous() -> None:
    normalizer = LanguageNormalizer()
    assert normalizer.resolve("R") == "r"


def test_new_catalog_languages_present() -> None:
    normalizer = LanguageNormalizer()
    ids = {language.id for language in normalizer.languages()}
    expected = {
        "typescript",
        "kotlin",
        "swift",
        "php",
        "ruby",
        "r",
        "scala",
        "dart",
        "lua",
        "perl",
        "haskell",
        "elixir",
        "julia",
        "matlab",
        "sql",
        "assembly",
        "groovy",
        "powershell",
        "zig",
        "fortran",
        "cobol",
        "ada",
        "delphi",
    }
    assert expected <= ids


def test_github_linguist_aliases_resolve() -> None:
    normalizer = LanguageNormalizer()
    for name, canonical in GITHUB_LINGUIST_ALIASES:
        assert normalizer.resolve(name, rating_id="github") == canonical


def test_github_non_languages_not_mapped() -> None:
    normalizer = LanguageNormalizer()
    assert normalizer.try_resolve("Jupyter Notebook", rating_id="github") is None
    for name in GITHUB_NON_LANGUAGES:
        assert normalizer.try_resolve(name, rating_id="github") is None


def test_ieee_aliases_resolve() -> None:
    normalizer = LanguageNormalizer()
    for name, canonical in IEEE_SPECTRUM_ALIASES:
        assert normalizer.resolve(name, rating_id="ieee-spectrum") == canonical


def test_ieee_dataset_labels_all_accounted_for() -> None:
    normalizer = LanguageNormalizer()
    for label in _ieee_dataset_labels():
        accounted = (
            label in IEEE_UNTRACKED_LABELS or normalizer.try_resolve(label, rating_id="ieee-spectrum") is not None
        )
        assert accounted, f"IEEE label {label!r} neither resolves nor is listed in IEEE_UNTRACKED_LABELS"


def test_ieee_untracked_labels_expected_contents() -> None:
    assert IEEE_UNTRACKED_LABELS == frozenset(
        {
            "HTML",
            "Arduino",
            "Verilog",
            "VHDL",
            "Visual Basic",
            "Cuda",
            "WebAssembly",
            "LabView",
            "Ladder Logic",
            "Pascal/Delphi",
        }
    )


def test_jetbrains_aliases_resolve() -> None:
    normalizer = LanguageNormalizer()
    for name, canonical in JETBRAINS_ALIASES:
        assert normalizer.resolve(name, rating_id="jetbrains") == canonical


def test_jetbrains_non_language_answers_unmapped() -> None:
    normalizer = LanguageNormalizer()
    # Markup and survey meta-answers never resolve as a language.
    for answer in JETBRAINS_UNMAPPED_ANSWERS:
        assert answer in JETBRAINS_NON_LANGUAGE_ANSWERS
        assert normalizer.try_resolve(answer, rating_id="jetbrains") is None

    # Classic Visual Basic resolves to ``vb.net`` via the bootstrap TIOBE alias,
    # so the provider must consult ``JETBRAINS_NON_LANGUAGE_ANSWERS`` *before*
    # resolving (mirroring ``IEEE_UNTRACKED_LABELS``); it is listed to be skipped,
    # not mapped, and must not be folded into ``vb.net`` for this milestone.
    assert "Visual Basic" in JETBRAINS_NON_LANGUAGE_ANSWERS


def test_jetbrains_combined_answer_not_split() -> None:
    normalizer = LanguageNormalizer()
    # A combined C/C++ answer maps to the single ``c-cpp`` canonical language and
    # is never split into ``c`` and ``c++``.
    assert normalizer.resolve("C/C++", rating_id="jetbrains") == "c-cpp"


def test_jetbrains_non_language_answers_expected_contents() -> None:
    assert JETBRAINS_NON_LANGUAGE_ANSWERS == frozenset(
        {
            "HTML / CSS",
            "Visual Basic",
            "Other",
            "I don't use programming languages",
        }
    )


def test_seed_languages_persists_rating_scoped_alias(database: Database) -> None:
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT rating_id, source_name, language_id FROM language_aliases WHERE rating_id != ''"
        ).fetchall()

    assert rows, "expected at least one rating-scoped alias to be persisted"
    scoped = {(row["rating_id"], row["source_name"]): row["language_id"] for row in rows}
    assert scoped[("stackoverflow-tags", "c#")] == "c#"
    assert all(row["rating_id"] for row in rows)
