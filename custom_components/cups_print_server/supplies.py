"""Parse printer supply levels reported by CUPS.

This module has no Home Assistant dependency so it can be tested on its own.
"""

from __future__ import annotations

from typing import Any

# Special marker-levels values defined by CUPS.
MARKER_LEVEL_STATES = {
    -1: "unavailable",
    -2: "unknown",
    -3: "some_remaining",
}


def _as_list(value: Any) -> list[Any]:
    """Return an IPP attribute value as a list.

    The IPP parser stores a single value as a scalar and repeated values
    as a list.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _item(values: list[Any], index: int) -> Any:
    return values[index] if index < len(values) else None


def parse_supplies(printer: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the supplies (toner, ink, drum...) reported by CUPS."""
    names = _as_list(printer.get("marker-names"))
    levels = _as_list(printer.get("marker-levels"))
    types = _as_list(printer.get("marker-types"))
    colors = _as_list(printer.get("marker-colors"))
    lows = _as_list(printer.get("marker-low-levels"))
    highs = _as_list(printer.get("marker-high-levels"))

    supplies: list[dict[str, Any]] = []

    for index in range(max(len(names), len(levels))):
        raw_level = _integer(_item(levels, index))

        if raw_level is not None and 0 <= raw_level <= 100:
            level: int | None = raw_level
            level_state = "ok"
        else:
            level = None
            level_state = MARKER_LEVEL_STATES.get(raw_level, "unknown")

        color = _text(_item(colors, index))

        supplies.append(
            {
                "index": index,
                "name": _text(_item(names, index)),
                "type": _text(_item(types, index)),
                "color": None if color == "none" else color,
                "level": level,
                "level_state": level_state,
                "low_level": _integer(_item(lows, index)),
                "high_level": _integer(_item(highs, index)),
            }
        )

    return supplies
