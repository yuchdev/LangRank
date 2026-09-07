from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from langrank import __version__
from langrank.db.repository import QueryRow


def export_json_records(rows: list[QueryRow], output: Path) -> None:
    payload = [asdict(row) for row in rows]
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def export_json_nested(rows: list[QueryRow], output: Path) -> None:
    nested: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        nested[row.rating_id][row.language_id].append(asdict(row))
    output.write_text(json.dumps(nested, indent=2), encoding="utf-8")


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def write_metadata_sidecar(output: Path, filters: dict[str, Any], providers: dict[str, str]) -> None:
    sidecar = {
        "version": __version__,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "filters": filters,
        "provider_versions": providers,
    }
    output.with_suffix(".metadata.json").write_text(
        json.dumps(sidecar, indent=2, default=_json_default),
        encoding="utf-8",
    )
