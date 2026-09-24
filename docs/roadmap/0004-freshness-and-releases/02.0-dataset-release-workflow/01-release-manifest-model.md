# Subtask 02.0/01 - Release Manifest Model

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Define the typed `metadata.json` schema as frozen dataclasses with a deterministic
`to_dict()`, so writers and tests share one definition.

## Baseline

- `exports/json_export.py:write_metadata_sidecar` builds an ad-hoc dict; no typed model.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/release/__init__.py` | Package |
| Create | `src/langrank/release/manifest.py` | Manifest dataclasses |
| Create | `tests/unit/test_release_manifest.py` | Model tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `MANIFEST_FORMAT_VERSION` | constant | `int` | `1` | Bumped on breaking manifest changes |
| `ReleaseFile` | frozen dataclass | `name: str`, `sha256: str`, `size_bytes: int`, `media_type: str`, `byte_reproducible: bool` | - | `byte_reproducible=False` for `langrank.sqlite` |
| `RatingCoverage` | frozen dataclass | `rating_id: str`, `metrics: list[str]`, `earliest: str`, `latest: str`, `observations: int`, `languages: int`, `derived_observations: int` | - | |
| `RatingProvenance` | frozen dataclass | `rating_id: str`, `display_name: str`, `homepage: str \| None`, `parser_versions: list[str]`, `acquisition_modes: list[str]`, `caveats: list[str]`, `redistribution: str` | - | lists sorted |
| `MethodologyEntry` | frozen dataclass | `rating_id: str`, `methodology_version: str`, `valid_from: str \| None`, `valid_to: str \| None`, `description: str`, `source_url: str \| None` | - | Mirrors `models.MethodologyNote` |
| `ReleaseFilters` | frozen dataclass | `since: str \| None`, `until: str \| None`, `ratings: list[str]` | - | |
| `ReleaseManifest` | frozen dataclass | `manifest_format_version: int`, `app_version: str`, `schema_version: int`, `generated_at: str`, `filters: ReleaseFilters`, `files: list[ReleaseFile]`, `coverage: list[RatingCoverage]`, `provenance: list[RatingProvenance]`, `methodology: list[MethodologyEntry]`, `warnings: list[str]`, `excluded_ratings: list[str]` | - | |
| `ReleaseManifest.to_dict` | method | `() -> dict[str, Any]` | - | Lists sorted by `rating_id`/`name`; stable key order |
| `ReleaseManifest.to_json` | method | `() -> str` | - | `json.dumps(..., sort_keys=True, indent=2) + "\n"` |

## Behaviour & validators

1. `to_dict()` sorts every list deterministically (`files` by `name`, rating-keyed lists by
   `rating_id` then secondary key); nested lists (`parser_versions`, `acquisition_modes`)
   are sorted and de-duplicated.
2. `schema_version` is `db.migrations.SCHEMA_VERSION`, `app_version` is `langrank.__version__`
   (filled by the service, not defaulted here).
3. `files` never lists `metadata.json` or `checksums.txt` themselves (they would be
   self-referential); `checksums.txt` covers `metadata.json` instead.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_manifest_to_json_is_deterministic` | `tests/unit/test_release_manifest.py` | Unit | shuffled inputs → identical JSON |
| `test_manifest_to_json_trailing_newline_and_sorted_keys` | same | Unit | ends with `\n`; keys sorted |
| `test_manifest_round_trips_through_json` | same | Unit | `json.loads(to_json()) == to_dict()` |

## Success criteria

- [ ] All dataclasses exist with the listed fields.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No I/O in `manifest.py`.

## Out of scope

- Filling the manifest from the DB - [04](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/04-release-service.md).
