"""Regression tests for the standalone CUPS IPP encoder and parser."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "cups_print_server"
    / "ipp.py"
)
spec = importlib.util.spec_from_file_location("cups_ipp_under_test", MODULE_PATH)
ipp = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = ipp
spec.loader.exec_module(ipp)


def response(*groups: bytes, status: int = 0) -> bytes:
    """Build a minimal IPP response with an end marker."""
    return (
        b"\\x02\\x00"
        + struct.pack(">H", status)
        + struct.pack(">I", 1)
        + b"".join(groups)
        + bytes([ipp.TAG_END])
    )


class TestIppCodec(unittest.TestCase):
    def test_request_contains_operation_and_requested_attributes(self):
        payload = ipp._request(
            ipp.OP_GET_JOBS,
            "printer-uri",
            "ipp://localhost:631/printers/test",
            ["job-id", "job-state"],
            all_jobs=True,
        )
        self.assertEqual(payload[:2], ipp.IPP_VERSION)
        self.assertEqual(
            struct.unpack(">H", payload[2:4])[0],
            ipp.OP_GET_JOBS,
        )
        self.assertIn(b"job-id", payload)
        self.assertIn(b"job-state", payload)
        self.assertIn(b"which-jobs", payload)
        self.assertEqual(payload[-1], ipp.TAG_END)

    def test_parse_integer_boolean_and_text(self):
        printer_group = (
            bytes([ipp.TAG_PRINTER])
            + ipp._attr(ipp.TAG_INTEGER, "queued-job-count", struct.pack(">i", 3))
            + ipp._attr(ipp.TAG_BOOLEAN, "printer-is-accepting-jobs", b"\\x01")
            + ipp._attr(ipp.TAG_NAME, "printer-name", b"Office")
        )
        status, groups = ipp.parse_response(response(printer_group))
        self.assertEqual(status, 0)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].attributes["queued-job-count"], 3)
        self.assertIs(groups[0].attributes["printer-is-accepting-jobs"], True)
        self.assertEqual(groups[0].attributes["printer-name"], "Office")

    def test_repeated_attribute_values_are_preserved(self):
        group = (
            bytes([ipp.TAG_JOB])
            + ipp._attr(ipp.TAG_KEYWORD, "job-state-reasons", b"queued")
            + ipp._attr(ipp.TAG_KEYWORD, "", b"printer-stopped")
        )
        _, groups = ipp.parse_response(response(group))
        self.assertEqual(
            groups[0].attributes["job-state-reasons"],
            ["queued", "printer-stopped"],
        )

    def test_multiple_groups_remain_separate(self):
        first = bytes([ipp.TAG_JOB]) + ipp._attr(
            ipp.TAG_INTEGER, "job-id", struct.pack(">i", 1)
        )
        second = bytes([ipp.TAG_JOB]) + ipp._attr(
            ipp.TAG_INTEGER, "job-id", struct.pack(">i", 2)
        )
        _, groups = ipp.parse_response(response(first, second))
        self.assertEqual([g.attributes["job-id"] for g in groups], [1, 2])

    def test_short_response_is_rejected(self):
        with self.assertRaises(ipp.CupsProtocolError):
            ipp.parse_response(b"\\x02\\x00")

    def test_missing_end_marker_is_rejected(self):
        with self.assertRaises(ipp.CupsProtocolError):
            ipp.parse_response(b"\\x02\\x00\\x00\\x00\\x00\\x00\\x00\\x01" + bytes([ipp.TAG_JOB]))

    def test_truncated_attribute_is_rejected(self):
        broken = (
            bytes([ipp.TAG_PRINTER])
            + bytes([ipp.TAG_NAME])
            + struct.pack(">H", 12)
            + b"short"
        )
        with self.assertRaises(ipp.CupsProtocolError):
            ipp.parse_response(response(broken))

    def test_truncated_value_is_rejected(self):
        broken = (
            bytes([ipp.TAG_PRINTER])
            + bytes([ipp.TAG_NAME])
            + struct.pack(">H", 4)
            + b"name"
            + struct.pack(">H", 9)
            + b"short"
        )
        with self.assertRaises(ipp.CupsProtocolError):
            ipp.parse_response(response(broken))

    def test_unknown_tag_value_is_hex_encoded(self):
        group = bytes([ipp.TAG_JOB]) + ipp._attr(
            0x35, "unknown", b"\\x01\\xff"
        )
        _, groups = ipp.parse_response(response(group))
        self.assertEqual(groups[0].attributes["unknown"], "01ff")


if __name__ == "__main__":
    unittest.main()
