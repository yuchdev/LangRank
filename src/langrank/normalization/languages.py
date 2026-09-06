from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches

from langrank.errors import UnknownLanguageError
from langrank.models import Language, LanguageAlias


@dataclass(frozen=True)
class CanonicalLanguage:
    canonical_name: str
    display_name: str
    aliases: tuple[str, ...]


class LanguageNormalizer:
    def __init__(self) -> None:
        self._languages = [
            CanonicalLanguage("python", "Python", ("py",)),
            CanonicalLanguage("c", "C", ()),
            CanonicalLanguage("c++", "C++", ("cpp", "cplusplus")),
            CanonicalLanguage("java", "Java", ()),
            CanonicalLanguage("javascript", "JavaScript", ("js",)),
            CanonicalLanguage("rust", "Rust", ()),
            CanonicalLanguage("go", "Go", ("golang",)),
            CanonicalLanguage("c#", "C#", ("c sharp", "csharp")),
            CanonicalLanguage("objective-c", "Objective-C", ("objective c",)),
            CanonicalLanguage("vb.net", "VB.NET", ("visual basic", "visual basic .net")),
            CanonicalLanguage("shell", "Shell", ("bash", "bash/shell")),
            CanonicalLanguage("c/c++", "C/C++", ("c-cpp",)),
        ]
        self._lookup = {}
        for language in self._languages:
            names = (language.canonical_name, language.display_name, *language.aliases)
            for name in names:
                self._lookup[self._normalize_key(name)] = language.canonical_name

    @staticmethod
    def _normalize_key(value: str) -> str:
        return "".join(char for char in value.lower().strip() if char.isalnum() or char in "+#/.")

    def resolve(self, value: str) -> str:
        key = self._normalize_key(value)
        if key in self._lookup:
            return self._lookup[key]
        suggestions = get_close_matches(
            value.lower(), [lang.canonical_name for lang in self._languages], n=3
        )
        raise UnknownLanguageError(value, suggestions)

    def languages(self) -> list[Language]:
        return [
            Language(
                id=item.canonical_name,
                canonical_name=item.canonical_name,
                display_name=item.display_name,
            )
            for item in self._languages
        ]

    def aliases(self) -> list[LanguageAlias]:
        aliases: list[LanguageAlias] = []
        for item in self._languages:
            names = {item.display_name, *item.aliases}
            for alias in sorted(names):
                aliases.append(
                    LanguageAlias(rating_id="", source_name=alias, language_id=item.canonical_name)
                )
        return aliases
