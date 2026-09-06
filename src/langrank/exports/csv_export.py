from __future__ import annotations

import csv
from pathlib import Path

from langrank.db.repository import QueryRow

CSV_COLUMNS = [
    "rating_id",
    "metric_id",
    "language_id",
    "display_name",
    "period_start",
    "period_end",
    "period_label",
    "rank",
    "value",
    "unit",
    "source_url",
]


def export_csv(rows: list[QueryRow], output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in CSV_COLUMNS})
