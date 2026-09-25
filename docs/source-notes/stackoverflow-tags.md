# Stack Overflow Tags

- What it measures: monthly count of new questions per language tag on Stack Overflow, expressed as a share of a stated denominator (never a cross-source "popularity score").
- Official source: https://api.stackexchange.com/2.3/questions (Stack Exchange API v2.3); Stack Exchange Data Explorer (SEDE) at https://data.stackexchange.com/ for manual import.
- Historical availability: 2008-09 onward (Stack Overflow launch); default fetch target is the last 10 years ending at the last complete month.
- Acquisition mechanism: `api` (default, scheduled/unattended) via the Stack Exchange API; `sede` manual import of an operator-run SEDE query CSV.
- Imported metrics: `stackoverflow-tags-questions`, `stackoverflow-tags-question-share`, `stackoverflow-tags-rank`.
- Denominators: `all_questions` for the `api` source (site-wide new-question total via `filter=total`) vs `tracked_language_union` for the `sede` source (sum over the tracked master-tag set) - the two are never mixed in one series and each observation records which denominator produced its share.
- Granularity: monthly.
- Language normalization rules: map each Stack Overflow master tag to the canonical language via the alias map; preserve the source tag string in the `SourceRecord`; no synthetic tag splits or merges.
- Known limitations: tag conventions drift over time (renamed/merged tags); question counts measure question-asking activity, not usage or code volume; the current incomplete month is excluded.
- Fallbacks: none - missing months stay missing; no interpolation. SEDE import is a distinct acquisition mode, not a fallback for the API.
- Terms/automation considerations: Stack Exchange API quota is 300 requests/day anonymous and 10,000 requests/day with a registered app key (`register_key`); every response `backoff` field MUST be honoured (wait that many seconds before the next call to the same method) or the app is banned; a separate per-IP dynamic throttle returns HTTP 400 `throttle_violation`; no scraping of stackoverflow.com HTML; the user-contributed data dump is NOT used (since 2024-07 it sits behind a login + agreement not to use content for LLM/AI training, so it is out of scope for automation here).
- Redistribution: aggregate integer counts and derived shares/ranks only; no question titles, bodies, or any other user-contributed content is stored or emitted. Underlying content is CC BY-SA (v2.5/3.0/4.0 by contribution date); the provider records the attribution string "Data from Stack Overflow, licensed under CC BY-SA; see https://stackoverflow.com" in provenance metadata even though bare factual counts are not themselves copyrightable.
- Gate verdict: `approved-for-scheduled-fetch` - reviewer: Security Auditor agent - date: 2026-09-25. Conditions: API source only; `backoff` honoured; daily request budget enforced (see below); aggregate counts only; SEDE stays `manual-only`.
- Request budget: 5000 requests/day enforced ceiling for the `api` source (well under the 10,000/day keyed quota, with headroom for the per-IP throttle). Without `LANGRANK_STACKEXCHANGE_KEY` the effective ceiling drops to the 300/day anonymous quota, so an unattended full backfill requires a key; subtask [04](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/04-fetch-api-and-offline-cache.md) enforces this number and refuses to start when the planned request count would exceed the available budget.
- Parser/version notes: `stackoverflow-tags-v1`.
- Last verified date: 2026-09-25.
