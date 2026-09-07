from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from langrank.db.repository import Database, QueryRow
from langrank.models import QueryFilters


@dataclass(frozen=True)
class ResolvedFilters:
    filters: QueryFilters
    language_ids: list[str]


class QueryService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def resolve_filters(self, filters: QueryFilters) -> ResolvedFilters:
        since = filters.since
        until = filters.until
        if filters.year is not None:
            since = date(filters.year, 1, 1)
            until = date(filters.year, 12, 31)
        if filters.years and since is None:
            _, latest_year = self._database.resolve_year_bounds(filters.rating_id)
            if latest_year:
                since = date(latest_year - filters.years + 1, 1, 1)
                until = until or date(latest_year, 12, 31)
        updated_filters = QueryFilters(
            rating_id=filters.rating_id,
            metric_id=filters.metric_id,
            language_ids=filters.language_ids,
            all_languages=filters.all_languages,
            since=since,
            until=until,
            years=filters.years,
            year=filters.year,
            top=filters.top,
            top_current=filters.top_current,
        )
        selector_filters = QueryFilters(
            rating_id=updated_filters.rating_id,
            metric_id=None
            if (updated_filters.top or updated_filters.top_current)
            else updated_filters.metric_id,
            language_ids=updated_filters.language_ids,
            all_languages=updated_filters.all_languages,
            since=updated_filters.since,
            until=updated_filters.until,
            years=updated_filters.years,
            year=updated_filters.year,
            top=updated_filters.top,
            top_current=updated_filters.top_current,
        )
        rows = self._database.query_rows(selector_filters)
        language_ids = self._apply_top_filters(rows, updated_filters)
        final_filters = QueryFilters(
            rating_id=updated_filters.rating_id,
            metric_id=updated_filters.metric_id,
            language_ids=language_ids,
            all_languages=updated_filters.all_languages,
            since=updated_filters.since,
            until=updated_filters.until,
            years=updated_filters.years,
            year=updated_filters.year,
            top=updated_filters.top,
            top_current=updated_filters.top_current,
        )
        return ResolvedFilters(filters=final_filters, language_ids=language_ids)

    def query(self, filters: QueryFilters) -> list[QueryRow]:
        resolved = self.resolve_filters(filters)
        return self._database.query_rows(resolved.filters)

    @staticmethod
    def _apply_top_filters(rows: list[QueryRow], filters: QueryFilters) -> list[str]:
        if filters.all_languages:
            return sorted({row.language_id for row in rows})
        if filters.top_current:
            latest_period = max(
                (row.period_start for row in rows if row.metric_id == "rank"), default=None
            )
            selected_languages = [
                row.language_id
                for row in sorted(
                    [
                        row
                        for row in rows
                        if row.metric_id == "rank" and row.period_start == latest_period
                    ],
                    key=lambda row: ((row.rank or 10**9), row.language_id),
                )[: filters.top_current]
            ]
            return selected_languages
        if filters.top:
            return sorted(
                {
                    row.language_id
                    for row in rows
                    if row.metric_id == "rank" and (row.rank or 10**9) <= filters.top
                }
            )
        return filters.language_ids
