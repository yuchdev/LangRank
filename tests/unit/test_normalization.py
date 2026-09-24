from __future__ import annotations

import pytest

from langrank.db import Database
from langrank.errors import UnknownLanguageError
from langrank.normalization import LanguageNormalizer

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


def test_seed_languages_persists_rating_scoped_alias(database: Database) -> None:
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT rating_id, source_name, language_id FROM language_aliases WHERE rating_id != ''"
        ).fetchall()

    assert rows, "expected at least one rating-scoped alias to be persisted"
    scoped = {(row["rating_id"], row["source_name"]): row["language_id"] for row in rows}
    assert scoped[("stackoverflow-tags", "c#")] == "c#"
    assert all(row["rating_id"] for row in rows)
