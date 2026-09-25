"""Provider-agnostic golden-output comparison for contract tests.

This helper is deliberately free of any provider imports so that every rating
provider's contract suite (Stack Overflow Tags, GitHub, IEEE Spectrum, JetBrains,
...) can reuse it. It compares a list of normalized
:class:`~langrank.models.Observation` objects against a checked-in JSON golden
file, ignoring only the non-deterministic ``retrieved_at`` timestamp.

Golden files are stored as a JSON array of observation dicts (each produced by
:meth:`Observation.to_dict`, minus ``retrieved_at``) sorted by
``(metric_id, language_id, period_start)`` for stable, review-friendly diffs.

Regenerating a golden file after an intentional change: run the suite with the
``LANGRANK_UPDATE_GOLDEN=1`` environment variable set (or pass ``update=True``),
review the diff, and commit it. Never set the flag to paper over an unexpected
diff - a changed golden means a changed observation, which is the exact class of
silent-data bug these tests exist to catch.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langrank.models import Observation

#: Fields excluded from the golden comparison because they are not derived from
#: the source bytes and would otherwise make every run diff. ``retrieved_at`` is
#: wall-clock acquisition time; everything else on an observation (including
#: ``raw_record_hash``) is a deterministic function of the fixture.
_VOLATILE_FIELDS = ("retrieved_at",)

#: Sort key giving one stable ordering regardless of provider emit order.
_SORT_FIELDS = ("metric_id", "language_id", "period_start")

#: Environment variable that, when ``"1"``, rewrites the golden file in place.
UPDATE_ENV = "LANGRANK_UPDATE_GOLDEN"


def _observation_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    """Return the stable sort key for one serialized observation.

    :param entry: A serialized observation dict.
    :returns: ``(metric_id, language_id, period_start)`` as strings.
    """
    return tuple(str(entry[field]) for field in _SORT_FIELDS)  # type: ignore[return-value]


def serialize_observations(observations: list[Observation]) -> list[dict[str, Any]]:
    """Serialize observations to sorted, comparison-ready dicts.

    Each observation is rendered via :meth:`Observation.to_dict`, the volatile
    ``retrieved_at`` field is dropped, and the list is sorted by
    ``(metric_id, language_id, period_start)`` so ordering never causes a
    spurious diff.

    :param observations: Observations to serialize.
    :returns: Sorted list of comparison-ready dicts.
    """
    rendered: list[dict[str, Any]] = []
    for observation in observations:
        data = observation.to_dict()
        for field in _VOLATILE_FIELDS:
            data.pop(field, None)
        rendered.append(data)
    rendered.sort(key=_observation_key)
    return rendered


def assert_matches_golden(observations: list[Observation], golden: Path, *, update: bool = False) -> None:
    """Assert that ``observations`` match the golden JSON file at ``golden``.

    Comparison ignores only ``retrieved_at``; every other field - including
    ``language_id``, ``metric_id``, ``rank``, ``value``, ``unit``, ``is_derived``,
    ``derivation_method`` and ``raw_record_hash`` - must match exactly, so a
    silently mis-normalized value or a changed hash fails the test.

    When ``update`` is true or ``LANGRANK_UPDATE_GOLDEN=1`` is set, the golden
    file is (re)written from ``observations`` and no assertion is made. This is a
    maintenance escape hatch for intentional changes, never a default.

    :param observations: Observations produced by the provider under test.
    :param golden: Path to the checked-in golden JSON file.
    :param update: Force-rewrite the golden file regardless of the env var.
    :raises AssertionError: If the observations differ from the golden file, or
        the golden file is missing while not in update mode.
    """
    actual = serialize_observations(observations)
    if update or os.environ.get(UPDATE_ENV) == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    assert golden.exists(), f"golden file {golden} is missing; regenerate it with {UPDATE_ENV}=1 and review the diff"
    expected = json.loads(golden.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"observations diverge from golden {golden.name}; "
        f"if this change is intentional, regenerate with {UPDATE_ENV}=1 and review the diff"
    )
