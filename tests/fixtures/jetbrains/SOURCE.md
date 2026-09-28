# jetbrains test fixtures

Fixtures for the `jetbrains` provider contract tests
(`tests/contract/test_jetbrains_provider.py`) and integration tests
(`tests/integration/test_jetbrains_integration.py`). Tests never hit the network:
the published mode reads a repo-committed CSV and the raw mode imports a local,
pre-extracted file, so both fixtures are static and offline.

## `published_sample.csv`

A **verbatim** subset of the bundled published-percentages dataset
`src/langrank/providers/data/jetbrains.csv`. Every row is copied **byte-for-byte**
from the bundled file (same header
`year,metric,language,percent,sample_size,population,source_url,published_at`);
**no cell was hand-edited or fabricated.** Values are JetBrains' own published,
weighted percentages, so keeping the rows verbatim keeps the golden honest
(`is_derived=False`).

### Selection rule

Copy every bundled row whose:

- **year** is one of `2017`, `2019`, `2024` — three editions that span a
  used-last-12-months **question-wording change** (2017 has only a chart legend, so
  its registry wording is unverified / `None`; 2019 and 2024 carry JetBrains'
  confirmed verbatim strings, which differ from each other), and where `2024` is the
  verified raw-import year;
- **metric** is any of the three JetBrains metrics
  (`jetbrains-used-last-12-months`, `jetbrains-primary-language`,
  `jetbrains-planned-adoption`), so the "questions are never merged" guarantee can be
  checked across all three; and
- **language** is in the fixed label set
  `{Python, Java, C++, SQL, HTML / CSS, Shell, Shell scripting languages}`.

The label set is chosen to exercise three behaviours:

- `Python`, `Java`, `C++`, `SQL` map to canonical language ids in every edition;
- `HTML / CSS` is a documented `JETBRAINS_NON_LANGUAGE_ANSWERS` markup answer that
  must yield **no observation and no `unmapped_language` warning**; and
- the **label-drift alias** for the shell-scripting grouping: JetBrains printed it as
  `Shell scripting languages` in 2019 and as `Shell` in 2024 (and did not list it in
  2017). Both source labels must resolve to the single canonical `shell`, proving the
  per-year alias handles wording drift.

A `(year, metric, language)` combination the edition never published is simply
absent (e.g. `SQL` has no 2017 primary-language row, `Shell` has no 2017 row), so the
file is a sparse slice, not a strict Cartesian product. The result is **48 data
rows**; the 9 `HTML / CSS` rows (3 metrics × 2017/2019/2024) contribute no
observation, leaving **39 published observations** in the golden.

## `raw_sample.csv`

A tiny **synthetic** wide CSV in the verified **2024** raw-dump layout. It is **not**
a JetBrains file: every respondent row is invented. No real JetBrains raw response is
ever committed (JB-SEC-5; the 2024 raw data is licensed CC BY-NC-SA 4.0,
non-commercial).

Layout mirrors the real 2024 dump: each multi-select language answer is one column
per option, named `<prefix>::<Option label>` with a `::` delimiter
(`proglang::` = used in last 12 months, `primary_lang::` = primary language,
`adopt_proglang::` = planned adoption). A cell holds the option label text when the
respondent selected it and is empty otherwise. The header also carries two
non-language columns: `country` and a `comment_freetext` free-text column.

### Synthetic content rule

- **20 respondents** (`R1`–`R20`). `R20` selects **nothing anywhere** — a full
  non-respondent that must fall out of **every** denominator (never 20). `R15` and
  `R16` answer the used question with **only** the meta-answers `Other` /
  `I don't use programming languages`, so they count toward the used denominator but
  produce no observation.
- The three questions have **different denominators** (respondents who answered at
  least one option of that question): used = **16**, primary = **12**, planned = **7**
  — which reinforces that the three metrics are independent series.
- Hand-countable per-option selections give the derived unweighted shares in
  `expected_raw.json` (e.g. used `python` = 10/16 = 62.5 %, primary `python` =
  5/12 ≈ 41.67 %, planned `rust` = 4/7 ≈ 57.14 %). Mapped languages: `python`,
  `java`, `c++`, `kotlin`, `rust`, `go`.
- `R1`'s `comment_freetext` holds a PII / SQL-injection-shaped string
  (`alice.secret@example.com …`). It exists **only** to prove the importer never
  reads a non-language column: the string must appear in no record, observation
  value, or metadata (JB-SEC-4 / JB-SEC-9).

The importer detects the survey year (2024) from the header prefixes, aggregates only
the language-question columns, and emits **11 derived `-raw` records** → **9
observations** (the two meta-answer records normalize away).

## `expected_published.json` / `expected_raw.json`

Golden normalized output produced by the provider's `parse`/`import_path` →
`normalize` and serialized by `tests/contract/_golden.py` (`retrieved_at` stripped;
sorted by `metric_id, language_id, period_start`). `expected_published.json` holds 39
observations (`is_derived=false`); `expected_raw.json` holds 9 observations
(`is_derived=true`, `derivation_method="unweighted_respondent_share"`, `-raw` metric
ids). Regenerate after an intentional change with `LANGRANK_UPDATE_GOLDEN=1` and
review the diff before committing — a changed golden means a changed observation, so
never regenerate to silence an unexpected diff.
