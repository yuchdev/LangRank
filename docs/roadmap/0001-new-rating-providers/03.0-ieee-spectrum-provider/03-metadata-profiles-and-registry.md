# Subtask 03.0/03 - Provider metadata, profiles & registry entry

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Create `IeeeSpectrumProvider` with a metric pair per profile and register `ieee-spectrum`.

## Baseline

`ProviderRegistry` dict; `TiobeProvider.metadata` pattern.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/ieee_spectrum.py` | Provider class |
| Modify | `src/langrank/providers/registry.py` | Register |
| Create | `tests/unit/test_ieee_spectrum_metadata.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `IeeeSpectrumProvider.provider_id` | class attr | `str` | `"ieee-spectrum"` | |
| `IeeeProfile` | StrEnum | `SPECTRUM`, `JOBS`, `TRENDING` (+ historical members from subtask 01) | - | |
| `rank_metric_id` | function | `(profile: IeeeProfile) -> str` | - | `f"ieee-spectrum-{profile}-rank"` |
| `score_metric_id` | function | `(profile: IeeeProfile) -> str` | - | `f"ieee-spectrum-{profile}-score"` |
| `PARSER_VERSION` | const | `str` | `"ieee-spectrum-v1"` | |

## Behaviour & validators

1. `metrics` = 2 × number of profiles; score unit `score` (0-100, higher better), rank unit
   `rank`.
2. `native_granularity=Granularity.YEAR`, `default_metric="ieee-spectrum-spectrum-rank"`.
3. Caveats: "Composite weighted index - weights differ per profile and per edition",
   "Profiles are different rankings, never one series", "Manual transcription".
4. `methodology_notes` = one per edition row of the source-note table.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_metadata_metric_pair_per_profile` | `tests/unit/test_ieee_spectrum_metadata.py` | Unit | IDs and units |
| `test_ieee_methodology_note_per_edition` | `tests/unit/test_ieee_spectrum_metadata.py` | Unit | Count and date ranges |
| `test_registry_contains_ieee_spectrum` | `tests/unit/test_ieee_spectrum_metadata.py` | Unit | `get("ieee-spectrum")` |

## Success criteria

- [ ] `langrank ratings show ieee-spectrum` lists every profile's metric pair.

## Constraints

- No I/O in `metadata()`.

## Out of scope

- Data (subtask 04).
