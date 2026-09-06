class LangRankError(Exception):
    """Base application error."""


class ConfigurationError(LangRankError):
    """Raised when configuration is invalid."""


class ProviderError(LangRankError):
    """Raised for provider failures."""


class FetchError(ProviderError):
    """Raised when fetching raw artifacts fails."""


class ParseError(ProviderError):
    """Raised when parsing provider data fails."""


class NormalizationError(ProviderError):
    """Raised when provider data cannot be normalized."""


class ValidationError(LangRankError):
    """Raised when data validation fails."""


class StorageError(LangRankError):
    """Raised when persistence fails."""


class UnknownLanguageError(LangRankError):
    def __init__(self, language: str, suggestions: list[str]) -> None:
        message = f"Unknown language '{language}'."
        if suggestions:
            joined = "\n  ".join(suggestions)
            message = f"{message}\n\nDid you mean:\n  {joined}"
        super().__init__(message)
