# Architecture Decision Records

ADRs for Language Ranking use the [MADR](https://adr.github.io/madr/) (Markdown Any Decision Records) template.
Each record lives in this directory as `000N-slug.md`. Mermaid diagrams referenced by ADRs
are in `assets/`.

## Inventory

| ADR                                                           | Title                                                                      | Status   | Date       |
|---------------------------------------------------------------|----------------------------------------------------------------------------|----------|------------|
| [0001](0001-linear-provider-pipeline.md)                      | Linear provider pipeline with persistence-free providers                   | Accepted | 2026-09-29 |
| [0002](0002-provenance-carrying-observations.md)              | Provenance-carrying observations; never fabricate values                   | Accepted | 2026-09-29 |
| [0003](0003-sqlite-storage-and-natural-key-upsert.md)         | Local SQLite via raw `sqlite3`, append-only migrations, natural-key upsert | Accepted | 2026-09-29 |
| [0004](0004-ratings-are-not-comparable-by-default.md)         | Ratings are not comparable by default; explicit normalization required     | Accepted | 2026-09-29 |
| [0005](0005-canonical-language-catalog-and-scoped-aliases.md) | Code-defined canonical language catalog with rating-scoped aliases         | Accepted | 2026-09-29 |
| [0006](0006-source-acquisition-policy.md)                     | Source acquisition policy: policy gate, cache-first, bundled, import       | Accepted | 2026-09-29 |
| [0007](0007-config-resolution-precedence.md)                  | Config resolution: CLI flag > env var > TOML file > XDG default            | Accepted | 2026-09-29 |

ADRs 0001-0007 were recorded retroactively on 2026-09-29: they document decisions already
implemented and enforced by the code at the end of milestone 0001, and each header notes when
the decision actually took effect. New ADRs start as `Proposed` (see `/adr-write`).

## Template

Use `template.md` when creating a new ADR:

```bash
cp docs/adr/template.md docs/adr/0008-short-title.md
```

Replace the template placeholders with the record's number, title, date, and status.

## Naming conventions

- Filename: `000N-kebab-slug.md` - sequential, zero-padded to four digits.
- Status values: `Proposed` | `Accepted` | `Implemented` | `Superseded` | `Deprecated`.
- Superseded ADRs keep their file; add a `Superseded by: [000N](...)` line to their header.
