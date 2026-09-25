from __future__ import annotations

import csv
import io
import stat
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

from langrank.errors import ParseError, ProviderError
from langrank.models import (
    FetchRequest,
    Granularity,
    MethodologyNote,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    SourceRecord,
    ValidationReport,
)
from langrank.normalization import JETBRAINS_NON_LANGUAGE_ANSWERS, LanguageNormalizer
from langrank.providers.base import FetchPayload
from langrank.providers.common import build_observation, payload_from_content
from langrank.providers.jetbrains_questions import (
    METRIC_PLANNED_ADOPTION,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_USED_LAST_12_MONTHS,
    RAW_METRIC_SUFFIX,
    base_metric_id,
    question_for,
    raw_prefix_years,
    raw_prefixes_for_year,
    wording_changes,
)
from langrank.providers.jetbrains_questions import (
    question_for as _question_for,  # noqa: F401  (kept for clarity; see usage below)
)

#: Stable rating id, used across the pipeline and as every metric-id prefix.
_RATING_ID = "jetbrains"

#: Parser version stamped onto every observation this provider emits.
PARSER_VERSION = "jetbrains-v1"

#: Latest verified *State of Developer Ecosystem* report landing page; each
#: curated row carries its own per-edition ``source_url`` (subtask 05), so this is
#: only the artifact-level provenance URL for the provider's metadata.
HOMEPAGE = "https://devecosystem-2025.jetbrains.com/"

#: Curated, repo-committed published-percentages dataset read at
#: :meth:`JetBrainsProvider.fetch` time in the default ``published`` mode (0 network
#: requests). Every value is a figure JetBrains itself ships as chart data for its
#: edition pages; integrity is assured by code review. Columns:
#: ``year,metric,language,percent,sample_size,population,source_url,published_at``.
DATA_PATH = Path(__file__).parent / "data" / "jetbrains.csv"

#: Exact curated-CSV header the published parser requires; a missing column raises a
#: :class:`~langrank.errors.ParseError` so a malformed file never lands miscolumned.
_REQUIRED_COLUMNS: tuple[str, ...] = (
    "year",
    "metric",
    "language",
    "percent",
    "sample_size",
    "population",
    "source_url",
    "published_at",
)

#: ``metadata['provenance']`` stamped on every published record: the value is
#: JetBrains' own weighted percentage taken from the edition's shipped chart data.
_PUBLISHED_PROVENANCE = "published_chart_data"

#: Inclusive percent bounds. JetBrains ships whole-percent figures and prints ``0``
#: values (kept, never dropped); anything outside ``0..100`` is a malformed cell.
_PERCENT_MIN = 0.0
_PERCENT_MAX = 100.0

#: Unit shared by every JetBrains metric: a self-reported percentage. Published
#: percentages are JetBrains' own weighted figures; ``-raw`` percentages are
#: LangRank-derived unweighted respondent shares. The two are never comparable and
#: are kept on separate metric IDs so they never share a series.
_UNIT_PERCENT = "percent"

#: ``derivation_method`` stamped on every ``-raw`` observation (subtask 06). Raw-mode
#: percentages are unweighted per-language respondent shares computed by LangRank over
#: the anonymized response dump, distinct from JetBrains' published weighted figures.
RAW_DERIVATION = "unweighted_respondent_share"

#: Backwards-compatible alias for :data:`RAW_DERIVATION` (same value; the spec/subtask
#: symbol table names the constant :data:`RAW_DERIVATION`, existing code imports
#: ``RAW_DERIVATION_METHOD``).
RAW_DERIVATION_METHOD = RAW_DERIVATION

#: ``metadata['provenance']`` stamped on every ``-raw`` record: the value is an
#: unweighted respondent share LangRank counted over the anonymized raw response dump.
_RAW_PROVENANCE = "raw_respondent_share"

#: Hard cap on the on-disk size of a raw-import file (JB-SEC-1). The verified 2024
#: wide dump is ~219 MB uncompressed; the cap leaves headroom for future editions
#: while rejecting an absurdly padded / decompression-bomb-expanded file before any
#: byte is parsed.
_MAX_IMPORT_BYTES = 600 * 1024 * 1024

#: Hard cap on the number of data rows a raw-import file may contain (JB-SEC-1).
#: JetBrains surveys draw ~25-30k cleaned respondents; the cap is far above any real
#: edition yet bounds a crafted row-flood.
_MAX_IMPORT_ROWS = 2_000_000

#: Explicit per-field byte limit for the raw CSV parser (JB-SEC-3). Language-answer
#: cells are short; free-text cells are ignored but still tokenized by ``csv``, so an
#: explicit bound stops a single pathological field from amplifying memory. Set for
#: the duration of a raw parse only (see :func:`_bounded_csv_field_size`).
_CSV_FIELD_SIZE_LIMIT = 1_000_000

#: Hard cap on the length of one physical line (JB-SEC-1). ``csv.reader`` builds a
#: whole line in memory before the row cap or field limit can act, so a single
#: crafted line would otherwise be bounded only by :data:`_MAX_IMPORT_BYTES`. The
#: verified 2024 dump averages ~9.4 KB per row with a ~200 KB header.
_MAX_LINE_CHARS = 16 * 1024 * 1024

#: Hard cap on the header's column count (JB-SEC-1); the 2024 dump has 5,469.
_MAX_COLUMNS = 50_000

#: ZIP local-file / central-directory / end-of-archive magic byte signatures. A raw
#: import must be a **pre-extracted** CSV (JB-SEC-2); a ``.zip`` is rejected with a
#: clear message telling the operator to extract it (no zip handling in this subtask).
_ZIP_MAGIC: tuple[bytes, ...] = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")

#: The three published, weighted metric IDs (``is_derived=False``). Ordered
#: ``used_last_12_months`` first so it can be the default metric. ``primary_language``
#: and ``used_last_12_months`` answer **different** survey questions and are never
#: merged into one series.
PUBLISHED_METRICS: tuple[str, ...] = (
    METRIC_USED_LAST_12_MONTHS,
    METRIC_PRIMARY_LANGUAGE,
    METRIC_PLANNED_ADOPTION,
)

#: The three derived, unweighted metric IDs, each the matching published ID plus the
#: ``-raw`` suffix (``is_derived=True``, ``derivation_method=`` :data:`RAW_DERIVATION_METHOD`).
#: A ``-raw`` metric never shares a series with its published counterpart.
RAW_METRICS: tuple[str, ...] = tuple(metric_id + RAW_METRIC_SUFFIX for metric_id in PUBLISHED_METRICS)

#: Per published metric: display name and the human-readable question it answers.
#: Reused to build both the published and the ``-raw`` metric definition so the two
#: stay described identically apart from the weighting/derivation distinction.
_METRIC_LABELS: dict[str, tuple[str, str]] = {
    METRIC_USED_LAST_12_MONTHS: (
        "Used in last 12 months",
        "used the language in the last 12 months",
    ),
    METRIC_PRIMARY_LANGUAGE: (
        "Primary language",
        "named the language as their primary (main) language",
    ),
    METRIC_PLANNED_ADOPTION: (
        "Planning to adopt",
        "reported planning to adopt or migrate to the language",
    ),
}


def raw_metric_id(published_metric_id: str) -> str:
    """Return the ``-raw`` metric ID for a published metric ID.

    :param published_metric_id: One of :data:`PUBLISHED_METRICS`.
    :returns: The published ID with the :data:`~langrank.providers.jetbrains_questions.RAW_METRIC_SUFFIX`
        appended (e.g. ``jetbrains-used-last-12-months-raw``).
    """
    return published_metric_id + RAW_METRIC_SUFFIX


class JetBrainsSource(StrEnum):
    """The two independently selectable JetBrains acquisition modes.

    The modes measure the same survey questions but differ in weighting and
    provenance and are **never merged**: ``published`` reads JetBrains' own
    **weighted** percentages (bundled curated CSV, ``is_derived=False``);
    ``raw-data`` imports the anonymized response dump and computes **unweighted**
    respondent shares (``is_derived=True``, ``-raw`` metric IDs). Each mode owns its
    own metric IDs, so a query never mixes weighted and unweighted values.

    :cvar PUBLISHED: JetBrains' published, weighted percentages (default; ``auto``).
    :cvar RAW_DATA: LangRank-derived unweighted shares from the imported raw dump.
    """

    PUBLISHED = "published"
    RAW_DATA = "raw-data"


#: ``--source`` values that select the default (published, weighted) mode.
_AUTO_SOURCES: frozenset[Optional[str]] = frozenset({None, "auto"})


def _resolve_source(value: Optional[str]) -> JetBrainsSource:
    """Resolve a ``--source`` value to a :class:`JetBrainsSource` mode.

    ``None`` and ``"auto"`` select :attr:`JetBrainsSource.PUBLISHED` (the bundled,
    weighted percentages preferred by ``fetch all``); ``"raw-data"`` selects the
    import mode. The modes are never merged, so an unknown value is rejected rather
    than guessed.

    :param value: The raw ``--source`` flag, or ``None`` when unset.
    :returns: The selected :class:`JetBrainsSource`.
    :raises ProviderError: If ``value`` is neither ``auto`` nor a known mode.
    """
    if value in _AUTO_SOURCES:
        return JetBrainsSource.PUBLISHED
    try:
        return JetBrainsSource(value)
    except ValueError as exc:
        valid = ", ".join(["auto", *sorted(source.value for source in JetBrainsSource)])
        raise ProviderError(f"unknown --source {value!r} for jetbrains; valid sources: {valid}.") from exc


class JetBrainsProvider:
    """Records JetBrains *State of Developer Ecosystem* language-usage percentages.

    JetBrains runs an annual self-reported survey and publishes **weighted**
    language figures for three distinct questions - ``used_last_12_months``,
    ``primary_language`` and ``planned_adoption`` - that are **never merged** into
    one series (they answer different questions on different denominators). Each
    question is one metric (:data:`PUBLISHED_METRICS`); the same three questions,
    imported from the anonymized raw response dump and re-computed by LangRank as
    **unweighted** respondent shares, are a second, distinct family of ``-raw``
    metric IDs (:data:`RAW_METRICS`). Published values are weighted
    (``is_derived=False``); ``-raw`` values are unweighted
    (``is_derived=True``, ``derivation_method=`` :data:`RAW_DERIVATION_METHOD`); the
    two families never share a series.

    Acquisition is manual-only in both modes (:class:`JetBrainsSource`):
    ``--source published`` (default / ``auto``) reads the bundled curated CSV with no
    network request, and ``--source raw-data`` imports a local file the operator
    obtained out-of-band. The bundled dataset (subtask 05) and the raw-data import
    (subtask 06) land later; the pipeline methods here are honest stubs until then.

    :ivar provider_id: Stable rating ID used across the pipeline.
    """

    provider_id = _RATING_ID

    def __init__(self, cache_dir: Path) -> None:
        """Wire the provider's cache directory and normalizer.

        Performs no network or database access.

        :param cache_dir: Root cache directory; the provider owns the ``jetbrains``
            subdirectory beneath it.
        """
        self._cache_dir = cache_dir / self.provider_id
        self._normalizer = LanguageNormalizer()
        self._retrieved_at = datetime.now(UTC)
        #: JetBrains labels the last :meth:`normalize` call could not resolve to a
        #: canonical language (documented :data:`JETBRAINS_NON_LANGUAGE_ANSWERS` are
        #: excluded); skipped rather than guessed and surfaced to validation
        #: (subtask 07).
        self.last_unmapped: list[str] = []

    def metadata(self) -> ProviderMetadata:
        """Return the provider's static metadata: the published and ``-raw`` families.

        Performs no network or database access. Methodology notes are built from
        :func:`~langrank.providers.jetbrains_questions.wording_changes` for each
        published metric, so only JetBrains' **verified verbatim** wordings ever feed
        a note (unverified years are skipped, never invented).

        :returns: Fully populated :class:`ProviderMetadata` for this rating.
        """
        metrics: list[MetricDefinition] = []
        for metric_id in PUBLISHED_METRICS:
            display_name, phrasing = _METRIC_LABELS[metric_id]
            metrics.append(
                MetricDefinition(
                    id=metric_id,
                    rating_id=self.provider_id,
                    display_name=f"{display_name} (%)",
                    unit=_UNIT_PERCENT,
                    higher_is_better=True,
                    description=(
                        f"Share of respondents who {phrasing}, as JetBrains published it - a weighted "
                        "percentage (raw, not derived). Weighted published values are never comparable with "
                        "the unweighted -raw shares and never share a series."
                    ),
                )
            )
            metrics.append(
                MetricDefinition(
                    id=raw_metric_id(metric_id),
                    rating_id=self.provider_id,
                    display_name=f"{display_name} (unweighted %)",
                    unit=_UNIT_PERCENT,
                    higher_is_better=True,
                    description=(
                        f"Unweighted share of respondents who {phrasing}, derived by LangRank over the "
                        "anonymized raw response dump (is_derived, "
                        f"derivation_method={RAW_DERIVATION_METHOD!r}). It differs from JetBrains' published "
                        "weighted figure and never shares a series with it."
                    ),
                )
            )
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="JetBrains Developer Ecosystem",
            description=(
                "JetBrains State of Developer Ecosystem: an annual self-reported survey of programming-"
                "language usage and intent. Three distinct questions (used in the last 12 months, primary "
                "language, planning to adopt) are separate metrics that are never merged. The default "
                "published mode carries JetBrains' weighted percentages; --source raw-data imports the "
                "anonymized response dump and stores LangRank's unweighted respondent shares under distinct "
                "-raw metric IDs. Manual-only in both modes (no automated network fetch)."
            ),
            homepage=HOMEPAGE,
            default_metric=METRIC_USED_LAST_12_MONTHS,
            native_granularity=Granularity.YEAR,
            caveats=[
                "Self-reported survey - not comparable with activity metrics (search, GitHub, SO tags).",
                "Published values are weighted; -raw values are unweighted respondent shares - "
                "different series, never comparable.",
                "primary_language and used_last_12_months answer different questions and are never merged.",
                "Question wording and answer sets can change between years (tracked per year in "
                "metadata_json['question_wording'] and surfaced as a methodology note on change).",
                "Raw-data licence: 2024/2025 editions are CC BY-NC-SA 4.0 (non-commercial); 2022/2023 are "
                "attribution-only. Raw files are never redistributed - they stay in the operator's local cache.",
            ],
            parser_version=PARSER_VERSION,
            metrics=metrics,
            methodology_notes=self._wording_methodology_notes(),
        )

    def _wording_methodology_notes(self) -> list[MethodologyNote]:
        """Build one :class:`MethodologyNote` per **verified** question-wording change.

        Iterates :data:`PUBLISHED_METRICS` and, for each, the
        :func:`~langrank.providers.jetbrains_questions.wording_changes` for that
        metric - which returns only years whose verbatim wording JetBrains has
        confirmed - so a note is emitted only for a real, verified wording (never a
        paraphrase or an invented string). Each note's span opens at the survey year
        the wording took effect and stays open (``valid_to=None``) until the next
        confirmed change supersedes it.

        :returns: One note per verified ``(metric, year, wording)`` change, ordered by
            metric then year.
        """
        notes: list[MethodologyNote] = []
        for metric_id in PUBLISHED_METRICS:
            for year, wording in wording_changes(metric_id):
                notes.append(
                    MethodologyNote(
                        rating_id=self.provider_id,
                        methodology_version=f"jetbrains-{metric_id}-wording-{year}",
                        valid_from=date(year, 1, 1),
                        valid_to=None,
                        description=(
                            f"{metric_id} question wording confirmed for the {year} survey: {wording!r}. "
                            "Wording can change between years; only verified verbatim wording is recorded."
                        ),
                        source_url=HOMEPAGE,
                    )
                )
        return notes

    def fetch(self, request: FetchRequest) -> FetchPayload:
        """Fetch raw data for the selected acquisition mode.

        Resolves ``--source`` first, so an unknown mode is rejected here. The default
        ``published`` mode reads the bundled curated CSV (:data:`DATA_PATH`) with **no
        network request** (budget 0) - its bytes' integrity is assured by code review
        and the ``--offline`` flag is a no-op for it. ``--source raw-data`` is
        **import-only** and never reachable through ``fetch``: the anonymized response
        dump enters solely via ``langrank import``
        (:meth:`import_path`), which makes **no** network request (JB-SEC-7), so
        ``fetch`` refuses the raw-data mode rather than downloading it. The artifact
        ``url`` is the provider homepage; each row carries its own per-edition
        ``source_url`` for the parser.

        :param request: Fetch parameters; ``source`` (validated here) and ``no_cache``
            are honoured. The published dataset covers a fixed span, so the
            ``since`` / ``until`` / ``years`` window is not applied to it.
        :returns: The raw fetch payload for the selected mode.
        :raises ProviderError: If ``--source`` names an unknown mode.
        :raises NotImplementedError: When ``--source raw-data`` is requested; raw data
            is imported via :meth:`import_path`, never fetched.
        """
        source = _resolve_source(request.source)
        if source is JetBrainsSource.RAW_DATA:
            raise NotImplementedError(
                "jetbrains raw-data is import-only; use `langrank import --rating jetbrains <raw.csv>`, not fetch."
            )
        content = DATA_PATH.read_bytes()
        return payload_from_content(
            provider_id=self.provider_id,
            cache_dir=self._cache_dir,
            url=HOMEPAGE,
            content=content,
            mime_type="text/csv",
            metadata_json={
                "mode": JetBrainsSource.PUBLISHED.value,
                "provenance": _PUBLISHED_PROVENANCE,
                "source_document_id": self.provider_id,
            },
            no_cache=request.no_cache,
        )

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        """Parse the curated published-percentages CSV into per-language records.

        Hardens the untrusted CSV: the stdlib ``csv`` module is used (never ``eval``);
        non-UTF-8 bytes raise a :class:`~langrank.errors.ParseError` (a UTF-8 BOM is
        tolerated); a missing required column (:data:`_REQUIRED_COLUMNS`) raises a
        ``ParseError`` naming it; and an unknown ``metric``, an implausible ``year``, a
        percent outside ``0..100``, a non-positive ``sample_size`` or a blank
        ``population`` each raise a ``ParseError`` naming the offending row. A row for a
        ``(year, metric)`` the registry says was **not** asked
        (:func:`~langrank.providers.jetbrains_questions.question_for` is ``None``) is
        rejected too, so a mis-yeared row never lands. Each mapped row yields one
        percentage record (no rank metric - JetBrains publishes percentages only); the
        row's ``question_wording`` / ``wording_verified``, ``sample_size``,
        ``population``, ``source_url`` and ``published_at`` are carried for
        :meth:`normalize`. Records are annual (:attr:`Granularity.YEAR`).

        :param raw: The raw curated-CSV fetch payload.
        :returns: One percentage record per curated row.
        :raises ParseError: On a decoding error, a missing required column, an unknown
            or unasked ``(year, metric)``, or a malformed / out-of-range cell.
        """
        try:
            text = raw.content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError("jetbrains CSV must be UTF-8 encoded.") from exc
        reader = csv.DictReader(text.splitlines())
        fieldnames = reader.fieldnames or []
        for column in _REQUIRED_COLUMNS:
            if column not in fieldnames:
                raise ParseError(f"jetbrains CSV is missing required column {column!r}.")
        return [_record_from_row(row) for row in reader]

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        """Normalize source records into observations with full provenance.

        :data:`~langrank.normalization.JETBRAINS_NON_LANGUAGE_ANSWERS` is consulted
        **before** resolution, so markup / meta-answers (``HTML / CSS``, ``Other``,
        ``GraphQL`` ...) and JetBrains' classic-VB ``Visual Basic`` are skipped
        silently - no observation, no ``unmapped_language`` warning - and never fold
        into ``vb.net`` via the global alias. Any other label that resolves to no
        canonical language is skipped and recorded in :attr:`last_unmapped` (never
        guessed) for validation (subtask 07).

        Published values are JetBrains' own weighted percentages, emitted verbatim
        (``is_derived=False``, ``derivation_method=None``, ``unit='percent'``). A
        ``-raw`` record (metric ID suffixed :data:`~langrank.providers.jetbrains_questions.RAW_METRIC_SUFFIX`,
        produced by :meth:`import_path`) is instead an unweighted respondent share
        (``is_derived=True``, ``derivation_method=`` :data:`RAW_DERIVATION`); its
        denominator travels in ``metadata_json['denominator']`` and is also stored as
        ``sample_size``. Either way the edition identifies the document
        (``source_document_id=jetbrains-devecosystem-{year}[-raw]``); the survey year
        is the period; and ``metadata_json`` carries the registry ``question_wording``
        (``None`` when unverified - never invented) plus ``wording_verified``. Pure
        over its inputs: no network, no database.

        :param records: Parsed per-language source records.
        :returns: One observation per mapped record; empty when none map.
        """
        self.last_unmapped = []
        observations: list[Observation] = []
        for record in records:
            label = record.language
            if label in JETBRAINS_NON_LANGUAGE_ANSWERS:
                continue
            language_id = self._normalizer.try_resolve(label, rating_id=self.provider_id)
            if language_id is None:
                if label not in self.last_unmapped:
                    self.last_unmapped.append(label)
                continue
            is_raw = record.metric_id.endswith(RAW_METRIC_SUFFIX)
            year = record.period_start.year
            source_document_id = f"jetbrains-devecosystem-{year}-raw" if is_raw else f"jetbrains-devecosystem-{year}"
            observations.append(
                build_observation(
                    record=record,
                    language_id=language_id,
                    parser_version=PARSER_VERSION,
                    retrieved_at=self._retrieved_at,
                    is_derived=is_raw,
                    derivation_method=RAW_DERIVATION if is_raw else None,
                    source_document_id=source_document_id,
                    source_published_at=_published_at(record.metadata.get("published_at")),
                    sample_size=record.metadata.get("sample_size"),
                    population=record.metadata.get("population"),
                )
            )
        return observations

    def import_path(self, path: Path) -> list[SourceRecord]:
        """Stream a local raw-response CSV into derived ``-raw`` source records.

        This is the :class:`~langrank.providers.base.SupportsRawImport` capability
        (``langrank import --rating jetbrains <raw.csv>``). Unlike the default import
        path it never reads the whole file into memory: it rejects a file larger than
        :data:`_MAX_IMPORT_BYTES` up front (JB-SEC-1), rejects a ``.zip`` by magic
        bytes with a message telling the operator to extract it (JB-SEC-2), then
        streams the CSV over a text file handle - one pass, no per-row objects - under
        a :data:`_MAX_IMPORT_ROWS` cap. Only the registry's language-question columns
        for the detected year are read; every other column (free-text included) is
        ignored and never persisted (JB-SEC-4). The file is read in place and never
        copied into the repo or cache (JB-SEC-5).

        :param path: Local, operator-supplied, pre-extracted raw CSV.
        :returns: One derived ``-raw`` record per (metric, language) selected.
        :raises ParseError: If the file is oversized, a ``.zip``, too many rows, not
            UTF-8, has no detectable supported survey year, or is malformed.
        """
        try:
            status = path.stat()
        except OSError as exc:
            raise ParseError(f"jetbrains raw import: cannot read {path.name!r}.") from exc
        if not stat.S_ISREG(status.st_mode):
            raise ParseError(f"jetbrains raw import: {path.name!r} is not a regular file.")
        size = status.st_size
        if size > _MAX_IMPORT_BYTES:
            raise ParseError(
                f"jetbrains raw import: file is {size} bytes, over the {_MAX_IMPORT_BYTES}-byte cap; refusing to load it."
            )
        with path.open("rb") as handle:
            _reject_zip(handle.read(len(_ZIP_MAGIC[0])))
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as text_handle:
                return _aggregate_raw(text_handle)
        except UnicodeDecodeError as exc:
            raise ParseError("jetbrains raw import: file must be UTF-8 encoded.") from exc

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        """Validate observations against named codes (lands in subtask 07).

        :param observations: Observations to validate.
        :returns: A validation report.
        :raises NotImplementedError: Until subtask 07 lands validation.
        """
        raise NotImplementedError("jetbrains validate lands in subtask 07.")


def _published_at(value: object) -> Optional[datetime]:
    """Parse a curated ``published_at`` cell into an aware UTC datetime.

    JetBrains prints no publication date for any edition, so the column is empty
    throughout; an empty (or missing) cell therefore yields ``None`` rather than a
    fabricated date.

    :param value: The row's ``published_at`` cell (``str`` or ``None``).
    :returns: The date at UTC midnight, or ``None`` when the cell is blank.
    """
    text = str(value or "").strip()
    if not text:
        return None
    return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)


def _record_from_row(row: dict[str, Any]) -> SourceRecord:
    """Build one percentage :class:`~langrank.models.SourceRecord` from a curated row.

    The row's ``metric`` must be one of :data:`PUBLISHED_METRICS`, its ``year`` must be
    plausible and asked for that metric (:func:`~langrank.providers.jetbrains_questions.question_for`),
    its ``percent`` must lie in ``0..100`` (JetBrains ships whole-percent figures and
    prints ``0`` values, which are kept), its ``sample_size`` must be a positive integer
    and its ``population`` must be non-empty. The verified/registry ``question_wording``
    and ``wording_verified`` flag are attached to the record metadata here (from the pure
    registry) so they travel into ``metadata_json`` unchanged; wording is never invented.

    :param row: A curated CSV row keyed by column name.
    :returns: The percentage record for the ``(year, metric, language)`` cell.
    :raises ParseError: If the metric is unknown, the year implausible or unasked, or a
        numeric / required cell is malformed.
    """
    try:
        year = int(row["year"])
        metric_id = row["metric"]
        language = row["language"]
        percent = float(row["percent"])
        sample_size = int(row["sample_size"])
        population = (row["population"] or "").strip()
        source_url = row["source_url"]
        published_at = (row["published_at"] or "").strip()
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"jetbrains row is malformed: {row!r}") from exc
    if metric_id not in PUBLISHED_METRICS:
        raise ParseError(f"jetbrains row has unknown metric {metric_id!r}: {row!r}")
    if not 2000 <= year <= 2100:
        raise ParseError(f"jetbrains year is implausible: {row!r}")
    question = question_for(year, metric_id)
    if question is None:
        raise ParseError(f"jetbrains metric {metric_id!r} was not asked in {year}: {row!r}")
    if not _PERCENT_MIN <= percent <= _PERCENT_MAX:
        raise ParseError(f"jetbrains percent must be in 0..100: {row!r}")
    if sample_size <= 0:
        raise ParseError(f"jetbrains sample_size must be positive: {row!r}")
    if not population:
        raise ParseError(f"jetbrains population must not be empty: {row!r}")
    metadata: dict[str, Any] = {
        "provenance": _PUBLISHED_PROVENANCE,
        "sample_size": sample_size,
        "population": population,
        "published_at": published_at,
        "question_wording": question.wording,
        "wording_verified": question.wording_verified,
    }
    return SourceRecord(
        rating_id=_RATING_ID,
        metric_id=metric_id,
        language=language,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        period_label=str(year),
        granularity=Granularity.YEAR,
        rank=None,
        value=percent,
        unit=_UNIT_PERCENT,
        source_url=source_url,
        metadata=metadata,
    )


def _report_url(year: int) -> str:
    """Return the *State of Developer Ecosystem* report URL for a survey year.

    Carried as the ``source_url`` of every ``-raw`` record. 2025 onward moved to a
    per-edition subdomain; earlier editions live under ``/lp/devecosystem-<year>/``.

    :param year: Survey year.
    :returns: The edition's report landing-page URL.
    """
    if year >= 2025:
        return f"https://devecosystem-{year}.jetbrains.com/"
    return f"https://www.jetbrains.com/lp/devecosystem-{year}/"


def _reject_zip(head: bytes) -> None:
    """Reject a raw import that is a ``.zip`` archive by magic bytes (JB-SEC-2).

    Raw import accepts only a **pre-extracted** CSV; this subtask does no zip
    handling (zip-slip / zip-bomb surface), so a ``.zip`` is refused with a message
    telling the operator to extract it first.

    :param head: The first bytes of the candidate file / payload.
    :raises ParseError: If ``head`` carries a ZIP signature.
    """
    if any(head.startswith(signature) for signature in _ZIP_MAGIC):
        raise ParseError(
            "jetbrains raw import: input looks like a .zip archive; extract the CSV and import the extracted file."
        )


@contextmanager
def _bounded_csv_field_size() -> Iterator[None]:
    """Bound :func:`csv.field_size_limit` for the duration of a raw parse (JB-SEC-3).

    The stdlib default is very large, so a single pathological field can amplify
    memory. This sets an explicit :data:`_CSV_FIELD_SIZE_LIMIT` and restores the
    previous process-wide value on exit, so other providers' parsing is unaffected.

    :returns: A context manager yielding ``None``.
    """
    previous = csv.field_size_limit()
    csv.field_size_limit(_CSV_FIELD_SIZE_LIMIT)
    try:
        yield
    finally:
        csv.field_size_limit(previous)


def _raw_year_prefixes() -> dict[int, dict[str, str]]:
    """Build ``{year: {metric_id: column_prefix}}`` for every raw-import year.

    Sourced purely from the question registry (:func:`raw_prefix_years` /
    :func:`raw_prefixes_for_year`); a year appears only when its raw column layout
    has been verified (2024 in this subtask).

    :returns: Per-year language-question column prefixes.
    """
    return {year: raw_prefixes_for_year(year) for year in raw_prefix_years()}


def _detect_survey_year(
    header: list[str],
    *,
    year_prefixes: Optional[Mapping[int, Mapping[str, str]]] = None,
) -> int:
    """Detect the survey year of a raw dump from its CSV header (JB-SEC / spec 06).

    A registry year is a candidate when **all** its language-question column
    prefixes are present in ``header``. Exactly one candidate is required: zero
    means the header matches no supported year's layout, and more than one means the
    layout cannot be attributed to a single year - both raise rather than guess, so
    a value is never mis-yeared. The message references years only, never a header
    cell (JB-SEC-9).

    :param header: The raw CSV header row.
    :param year_prefixes: Optional ``{year: {metric_id: prefix}}`` override; defaults
        to the registry-derived mapping (:func:`_raw_year_prefixes`).
    :returns: The single detected survey year.
    :raises ParseError: If no supported year matches, or the match is ambiguous.
    """
    mapping = _raw_year_prefixes() if year_prefixes is None else year_prefixes
    candidates = [
        year
        for year, prefixes in mapping.items()
        if prefixes and all(any(column.startswith(prefix) for column in header) for prefix in prefixes.values())
    ]
    if not candidates:
        supported = ", ".join(str(year) for year in sorted(mapping)) or "none"
        raise ParseError(
            f"jetbrains raw import: could not detect a supported survey year from the CSV header (supported: {supported})."
        )
    if len(candidates) > 1:
        years = ", ".join(str(year) for year in sorted(candidates))
        raise ParseError(f"jetbrains raw import: survey year is ambiguous between {years}; refusing to guess.")
    return candidates[0]


def _bounded_lines(stream: io.TextIOBase) -> Iterator[str]:
    """Yield physical lines from ``stream``, refusing any over :data:`_MAX_LINE_CHARS`.

    :param stream: A text stream.
    :returns: An iterator of lines, each at most :data:`_MAX_LINE_CHARS` characters.
    :raises ParseError: If a line exceeds the cap (its content is never echoed).
    """
    line_number = 0
    while True:
        line = stream.readline(_MAX_LINE_CHARS + 1)
        if not line:
            return
        line_number += 1
        if len(line) > _MAX_LINE_CHARS:
            raise ParseError(
                f"jetbrains raw import: physical line {line_number} exceeds the {_MAX_LINE_CHARS}-character cap."
            )
        yield line


def _aggregate_raw(stream: io.TextIOBase) -> list[SourceRecord]:
    """Stream a raw-dump text handle into derived ``-raw`` source records.

    One pass over ``stream``: the header selects the detected year's language
    columns (only those columns are ever read - JB-SEC-4), then each data row is
    counted without building a per-row object. For every language question, a
    respondent counts toward the denominator when they selected **at least one**
    option (a non-empty cell); the per-option count over that denominator is the
    unweighted respondent share. Row width is checked against the header and the row
    count is capped (:data:`_MAX_IMPORT_ROWS`); malformed rows raise a
    :class:`~langrank.errors.ParseError` naming the **row index only** - never a cell
    value (JB-SEC-9).

    :param stream: A text stream positioned at the header row.
    :returns: One ``-raw`` record per (metric, selected option label).
    :raises ParseError: On an empty file, an undetectable / ambiguous year, a row of
        unexpected width, a row-count overflow, or a malformed CSV line.
    """
    with _bounded_csv_field_size():
        reader = csv.reader(_bounded_lines(stream))
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ParseError("jetbrains raw import: file is empty.") from exc
        if len(header) > _MAX_COLUMNS:
            raise ParseError(f"jetbrains raw import: header has {len(header)} columns, over the {_MAX_COLUMNS} cap.")
        year = _detect_survey_year(header)
        width = len(header)
        columns: dict[str, list[tuple[int, str]]] = {}
        for metric_id, prefix in raw_prefixes_for_year(year).items():
            columns[metric_id] = [
                (index, column[len(prefix) :]) for index, column in enumerate(header) if column.startswith(prefix)
            ]
        selection_counts: dict[str, Counter[str]] = {metric_id: Counter() for metric_id in columns}
        denominators: dict[str, int] = dict.fromkeys(columns, 0)
        try:
            for row_number, row in enumerate(reader, start=2):
                if row_number - 1 > _MAX_IMPORT_ROWS:
                    raise ParseError(
                        f"jetbrains raw import: exceeded the {_MAX_IMPORT_ROWS}-row cap at data row {row_number - 1}."
                    )
                if len(row) != width:
                    raise ParseError(f"jetbrains raw import: row {row_number} has {len(row)} fields, expected {width}.")
                for metric_id, cells in columns.items():
                    selected = [label for index, label in cells if row[index].strip()]
                    if selected:
                        denominators[metric_id] += 1
                        selection_counts[metric_id].update(selected)
        except csv.Error as exc:
            raise ParseError("jetbrains raw import: malformed CSV line.") from exc
    return _records_from_counts(year, selection_counts, denominators)


def _records_from_counts(
    year: int,
    selection_counts: Mapping[str, Counter[str]],
    denominators: Mapping[str, int],
) -> list[SourceRecord]:
    """Turn per-metric selection counts into derived ``-raw`` source records.

    Only aggregate counts and the denominator are persisted - never a response-level
    row or a free-text value (JB-SEC-4). Each record's ``value`` is the unweighted
    respondent share (``count / denominator * 100``); the denominator is stored both
    as ``metadata['denominator']`` and ``metadata['sample_size']`` (the latter feeds
    :meth:`JetBrainsProvider.normalize`); the registry question wording (``None`` when
    unverified) travels alongside. A metric no respondent answered (denominator 0) is
    skipped. Metrics are emitted in :data:`PUBLISHED_METRICS` order for determinism.

    :param year: Detected survey year.
    :param selection_counts: Per published metric ID, the count each option label was
        selected.
    :param denominators: Per published metric ID, the respondents who answered it.
    :returns: Derived ``-raw`` records (:data:`RAW_DERIVATION`, ``-raw`` metric IDs).
    """
    records: list[SourceRecord] = []
    source_url = _report_url(year)
    for metric_id in PUBLISHED_METRICS:
        counts = selection_counts.get(metric_id)
        denominator = denominators.get(metric_id, 0)
        if not counts or denominator <= 0:
            continue
        question = question_for(year, metric_id)
        wording = question.wording if question is not None else None
        wording_verified = question.wording_verified if question is not None else False
        derived_metric_id = raw_metric_id(base_metric_id(metric_id))
        for label, count in sorted(counts.items()):
            metadata: dict[str, Any] = {
                "provenance": _RAW_PROVENANCE,
                "acquisition_mode": JetBrainsSource.RAW_DATA.value,
                "denominator": denominator,
                "sample_size": denominator,
                "respondent_count": count,
                "survey_year": year,
                "question_wording": wording,
                "wording_verified": wording_verified,
            }
            records.append(
                SourceRecord(
                    rating_id=_RATING_ID,
                    metric_id=derived_metric_id,
                    language=label,
                    period_start=date(year, 1, 1),
                    period_end=date(year, 12, 31),
                    period_label=str(year),
                    granularity=Granularity.YEAR,
                    rank=None,
                    value=count / denominator * 100.0,
                    unit=_UNIT_PERCENT,
                    source_url=source_url,
                    metadata=metadata,
                )
            )
    return records


def _parse_raw(content: bytes) -> list[SourceRecord]:
    """Parse raw-dump **bytes** into derived ``-raw`` source records (spec 06 symbol).

    Pure over the input bytes: wraps them in a text stream and delegates to
    :func:`_aggregate_raw`. A ``.zip`` is rejected by magic bytes (JB-SEC-2) and
    non-UTF-8 bytes raise a :class:`~langrank.errors.ParseError` (JB-SEC-3). The
    streaming, size-capped file path used by ``langrank import`` is
    :meth:`JetBrainsProvider.import_path`; this bytes entry point shares the same
    one-pass aggregation for callers that already hold the content.

    :param content: Raw response-dump CSV bytes.
    :returns: One ``-raw`` record per (metric, selected option label).
    :raises ParseError: On a ``.zip`` input, non-UTF-8 bytes, or a malformed CSV.
    """
    _reject_zip(content[: len(_ZIP_MAGIC[0])])
    stream = io.TextIOWrapper(io.BytesIO(content), encoding="utf-8-sig", newline="")
    try:
        return _aggregate_raw(stream)
    except UnicodeDecodeError as exc:
        raise ParseError("jetbrains raw import: content must be UTF-8 encoded.") from exc
