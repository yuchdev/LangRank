# Architecture

LangRank follows a provider-to-storage pipeline:

1. provider metadata and fetch request
2. raw artifact capture/cache
3. parser into source records
4. language normalization into canonical observations
5. validation
6. SQLite persistence
7. query/export/plot services
8. CLI presentation

The demo provider proves the architecture offline with deterministic synthetic data.

## Manual import path

`langrank import --rating <id> <file>` feeds a locally-supplied file into the pipeline,
bypassing the network fetch. The CLI checks whether the provider implements the optional
`SupportsRawImport` protocol (see [/docs/providers.md#optional-capability-supportsrawimport](/docs/providers.md#optional-capability-supportsrawimport)):

- **Provider implements `SupportsRawImport`:** `provider.import_path(path)` is called. The
  method streams the file under explicit byte and row caps and returns source records directly.
  The default `path.read_bytes()` path is not used.
- **Provider does not implement `SupportsRawImport`:** `path.read_bytes()` is called and the
  bytes are passed to `provider.parse()` (unchanged existing behaviour).

After records are returned, the pipeline continues from step 4 (normalize → validate →
persist) as normal.
