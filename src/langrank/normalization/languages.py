from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import get_close_matches
from typing import Optional

from langrank.errors import ConfigurationError, UnknownLanguageError
from langrank.models import Language, LanguageAlias


@dataclass(frozen=True)
class CanonicalLanguage:
    """A canonical programming language plus its global, rating-agnostic aliases.

    :ivar canonical_name: Stable identifier used as the ``language_id``.
    :ivar display_name: Human-facing name.
    :ivar aliases: Additional global source names that resolve to this language.
    """

    canonical_name: str
    display_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class RatingAlias:
    """A source name that resolves to a canonical language only within one rating.

    Rating-scoped aliases take precedence over global aliases so that, e.g., the
    Stack Overflow tag ``c#`` and PYPL's ``C/C++`` can be disambiguated per source.

    :ivar rating_id: Rating the alias applies to (e.g. ``stackoverflow-tags``).
    :ivar source_name: Raw source name as published by the rating.
    :ivar canonical_name: Canonical language the source name maps to.
    :ivar valid_from: Optional first date the mapping is valid (metadata only).
    :ivar valid_to: Optional last date the mapping is valid (metadata only, never
        rewrites history - a past ``valid_to`` still resolves).
    :ivar notes: Optional free-form provenance note.
    """

    rating_id: str
    source_name: str
    canonical_name: str
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


#: GitHub Linguist "language" names that are markup, config, data, or notebook
#: formats rather than programming languages tracked by this project. They are
#: deliberately left unmapped; a genuinely new (unlisted) Linguist name should
#: still raise an ``unmapped_language`` warning downstream, so this set exists to
#: suppress the warning only for these documented exclusions.
GITHUB_NON_LANGUAGES: frozenset[str] = frozenset(
    {
        "Jupyter Notebook",
        "HCL",
        "Dockerfile",
        "Makefile",
        "HTML",
        "CSS",
    }
)


#: IEEE Spectrum "Top Programming Languages" labels that are deliberately not
#: tracked in this project's canonical catalog. ``HTML`` is markup; ``Arduino``,
#: ``Verilog`` and ``VHDL`` are a board dialect and two hardware-description
#: languages rather than general-purpose programming languages (2026-09-25 user
#: ruling, recorded in ``docs/roadmap/0001-new-rating-providers/status.md``).
#: ``Visual Basic`` is IEEE's classic-VB label: ``visual-basic`` is not a
#: canonical language yet and its normalized key collides with the global
#: ``"visual basic" -> vb.net`` alias, so it is skipped here rather than silently
#: folded into ``vb.net``. A provider must consult this set *before* attempting
#: resolution so these documented labels are skipped without emitting an
#: ``unmapped_language`` warning; any IEEE label neither in this set nor
#: resolvable should still warn downstream.
IEEE_UNTRACKED_LABELS: frozenset[str] = frozenset(
    {
        "HTML",
        "Arduino",
        "Verilog",
        "VHDL",
        "Visual Basic",
    }
)


#: Source-specific aliases shared by the new rating providers (Tasks 01.0-04.0).
#: Rating-scoped entries win over the global alias table in :meth:`resolve`.
RATING_ALIASES: tuple[RatingAlias, ...] = (
    RatingAlias("stackoverflow-tags", "c#", "c#", notes="Stack Overflow C# tag"),
    RatingAlias("stackoverflow-tags", "csharp", "c#", notes="Stack Overflow csharp synonym"),
    RatingAlias("stackoverflow-tags", "cpp", "c++", notes="Stack Overflow cpp synonym"),
    RatingAlias("stackoverflow-tags", "golang", "go", notes="Stack Overflow golang synonym"),
    RatingAlias("stackoverflow-tags", "objc", "objective-c", notes="Stack Overflow objc synonym"),
    RatingAlias("stackoverflow-tags", "objective-c", "objective-c", notes="Stack Overflow objective-c tag"),
    RatingAlias("stackoverflow-tags", "bash", "shell", notes="Stack Overflow bash tag"),
    RatingAlias("stackoverflow-tags", "vb.net", "vb.net", notes="Stack Overflow vb.net tag"),
    RatingAlias("stackoverflow-tags", "typescript", "typescript", notes="Stack Overflow typescript tag"),
    RatingAlias("github", "C++", "c++", notes="GitHub Linguist C++ name"),
    RatingAlias("github", "C#", "c#", notes="GitHub Linguist C# name"),
    RatingAlias("github", "Shell", "shell", notes="GitHub Linguist Shell name"),
    RatingAlias("github", "PowerShell", "powershell", notes="GitHub Linguist PowerShell name"),
    RatingAlias("github", "Visual Basic .NET", "vb.net", notes="GitHub Linguist Visual Basic .NET name"),
    RatingAlias("github", "Objective-C", "objective-c", notes="GitHub Linguist Objective-C name"),
    RatingAlias("ieee-spectrum", "Shell", "shell", notes="IEEE Spectrum Shell label"),
    RatingAlias("ieee-spectrum", "Assembly", "assembly", notes="IEEE Spectrum Assembly label"),
    RatingAlias("ieee-spectrum", "SQL", "sql", notes="IEEE Spectrum ranks SQL as a language"),
)


class LanguageNormalizer:
    """Pure, in-memory mapping from source language names to canonical language IDs.

    The catalog covers the bootstrap providers plus the languages published by the
    new rating providers. Resolution consults rating-scoped aliases first, then the
    global alias / canonical / display-name table.
    """

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
            CanonicalLanguage("c-cpp", "C/C++", ("c/c++",)),
            CanonicalLanguage("typescript", "TypeScript", ("ts",)),
            CanonicalLanguage("kotlin", "Kotlin", ()),
            CanonicalLanguage("swift", "Swift", ()),
            CanonicalLanguage("php", "PHP", ()),
            CanonicalLanguage("ruby", "Ruby", ()),
            CanonicalLanguage("r", "R", ()),
            CanonicalLanguage("scala", "Scala", ()),
            CanonicalLanguage("dart", "Dart", ()),
            CanonicalLanguage("lua", "Lua", ()),
            CanonicalLanguage("perl", "Perl", ()),
            CanonicalLanguage("haskell", "Haskell", ()),
            CanonicalLanguage("elixir", "Elixir", ()),
            CanonicalLanguage("julia", "Julia", ()),
            CanonicalLanguage("matlab", "MATLAB", ()),
            CanonicalLanguage("sql", "SQL", ()),
            CanonicalLanguage("assembly", "Assembly", ("asm",)),
            CanonicalLanguage("groovy", "Groovy", ()),
            CanonicalLanguage("powershell", "PowerShell", ()),
            CanonicalLanguage("zig", "Zig", ()),
            CanonicalLanguage("fortran", "Fortran", ()),
            CanonicalLanguage("cobol", "COBOL", ()),
            CanonicalLanguage("ada", "Ada", ()),
            CanonicalLanguage("delphi", "Delphi", ()),
        ]
        self._lookup: dict[str, str] = {}
        for language in self._languages:
            names = (language.canonical_name, language.display_name, *language.aliases)
            for name in names:
                key = self._normalize_key(name)
                existing = self._lookup.get(key)
                if existing is not None and existing != language.canonical_name:
                    raise ConfigurationError(
                        f"Ambiguous language alias '{name}' maps to both '{existing}' and '{language.canonical_name}'."
                    )
                self._lookup[key] = language.canonical_name

        canonical_names = {language.canonical_name for language in self._languages}
        self._rating_aliases: tuple[RatingAlias, ...] = RATING_ALIASES
        self._rating_lookup: dict[tuple[str, str], str] = {}
        for alias in self._rating_aliases:
            if alias.canonical_name not in canonical_names:
                raise ConfigurationError(
                    f"Rating alias '{alias.source_name}' ({alias.rating_id}) maps to "
                    f"unknown canonical language '{alias.canonical_name}'."
                )
            self._rating_lookup[(alias.rating_id, self._normalize_key(alias.source_name))] = alias.canonical_name

    @staticmethod
    def _normalize_key(value: str) -> str:
        return "".join(char for char in value.lower().strip() if char.isalnum() or char in "+#/.")

    def try_resolve(self, value: str, *, rating_id: Optional[str] = None) -> Optional[str]:
        """Resolve ``value`` to a canonical language ID, returning ``None`` if unknown.

        Lookup order: rating-scoped alias for ``rating_id`` -> global alias ->
        canonical / display name. Never raises, so a single long-tail language
        cannot abort a whole fetch.

        :param value: Source language name to resolve.
        :param rating_id: Optional rating whose scoped aliases take precedence.
        :returns: Canonical language ID, or ``None`` when no mapping exists.
        """
        key = self._normalize_key(value)
        if rating_id:
            scoped = self._rating_lookup.get((rating_id, key))
            if scoped is not None:
                return scoped
        return self._lookup.get(key)

    def resolve(self, value: str, *, rating_id: Optional[str] = None) -> str:
        """Resolve ``value`` to a canonical language ID, raising when unknown.

        :param value: Source language name to resolve.
        :param rating_id: Optional rating whose scoped aliases take precedence.
        :returns: Canonical language ID.
        :raises UnknownLanguageError: If the name resolves to no canonical language.
        """
        resolved = self.try_resolve(value, rating_id=rating_id)
        if resolved is not None:
            return resolved
        suggestions = get_close_matches(value.lower(), [lang.canonical_name for lang in self._languages], n=3)
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
        """Return every alias, global and rating-scoped, for seeding the database.

        :returns: Global aliases (``rating_id=""``) followed by rating-scoped
            aliases carrying their own ``rating_id`` and validity metadata.
        """
        aliases: list[LanguageAlias] = []
        for item in self._languages:
            names = {item.display_name, *item.aliases}
            for alias in sorted(names):
                aliases.append(LanguageAlias(rating_id="", source_name=alias, language_id=item.canonical_name))
        for rating_alias in self._rating_aliases:
            aliases.append(
                LanguageAlias(
                    rating_id=rating_alias.rating_id,
                    source_name=rating_alias.source_name,
                    language_id=rating_alias.canonical_name,
                    valid_from=rating_alias.valid_from,
                    valid_to=rating_alias.valid_to,
                    notes=rating_alias.notes,
                )
            )
        return aliases
