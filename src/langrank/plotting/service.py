from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from langrank.db.repository import QueryRow


class PlotService:
    def plot(
        self,
        rows: list[QueryRow],
        *,
        metric_id: str,
        output: Path | None,
        title: str | None,
        width: float,
        height: float,
        dpi: int,
        markers: bool,
        invert_rank: bool,
    ) -> None:
        fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
        grouped: dict[str, list[QueryRow]] = {}
        for row in rows:
            grouped.setdefault(row.language_id, []).append(row)
        for language_id, values in grouped.items():
            values = sorted(values, key=lambda row: row.period_start)
            points = [(row.period_start, row.value) for row in values if row.value is not None]
            if not points:
                continue
            x_values: Any = [date.fromisoformat(point[0]) for point in points]
            ax.plot(
                x_values,
                [point[1] for point in points],
                marker="o" if markers else None,
                label=language_id,
            )
        ax.set_xlabel("Period")
        ax.set_ylabel(metric_id)
        ax.set_title(title or f"{metric_id} history")
        if grouped:
            ax.legend()
        if metric_id == "rank" and invert_rank:
            ax.invert_yaxis()
        fig.tight_layout()
        if output is None:
            plt.show()
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(output)
        plt.close(fig)
