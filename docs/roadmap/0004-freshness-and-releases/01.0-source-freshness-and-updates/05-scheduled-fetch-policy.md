# Subtask 01.0/05 - Scheduled-Fetch Source Policy

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Security Auditor (advisory) then Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Make "may this source be fetched unattended?" an explicit, per-provider, provenance-backed
declaration that `langrank update --scheduled` must consult - defaulting to **not allowed**
until a source's legal/source-policy review says otherwise.

## Baseline

- The legal/source-policy gate exists only as prose in
  [milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
  and in `docs/source-notes/*.md` ("Terms/automation considerations").
- `ProviderMetadata` has no policy fields. `config.py:load_file_config` reads only the flat
  `[langrank]` TOML table into `dict[str, str]`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/models.py` | `SourcePolicy` dataclass; `ProviderMetadata.source_policy` |
| Modify | `src/langrank/providers/{tiobe,pypl,redmonk,stackoverflow_survey,demo}.py` | Declare `SourcePolicy` |
| Modify | `src/langrank/config.py` | `AppConfig.scheduled_fetch_overrides`; parse `[langrank.scheduled_fetch]` |
| Create | `src/langrank/services/policy.py` | `effective_scheduled_fetch(metadata, config) -> PolicyDecision` |
| Modify | `docs/source-notes/{tiobe,pypl,redmonk,stackoverflow-survey}.md` | Add `Scheduled fetch:` line matching the declared policy |
| Create | `tests/unit/test_source_policy.py` | Policy + config tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `SourcePolicy` | frozen dataclass | `allow_scheduled_fetch: bool`, `min_interval_hours: int`, `redistribution: str`, `terms_url: str \| None`, `reviewed_at: date \| None`, `notes: str` | `False`, `24`, `"unclear"`, `None`, `None`, `""` | `redistribution` ∈ `{"allowed","derived_only","unclear","forbidden"}` |
| `ProviderMetadata.source_policy` | field | `SourcePolicy` | `SourcePolicy()` | Default = most restrictive |
| `AppConfig.scheduled_fetch_overrides` | field | `dict[str, bool]` | `{}` | From TOML `[langrank.scheduled_fetch]` |
| `PolicyDecision` | frozen dataclass | `provider_id: str`, `allowed: bool`, `source: str`, `reason: str` | - | `source` ∈ `{"provider","config_override"}` |
| `effective_scheduled_fetch` | function | `(metadata: ProviderMetadata, config: AppConfig) -> PolicyDecision` | - | |

## Behaviour & validators

1. Every provider declares a `SourcePolicy` explicitly. `demo`:
   `allow_scheduled_fetch=True, redistribution="allowed"`. The four bundled-snapshot
   providers: `allow_scheduled_fetch=True` is acceptable **only because their `fetch()`
   reads a bundled file (no network)**; the `notes` field must say so, and a live-fetch
   rewrite must re-review. `redistribution` reflects each source note (default
   `"unclear"` → releases ship derived data only; see Task 02.0).
2. A TOML override `[langrank.scheduled_fetch] <provider_id> = true|false` may only
   *restrict* or *enable* for the local user; `PolicyDecision.source="config_override"`
   and `reason` records it. The override is never written anywhere else.
3. `load_file_config` keeps returning the flat `[langrank]` string map; the nested table is
   parsed by a new `load_scheduled_fetch_overrides(config_path) -> dict[str, bool]`
   (non-bool values → `ConfigurationError`).
4. Unknown provider IDs in the override table are **not** a `ConfigurationError` (the
   registry isn't known inside `resolve_config`); `UpdateService` (06) reports them as a
   summary warning.
5. The Security Auditor reviews declared values against `docs/source-notes/` before merge;
   the review outcome is recorded as `reviewed_at`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_default_source_policy_is_restrictive` | `tests/unit/test_source_policy.py` | Unit | `SourcePolicy()` → `allow_scheduled_fetch is False`, `redistribution == "unclear"` |
| `test_every_provider_declares_policy_explicitly` | same | Unit | each registry provider's `metadata().source_policy` is not the default instance **or** has non-empty `notes` |
| `test_config_override_enables_and_is_attributed` | same | Unit | decision `source == "config_override"` |
| `test_config_override_rejects_non_bool` | same | Unit | `ConfigurationError` |
| `test_decision_without_override_uses_provider_policy` | same | Unit | `source == "provider"` |

## Success criteria

- [ ] `SourcePolicy` declared by all providers; source notes updated consistently.
- [ ] Override precedence documented in `docs/ops/scheduled-updates.md` (written in 08).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Do not persist `SourcePolicy` in SQLite in this subtask (metadata-only; release manifest
  reads it from providers).
- Defaults must fail closed.

## Out of scope

- Rate limiting enforcement beyond `min_interval_hours` checks in 06.
