from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from langrank import __version__
from langrank.config import AppConfig, resolve_config
from langrank.db import Database
from langrank.db.migrations import SCHEMA_VERSION
from langrank.errors import LangRankError
from langrank.exports.csv_export import export_csv
from langrank.exports.json_export import (
    export_json_nested,
    export_json_records,
    write_metadata_sidecar,
)
from langrank.models import FetchRequest, FetchRunStatus, QueryFilters
from langrank.plotting.service import PlotService
from langrank.providers import ProviderRegistry
from langrank.providers.base import FetchPayload
from langrank.services.fetch import FetchService
from langrank.services.query import QueryService
from langrank.services.status import StatusService
from langrank.services.validation import ValidationService

app = typer.Typer(help="LangRank CLI", no_args_is_help=True)
ratings_app = typer.Typer(help="Inspect ratings/providers", invoke_without_command=True)
languages_app = typer.Typer(help="Inspect canonical languages", invoke_without_command=True)
export_app = typer.Typer(help="Export observations")
app.add_typer(ratings_app, name="ratings")
app.add_typer(languages_app, name="languages")
app.add_typer(export_app, name="export")
console = Console()


class AppState:
    def __init__(self, config: AppConfig, verbose: int, quiet: bool) -> None:
        self.config = config
        self.verbose = verbose
        self.quiet = quiet
        self.database = Database(config.db_path)
        self.providers = ProviderRegistry(config.cache_path)


def _parse_date(value: str | None, *, is_end: bool = False) -> date | None:
    if value is None:
        return None
    if len(value) == 4 and value.isdigit():
        return date(int(value), 12 if is_end else 1, 31 if is_end else 1)
    return date.fromisoformat(value)


def _language_ids(state: AppState, names: str | None, rating_id: str | None) -> list[str]:
    if not names:
        return []
    resolved: list[str] = []
    for name in [item.strip() for item in names.split(",") if item.strip()]:
        language_id = state.database.alias_to_language(name, rating_id) or state.database.alias_to_language(name)
        if language_id is None:
            if rating_id == "pypl" and name.lower() in {"c++", "c", "c/c++"}:
                raise LangRankError("PYPL reports C/C++ as a combined source category.\nUse canonical language: c-cpp")
            suggestions = state.database.language_suggestions(name)
            message = f"Unknown language '{name}'."
            if suggestions:
                message = f"{message}\n\nDid you mean:\n  " + "\n  ".join(suggestions)
            raise LangRankError(message)
        resolved.append(language_id)
    return resolved


def _build_filters(
    state: AppState,
    rating: str | None,
    metric: str | None,
    language: str | None,
    languages: str | None,
    all_languages: bool,
    since: str | None,
    until: str | None,
    years: int | None,
    year: int | None,
    top: int | None = None,
    top_current: int | None = None,
) -> QueryFilters:
    selected_names = ",".join(filter(None, [language, languages])) or None
    if rating is not None:
        provider_metrics = state.providers.get(rating).metadata().metrics
        available_ids = [definition.id for definition in provider_metrics]
        if metric is None:
            metric = state.providers.get(rating).metadata().default_metric
        elif metric not in available_ids:
            mapped = [item for item in available_ids if item.endswith(f"-{metric}")]
            if len(mapped) == 1:
                metric = mapped[0]
            else:
                available = "\n  ".join(sorted(available_ids))
                raise LangRankError(
                    f"Metric '{metric}' is not available for {rating}.\n\nAvailable metrics:\n  {available}"
                )
    return QueryFilters(
        rating_id=rating,
        metric_id=metric,
        language_ids=_language_ids(state, selected_names, rating),
        all_languages=all_languages,
        since=_parse_date(since),
        until=_parse_date(until, is_end=True),
        years=years,
        year=year,
        top=top,
        top_current=top_current,
    )


def _render_rows(rows: list[Any], format_name: str) -> None:
    if format_name == "json":
        console.print_json(data=json.dumps([asdict(row) for row in rows]))
        return
    if format_name == "csv":
        headers = list(asdict(rows[0]).keys()) if rows else []
        console.print(",".join(headers))
        for row in rows:
            console.print(",".join(str(getattr(row, header)) for header in headers))
        return
    table = Table(title="Observations")
    for column in [
        "rating_id",
        "metric_id",
        "language_id",
        "period_label",
        "rank",
        "value",
        "unit",
    ]:
        table.add_column(column)
    for row in rows:
        table.add_row(
            row.rating_id,
            row.metric_id,
            row.language_id,
            row.period_label,
            str(row.rank),
            str(row.value),
            row.unit,
        )
    console.print(table)


@app.callback()
def main_callback(
    ctx: typer.Context,
    db: Annotated[Path | None, typer.Option("--db", help="Override database path")] = None,
    cache: Annotated[Path | None, typer.Option("--cache", help="Override cache path")] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Override config path")] = None,
    verbose: Annotated[int, typer.Option("-v", count=True, help="Increase verbosity")] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", help="Suppress non-essential output")] = False,
) -> None:
    level = (
        logging.ERROR if quiet else logging.DEBUG if verbose >= 2 else logging.INFO if verbose == 1 else logging.WARNING
    )
    logging.basicConfig(level=level)
    ctx.obj = AppState(resolve_config(cli_db=db, cli_cache=cache, cli_config=config), verbose, quiet)


@app.command()
def doctor(ctx: typer.Context) -> None:
    state: AppState = ctx.obj
    versions = {row["rating_id"]: row["parser_version"] for row in state.database.provider_versions()}
    table = Table(title="Doctor")
    table.add_column("Item")
    table.add_column("Value")
    rows = {
        "langrank version": __version__,
        "Python version": sys.version.split()[0],
        "DB path": str(state.config.db_path),
        "cache path": str(state.config.cache_path),
        "config path": str(state.config.config_path),
        "schema version": str(state.database.schema_version()),
        "expected schema version": str(SCHEMA_VERSION),
        "enabled providers": ", ".join(provider.provider_id for provider in state.providers.all()),
        "provider/parser versions": json.dumps(
            versions or {provider.provider_id: provider.metadata().parser_version for provider in state.providers.all()}
        ),
    }
    for key, value in rows.items():
        table.add_row(key, value)
    console.print(table)


def _render_ratings_table(state: AppState) -> None:
    for provider in state.providers.all():
        state.database.upsert_provider_metadata(provider.metadata())
    table = Table(title="Ratings")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Granularity")
    table.add_column("Default metric")
    for row in state.database.list_ratings():
        table.add_row(row["id"], row["display_name"], row["native_granularity"], row["default_metric"])
    console.print(table)


@ratings_app.callback()
def ratings_list(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    state: AppState = ctx.obj
    _render_ratings_table(state)


@ratings_app.command("show")
def ratings_show(ctx: typer.Context, provider_id: str) -> None:
    state: AppState = ctx.obj
    provider = state.providers.get(provider_id)
    state.database.upsert_provider_metadata(provider.metadata())
    rating = state.database.get_rating(provider_id)
    assert rating is not None
    table = Table(title=f"Rating {provider_id}")
    table.add_column("Field")
    table.add_column("Value")
    metrics = ", ".join(metric.id for metric in state.database.list_metrics(provider_id))
    caveats = "; ".join(provider.metadata().caveats)
    for field, value in {
        "name": rating["display_name"],
        "description": rating["description"],
        "homepage": rating["homepage"] or "-",
        "native_granularity": rating["native_granularity"],
        "default_metric": rating["default_metric"],
        "available_metrics": metrics,
        "caveats": caveats,
    }.items():
        table.add_row(field, value)
    console.print(table)


def _render_languages_table(state: AppState) -> None:
    table = Table(title="Languages")
    table.add_column("Canonical")
    table.add_column("Display")
    for row in state.database.list_languages():
        table.add_row(row["canonical_name"], row["display_name"])
    console.print(table)


@languages_app.callback()
def languages_list(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    state: AppState = ctx.obj
    _render_languages_table(state)


@languages_app.command("show")
def languages_show(ctx: typer.Context, language: str) -> None:
    state: AppState = ctx.obj
    language_id = state.database.alias_to_language(language)
    if language_id is None:
        suggestions = state.database.language_suggestions(language)
        message = f"Unknown language '{language}'."
        if suggestions:
            message = f"{message}\n\nDid you mean:\n  " + "\n  ".join(suggestions)
        raise LangRankError(message)
    row = state.database.find_language(language_id)
    assert row is not None
    table = Table(title=f"Language {language}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("canonical_name", row["canonical_name"])
    table.add_row("display_name", row["display_name"])
    console.print(table)


@languages_app.command("aliases")
def languages_aliases(ctx: typer.Context, rating: str | None = None) -> None:
    state: AppState = ctx.obj
    table = Table(title="Language aliases")
    table.add_column("Rating")
    table.add_column("Alias")
    table.add_column("Canonical")
    for alias in state.database.list_aliases(rating):
        table.add_row(alias.rating_id or "global", alias.source_name, alias.language_id)
    console.print(table)


@app.command()
def fetch(
    ctx: typer.Context,
    provider_id: str,
    since: str | None = None,
    until: str | None = None,
    years: int | None = None,
    force: bool = False,
    refresh: bool = False,
    offline: bool = False,
    no_cache: bool = False,
    dry_run: bool = False,
    source: str | None = None,
) -> None:
    state: AppState = ctx.obj
    if provider_id == "all":
        providers = state.providers.all()
    else:
        try:
            providers = [state.providers.get(provider_id)]
        except LangRankError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
    service = FetchService(state.database)
    failed = False
    for provider in providers:
        try:
            summary = service.fetch(
                provider,
                FetchRequest(
                    since=_parse_date(since),
                    until=_parse_date(until, is_end=True),
                    years=years,
                    force=force,
                    refresh=refresh,
                    offline=offline,
                    no_cache=no_cache,
                    dry_run=dry_run,
                    verbose=state.verbose,
                    source=source,
                ),
            )
            console.print(
                f"SUCCESS {summary.provider_id} seen={summary.records_seen} inserted={summary.records_inserted} updated={summary.records_updated}"
            )
            if summary.validation_report.issues:
                for issue in summary.validation_report.issues:
                    console.print(f"[{issue.severity.value}] {issue.code}: {issue.message}")
        except Exception as exc:
            failed = True
            console.print(f"FAILED  {provider.provider_id}: {exc}")
    if failed:
        raise typer.Exit(code=1)


@app.command("import")
def import_data(
    ctx: typer.Context,
    rating: str = typer.Option(..., "--rating"),
    path: Path = typer.Argument(...),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    state: AppState = ctx.obj
    provider = state.providers.get(rating)
    metadata = provider.metadata()
    state.database.upsert_provider_metadata(metadata)
    payload = FetchPayload(artifact=None, content=path.read_bytes())
    records = provider.parse(payload)
    observations = provider.normalize(records)
    report = provider.validate(observations)
    if report.ok and not dry_run:
        fetch_run_id = state.database.create_fetch_run(provider.provider_id)
        inserted, updated = state.database.upsert_observations(observations, fetch_run_id)
        state.database.finish_fetch_run(
            fetch_run_id,
            status=FetchRunStatus.SUCCESS,
            records_seen=len(records),
            records_inserted=inserted,
            records_updated=updated,
            warnings=[],
            error=None,
        )
        console.print(f"Imported {rating}: seen={len(records)} inserted={inserted} updated={updated}")
    else:
        console.print(f"Imported {rating}: seen={len(records)} dry_run={dry_run} ok={report.ok}")


@app.command()
def query(
    ctx: typer.Context,
    rating: str | None = typer.Option(None, "--rating"),
    metric: str | None = typer.Option(None, "--metric"),
    language: str | None = typer.Option(None, "--language"),
    languages: str | None = typer.Option(None, "--languages"),
    all_languages: bool = typer.Option(False, "--all-languages"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    years: int | None = typer.Option(None, "--years"),
    year: int | None = typer.Option(None, "--year"),
    format_name: str = typer.Option("table", "--format"),
) -> None:
    state: AppState = ctx.obj
    service = QueryService(state.database)
    filters = _build_filters(state, rating, metric, language, languages, all_languages, since, until, years, year)
    rows = service.query(filters)
    _render_rows(rows, format_name)


@export_app.command("csv")
def export_csv_command(
    ctx: typer.Context,
    output: Path = typer.Option(..., "--output"),
    rating: str | None = typer.Option(None, "--rating"),
    ratings: str | None = typer.Option(None, "--ratings"),
    metric: str | None = typer.Option(None, "--metric"),
    language: str | None = typer.Option(None, "--language"),
    languages: str | None = typer.Option(None, "--languages"),
    all_languages: bool = typer.Option(False, "--all-languages"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    years: int | None = typer.Option(None, "--years"),
    year: int | None = typer.Option(None, "--year"),
    metadata_sidecar: bool = typer.Option(True, "--metadata-sidecar/--no-metadata-sidecar"),
) -> None:
    state: AppState = ctx.obj
    sidecar_filters: QueryFilters | None = None
    provider_ids = [item.strip() for item in (ratings or "").split(",") if item.strip()]
    if rating:
        provider_ids.append(rating)
    rows = []
    if provider_ids:
        for provider_id in sorted(set(provider_ids)):
            filters = _build_filters(
                state,
                provider_id,
                metric,
                language,
                languages,
                all_languages,
                since,
                until,
                years,
                year,
            )
            sidecar_filters = filters
            rows.extend(QueryService(state.database).query(filters))
    else:
        filters = _build_filters(state, rating, metric, language, languages, all_languages, since, until, years, year)
        sidecar_filters = filters
        rows = QueryService(state.database).query(filters)
    export_csv(rows, output)
    if metadata_sidecar:
        versions = {provider.provider_id: provider.metadata().parser_version for provider in state.providers.all()}
        write_metadata_sidecar(output, asdict(sidecar_filters) if sidecar_filters else {}, versions)
    console.print(f"Wrote {output}")


@export_app.command("json")
def export_json_command(
    ctx: typer.Context,
    output: Path = typer.Option(..., "--output"),
    rating: str | None = typer.Option(None, "--rating"),
    ratings: str | None = typer.Option(None, "--ratings"),
    metric: str | None = typer.Option(None, "--metric"),
    language: str | None = typer.Option(None, "--language"),
    languages: str | None = typer.Option(None, "--languages"),
    all_languages: bool = typer.Option(False, "--all-languages"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    years: int | None = typer.Option(None, "--years"),
    year: int | None = typer.Option(None, "--year"),
    layout: str = typer.Option("records", "--layout"),
    metadata_sidecar: bool = typer.Option(True, "--metadata-sidecar/--no-metadata-sidecar"),
) -> None:
    state: AppState = ctx.obj
    sidecar_filters: QueryFilters | None = None
    provider_ids = [item.strip() for item in (ratings or "").split(",") if item.strip()]
    if rating:
        provider_ids.append(rating)
    rows = []
    if provider_ids:
        for provider_id in sorted(set(provider_ids)):
            filters = _build_filters(
                state,
                provider_id,
                metric,
                language,
                languages,
                all_languages,
                since,
                until,
                years,
                year,
            )
            sidecar_filters = filters
            rows.extend(QueryService(state.database).query(filters))
    else:
        filters = _build_filters(state, rating, metric, language, languages, all_languages, since, until, years, year)
        sidecar_filters = filters
        rows = QueryService(state.database).query(filters)
    if layout == "nested":
        export_json_nested(rows, output)
    else:
        export_json_records(rows, output)
    if metadata_sidecar:
        versions = {provider.provider_id: provider.metadata().parser_version for provider in state.providers.all()}
        write_metadata_sidecar(output, asdict(sidecar_filters) if sidecar_filters else {}, versions)
    console.print(f"Wrote {output}")


@app.command()
def plot(
    ctx: typer.Context,
    rating: str | None = typer.Option(None, "--rating"),
    metric: str = typer.Option("rating", "--metric"),
    language: str | None = typer.Option(None, "--language"),
    languages: str | None = typer.Option(None, "--languages"),
    all_languages: bool = typer.Option(False, "--all-languages"),
    top: int | None = typer.Option(None, "--top"),
    top_current: int | None = typer.Option(None, "--top-current"),
    since: str | None = typer.Option(None, "--since"),
    until: str | None = typer.Option(None, "--until"),
    years: int | None = typer.Option(None, "--years"),
    output: Path | None = typer.Option(None, "--output"),
    title: str | None = typer.Option(None, "--title"),
    width: float = typer.Option(10.0, "--width"),
    height: float = typer.Option(6.0, "--height"),
    dpi: int = typer.Option(100, "--dpi"),
    markers: bool = typer.Option(False, "--markers"),
    invert_rank: bool = typer.Option(True, "--invert-rank/--no-invert-rank"),
) -> None:
    state: AppState = ctx.obj
    filters = _build_filters(
        state,
        rating,
        metric,
        language,
        languages,
        all_languages,
        since,
        until,
        years,
        None,
        top,
        top_current,
    )
    rows = [row for row in QueryService(state.database).query(filters) if row.metric_id == metric]
    PlotService().plot(
        rows,
        metric_id=metric,
        output=output,
        title=title,
        width=width,
        height=height,
        dpi=dpi,
        markers=markers,
        invert_rank=invert_rank,
    )
    if output:
        console.print(f"Wrote {output}")


@app.command()
def validate(ctx: typer.Context, rating: str | None = typer.Option(None, "--rating"), strict: bool = False) -> None:
    state: AppState = ctx.obj
    report = ValidationService(state.database).validate()
    if rating is not None:
        report.issues = [
            issue
            for issue in report.issues
            if f"rating_id={rating}" in issue.message or "rating_id=" not in issue.message
        ]
    if not report.issues:
        console.print("Validation passed")
        return
    for issue in report.issues:
        console.print(f"[{issue.severity.value}] {issue.code}: {issue.message}")
    if strict:
        raise typer.Exit(code=1)


@app.command()
def coverage(ctx: typer.Context, language: str | None = typer.Option(None, "--language")) -> None:
    state: AppState = ctx.obj
    language_id = state.database.alias_to_language(language) if language else None
    rows = state.database.coverage(language_id)
    table = Table(title="Coverage")
    table.add_column("Rating")
    table.add_column("Earliest")
    table.add_column("Latest")
    table.add_column("Points")
    table.add_column("Languages")
    for row in rows:
        table.add_row(
            row["rating_id"],
            row["earliest"] or "-",
            row["latest"] or "-",
            str(row["points"]),
            str(row["languages"]),
        )
    console.print(table)


@app.command()
def status(ctx: typer.Context) -> None:
    state: AppState = ctx.obj
    service = StatusService(state.database, state.providers)
    table = Table(title="Status")
    table.add_column("Provider")
    table.add_column("Latest local observation")
    table.add_column("Last fetch run")
    table.add_column("Last failed fetch")
    table.add_column("Records")
    table.add_column("Upstream latest")
    table.add_column("State")
    for item in service.statuses():
        table.add_row(
            item.provider_id,
            item.latest_local_observation or "-",
            item.last_fetch_status or "-",
            item.last_failed_fetch_at or "-",
            str(item.record_count),
            item.upstream_latest_period or "-",
            item.provider_state,
        )
    console.print(table)


def main() -> None:
    try:
        app()
    except LangRankError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
