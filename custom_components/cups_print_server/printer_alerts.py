"""Interpret printer alerts reported by CUPS.

This module has no Home Assistant dependency so it can be tested on its own.
"""

from __future__ import annotations

from typing import Any

# printer-state-reasons that describe normal operation rather than a fault.
INFORMATIONAL_REASONS = {
    "none",
    "connecting-to-device",
    "cups-waiting-for-job-completed",
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


def state_reasons(printer: dict[str, Any]) -> list[str]:
    """Return printer-state-reasons without the 'none' placeholder."""
    return [
        reason
        for reason in _as_list(printer.get("printer-state-reasons"))
        if isinstance(reason, str) and reason and reason != "none"
    ]


def problem_reasons(printer: dict[str, Any]) -> list[str]:
    """Return the printer-state-reasons that indicate a problem.

    Informational '-report' reasons and normal activity such as
    'connecting-to-device' are ignored.
    """
    return [
        reason
        for reason in state_reasons(printer)
        if reason not in INFORMATIONAL_REASONS
        and not reason.endswith("-report")
    ]
