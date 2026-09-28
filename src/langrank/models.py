from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Optional


class Granularity(StrEnum):
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"


class FetchRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    DRY_RUN = "dry-run"


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    rating_id: str
    display_name: str
    unit: str
    higher_is_better: bool
    description: str


@dataclass(frozen=True)
class MethodologyNote:
    rating_id: str
    methodology_version: str
    valid_from: Optional[date]
    valid_to: Optional[date]
    description: str
    source_url: Optional[str] = None


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    display_name: str
    description: str
    homepage: Optional[str]
    default_metric: str
    native_granularity: Granularity
    caveats: list[str]
    metrics: list[MetricDefinition]
    parser_version: str
    methodology_notes: list[MethodologyNote] = field(default_factory=list)


@dataclass(frozen=True)
class FetchRequest:
    since: Optional[date] = None
    until: Optional[date] = None
    years: Optional[int] = None
    force: bool = False
    refresh: bool = False
    offline: bool = False
    no_cache: bool = False
    dry_run: bool = False
    verbose: int = 0
    source: Optional[str] = None


@dataclass(frozen=True)
class RawArtifact:
    id: str
    rating_id: str
    url: str
    retrieved_at: datetime
    sha256: str
    mime_type: str
    local_path: str
    http_etag: Optional[str] = None
    http_last_modified: Optional[str] = None
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceRecord:
    rating_id: str
    metric_id: str
    language: str
    period_start: date
    period_end: date
    period_label: str
    granularity: Granularity
    rank: Optional[int]
    value: Optional[float]
    unit: str
    source_url: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    rating_id: str
    metric_id: str
    language_id: str
    period_start: date
    period_end: date
    period_label: str
    granularity: Granularity
    rank: Optional[int]
    value: Optional[float]
    unit: str
    source_language_name: str
    source_url: str
    source_document_id: Optional[str]
    is_derived: bool
    derivation_method: Optional[str]
    retrieved_at: datetime
    source_published_at: Optional[datetime]
    parser_version: str
    raw_record_hash: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    sample_size: Optional[int] = None
    population: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["period_start"] = self.period_start.isoformat()
        data["period_end"] = self.period_end.isoformat()
        data["retrieved_at"] = self.retrieved_at.isoformat()
        data["source_published_at"] = self.source_published_at.isoformat() if self.source_published_at else None
        data["granularity"] = self.granularity.value
        return data


@dataclass(frozen=True)
class Language:
    id: str
    canonical_name: str
    display_name: str


@dataclass(frozen=True)
class LanguageAlias:
    rating_id: str
    source_name: str
    language_id: str
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class QueryFilters:
    rating_id: Optional[str] = None
    metric_id: Optional[str] = None
    language_ids: list[str] = field(default_factory=list)
    all_languages: bool = False
    since: Optional[date] = None
    until: Optional[date] = None
    years: Optional[int] = None
    year: Optional[int] = None
    top: Optional[int] = None
    top_current: Optional[int] = None


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity is Severity.ERROR for issue in self.issues)

    def add(self, severity: Severity, code: str, message: str) -> None:
        self.issues.append(ValidationIssue(severity=severity, code=code, message=message))

    def extend(self, issues: list[ValidationIssue]) -> None:
        self.issues.extend(issues)
