# Documentation Registry

## Architecture and design

- [architecture.md](/docs/architecture.md) - System architecture overview.
- [data-model.md](/docs/data-model.md) - Observation model, derived fields, provenance chain.
- [providers.md](/docs/providers.md) - Provider reference: demo, stackoverflow-tags, github, ieee-spectrum, jetbrains, and others.

## Source notes

Per-provider acquisition policy, quota limits, terms, and methodology gate verdicts.

- [source-notes/stackoverflow-tags.md](/docs/source-notes/stackoverflow-tags.md)
- [source-notes/tiobe.md](/docs/source-notes/tiobe.md)
- [source-notes/pypl.md](/docs/source-notes/pypl.md)
- [source-notes/redmonk.md](/docs/source-notes/redmonk.md)
- [source-notes/stackoverflow-survey.md](/docs/source-notes/stackoverflow-survey.md)
- [source-notes/github.md](/docs/source-notes/github.md)
- [source-notes/ieee-spectrum.md](/docs/source-notes/ieee-spectrum.md)
- [source-notes/jetbrains.md](/docs/source-notes/jetbrains.md)

## Security

- [security/2026-09-25-stackoverflow-tags-fetch.md](/docs/security/2026-09-25-stackoverflow-tags-fetch.md) - Threat model and re-audit for stackoverflow-tags fetch.
- [security/2026-09-25-github-fetch.md](/docs/security/2026-09-25-github-fetch.md) - Threat model and re-audit for github fetch (Innovation Graph and Octoverse).
- [security/2026-09-26-jetbrains-import.md](/docs/security/2026-09-26-jetbrains-import.md) - Threat model and re-audit for jetbrains raw-data import (JB-SEC-1..9).

## Testing

- [test/conventions.md](/docs/test/conventions.md) - Test markers (`integration`, `live`), golden-file workflow, and `LANGRANK_LIVE_TESTS` / `LANGRANK_UPDATE_GOLDEN` env vars.
- [test/code_test_coverage.md](/docs/test/code_test_coverage.md) - Coverage requirements and checklist.

## ADRs

- [adr/README.md](/docs/adr/README.md)
- [adr/0001-config-loading-via-layered-settings.md](/docs/adr/0001-config-loading-via-layered-settings.md)

## Roadmap

- [roadmap/README.md](/docs/roadmap/README.md) - Milestone hierarchy and status.
