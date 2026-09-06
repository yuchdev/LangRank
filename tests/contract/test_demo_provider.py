from __future__ import annotations

from pathlib import Path

from langrank.models import FetchRequest
from langrank.providers.demo import DemoProvider


def test_demo_provider_returns_ten_years_plus_history(tmp_path: Path) -> None:
    provider = DemoProvider(tmp_path)
    payload = provider.fetch(FetchRequest())
    records = provider.parse(payload)
    years = sorted({record.period_start.year for record in records})
    assert len(years) >= 10
    assert {record.metric_id for record in records} == {"rank", "rating"}
