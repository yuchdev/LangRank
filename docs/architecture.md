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
