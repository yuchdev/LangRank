from __future__ import annotations

from langrank.db.repository import Database
from langrank.models import Severity, ValidationReport


class ValidationService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def validate(self) -> ValidationReport:
        report = ValidationReport()
        results = self._database.validation_queries()
        for key, rows in results.items():
            for row in rows:
                report.add(Severity.ERROR, key, ", ".join(f"{name}={row[name]}" for name in row.keys()))
        return report
