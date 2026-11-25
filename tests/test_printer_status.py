"""Tests for CUPS supply level and printer alert parsing."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "cups_print_server"
    / "printer_status.py"
)
spec = importlib.util.spec_from_file_location(
    "cups_printer_status_under_test", MODULE_PATH
)
printer_status = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = printer_status
spec.loader.exec_module(printer_status)


class TestParseSupplies(unittest.TestCase):
    def test_no_marker_attributes_means_no_supplies(self):
        self.assertEqual(printer_status.parse_supplies({}), [])

    def test_single_supply_stored_as_scalars(self):
        supplies = printer_status.parse_supplies(
            {
                "marker-names": "Black Toner",
                "marker-levels": 42,
                "marker-types": "toner",
                "marker-colors": "#000000",
                "marker-low-levels": 10,
                "marker-high-levels": 100,
            }
        )
        self.assertEqual(
            supplies,
            [
                {
                    "index": 0,
                    "name": "Black Toner",
                    "type": "toner",
                    "color": "#000000",
                    "level": 42,
                    "level_state": "ok",
                    "low_level": 10,
                    "high_level": 100,
                }
            ],
        )

    def test_multiple_supplies_keep_their_order(self):
        supplies = printer_status.parse_supplies(
            {
                "marker-names": ["Cyan", "Magenta", "Yellow"],
                "marker-levels": [80, 55, 3],
                "marker-types": ["ink-cartridge"] * 3,
            }
        )
        self.assertEqual(
            [(s["index"], s["name"], s["level"]) for s in supplies],
            [(0, "Cyan", 80), (1, "Magenta", 55), (2, "Yellow", 3)],
        )

    def test_special_levels_are_not_percentages(self):
        supplies = printer_status.parse_supplies(
            {
                "marker-names": ["A", "B", "C", "D"],
                "marker-levels": [-1, -2, -3, 250],
            }
        )
        self.assertEqual([s["level"] for s in supplies], [None] * 4)
        self.assertEqual(
            [s["level_state"] for s in supplies],
            ["unavailable", "unknown", "some_remaining", "unknown"],
        )

    def test_missing_values_are_tolerated(self):
        supplies = printer_status.parse_supplies(
            {
                "marker-names": ["Drum", ""],
                "marker-levels": [70],
                "marker-colors": ["none"],
            }
        )
        self.assertEqual(len(supplies), 2)
        self.assertIsNone(supplies[0]["color"])
        self.assertIsNone(supplies[1]["name"])
        self.assertIsNone(supplies[1]["level"])


class TestStateReasons(unittest.TestCase):
    def test_none_means_no_reason_and_no_problem(self):
        printer = {"printer-state-reasons": "none"}
        self.assertEqual(printer_status.state_reasons(printer), [])
        self.assertEqual(printer_status.problem_reasons(printer), [])

    def test_informational_reasons_are_not_problems(self):
        printer = {
            "printer-state-reasons": [
                "connecting-to-device",
                "offline-report",
                "cups-waiting-for-job-completed",
            ]
        }
        self.assertEqual(len(printer_status.state_reasons(printer)), 3)
        self.assertEqual(printer_status.problem_reasons(printer), [])

    def test_warnings_errors_and_paused_queue_are_problems(self):
        printer = {
            "printer-state-reasons": [
                "toner-low-warning",
                "media-empty-error",
                "paused",
                "offline-report",
            ]
        }
        self.assertEqual(
            printer_status.problem_reasons(printer),
            ["toner-low-warning", "media-empty-error", "paused"],
        )


if __name__ == "__main__":
    unittest.main()
