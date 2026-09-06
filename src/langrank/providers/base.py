from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

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
    artifact: RawArtifact | None
    content: bytes


class RatingProvider(Protocol):
    provider_id: str

    def metadata(self) -> ProviderMetadata: ...

    def fetch(self, request: FetchRequest) -> FetchPayload: ...

    def parse(self, raw: FetchPayload) -> list[SourceRecord]: ...

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]: ...

    def validate(self, observations: Sequence[Observation]) -> ValidationReport: ...
