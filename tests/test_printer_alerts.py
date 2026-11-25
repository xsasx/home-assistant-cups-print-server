"""Tests for CUPS printer alert parsing."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "cups_print_server"
    / "printer_alerts.py"
)
spec = importlib.util.spec_from_file_location(
    "cups_printer_alerts_under_test", MODULE_PATH
)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestStateReasons(unittest.TestCase):
    def test_none_means_no_reason_and_no_problem(self):
        printer = {"printer-state-reasons": "none"}
        self.assertEqual(mod.state_reasons(printer), [])
        self.assertEqual(mod.problem_reasons(printer), [])

    def test_informational_reasons_are_not_problems(self):
        printer = {
            "printer-state-reasons": [
                "connecting-to-device",
                "offline-report",
                "cups-waiting-for-job-completed",
            ]
        }
        self.assertEqual(len(mod.state_reasons(printer)), 3)
        self.assertEqual(mod.problem_reasons(printer), [])

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
            mod.problem_reasons(printer),
            ["toner-low-warning", "media-empty-error", "paused"],
        )


if __name__ == "__main__":
    unittest.main()
