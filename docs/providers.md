# Providers

Providers implement the fetch -> parse -> normalize -> validate pipeline and must never write directly to SQLite.

## Demo provider

`demo` ships with LangRank and produces deterministic synthetic annual history for a small language set and two metrics:

- `rank`
- `rating`

The values are synthetic and intended only for testing, demos, and validating the architecture.
