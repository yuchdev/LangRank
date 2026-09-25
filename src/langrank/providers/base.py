from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from langrank.models import (
    FetchRequest,
    Observation,
    ProviderMetadata,
    RawArtifact,
    SourceRecord,
    ValidationReport,
)


@dataclass(frozen=True)
class FetchPayload:
    artifact: Optional[RawArtifact]
    content: bytes


class RatingProvider(Protocol):
    provider_id: str

    def metadata(self) -> ProviderMetadata: ...

    def fetch(self, request: FetchRequest) -> FetchPayload: ...

    def parse(self, raw: FetchPayload) -> list[SourceRecord]: ...

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]: ...

    def validate(self, observations: Sequence[Observation]) -> ValidationReport: ...


@runtime_checkable
class SupportsRawImport(Protocol):
    """Optional provider capability: stream a local raw file into source records.

    A provider implements this when ``langrank import`` should ingest a large,
    untrusted, operator-supplied file by **streaming** it under explicit byte and
    row caps, rather than through the default whole-file ``path.read_bytes()`` path
    (which loads the entire file into memory). ``cli.py`` detects the capability at
    runtime via :func:`isinstance` and dispatches to :meth:`import_path`; providers
    without it keep the existing bytes path unchanged. The method owns all parsing
    business logic - the CLI only dispatches.
    """

    provider_id: str

    def import_path(self, path: Path) -> list[SourceRecord]:
        """Stream ``path`` and return the parsed source records (capped, no full read)."""
        ...
