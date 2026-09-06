from __future__ import annotations

import pytest

from langrank.errors import UnknownLanguageError
from langrank.normalization import LanguageNormalizer


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [("cpp", "c++"), ("C++", "c++"), ("JS", "javascript"), ("Bash/Shell", "shell")],
)
def test_language_alias_resolution(alias: str, canonical: str) -> None:
    normalizer = LanguageNormalizer()
    assert normalizer.resolve(alias) == canonical


def test_unknown_language_suggests_close_match() -> None:
    normalizer = LanguageNormalizer()
    with pytest.raises(UnknownLanguageError):
        normalizer.resolve("cplusplusx")
