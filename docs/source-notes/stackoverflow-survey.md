# Stack Overflow Developer Survey

- What it measures: self-reported language usage percentages.
- Official source: https://survey.stackoverflow.co/
- Historical availability: annual datasets (import targets 2016+).
- Acquisition mechanism: CSV-backed year-wise adapter metadata and denominator tracking.
- Imported metrics: `worked_with_percent`, `stackoverflow-survey-rank`.
- Granularity: yearly.
- Language normalization rules: preserve source names, alias-map canonically.
- Known limitations: schema drifts by year and is tracked in metadata.
- Fallbacks: manual import path supported through provider parser pipeline.
- Terms/automation considerations: use official datasets; avoid restricted automation.
- Parser/version notes: `stackoverflow-survey-v1`.
- Last verified date: 2026-09-06.
