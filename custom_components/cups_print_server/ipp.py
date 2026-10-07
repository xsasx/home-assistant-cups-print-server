"""Minimal asynchronous IPP client for CUPS.

This module intentionally uses Home Assistant's aiohttp session and has no
external Python dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientError, ClientSession

IPP_VERSION = b"\x02\x00"

OP_GET_PRINTER_ATTRIBUTES = 0x000B
OP_GET_JOBS = 0x000A

STATUS_OK_MAX = 0x00FF

TAG_OPERATION = 0x01
TAG_JOB = 0x02
TAG_END = 0x03
TAG_PRINTER = 0x04

TAG_INTEGER = 0x21
TAG_BOOLEAN = 0x22
TAG_ENUM = 0x23
TAG_DATETIME = 0x31
TAG_TEXT = 0x41
TAG_NAME = 0x42
TAG_KEYWORD = 0x44
TAG_URI = 0x45
TAG_CHARSET = 0x47
TAG_LANGUAGE = 0x48
TAG_MIMETYPE = 0x49

STRING_TAGS = {
    TAG_TEXT, TAG_NAME, TAG_KEYWORD, TAG_URI, TAG_CHARSET, TAG_LANGUAGE,
    TAG_MIMETYPE,
}


class CupsIppError(Exception):
    """Base CUPS IPP error."""


class CupsConnectionError(CupsIppError):
    """Connection to CUPS failed."""


class CupsProtocolError(CupsIppError):
    """Invalid or unsuccessful IPP response."""


@dataclass(slots=True)
class IppGroup:
    """Parsed IPP attribute group."""

    tag: int
    attributes: dict[str, Any]


def _attr(tag: int, name: str, value: bytes) -> bytes:
    name_b = name.encode("utf-8")
    return bytes([tag]) + struct.pack(">H", len(name_b)) + name_b + struct.pack(">H", len(value)) + value


def _request(operation: int, uri_name: str, uri: str, requested: list[str], *, all_jobs: bool = False) -> bytes:
    payload = bytearray()
    payload += IPP_VERSION
    payload += struct.pack(">H", operation)
    payload += struct.pack(">I", 1)
    payload += bytes([TAG_OPERATION])
    payload += _attr(TAG_CHARSET, "attributes-charset", b"utf-8")
    payload += _attr(TAG_LANGUAGE, "attributes-natural-language", b"en")
    payload += _attr(TAG_URI, uri_name, uri.encode())
    if all_jobs:
        payload += _attr(TAG_KEYWORD, "which-jobs", b"all")
        payload += _attr(TAG_BOOLEAN, "my-jobs", b"\x00")
    for idx, name in enumerate(requested):
        payload += _attr(TAG_KEYWORD, "requested-attributes" if idx == 0 else "", name.encode())
    payload += bytes([TAG_END])
    return bytes(payload)


def _decode(tag: int, raw: bytes) -> Any:
    if tag in (TAG_INTEGER, TAG_ENUM) and len(raw) == 4:
        return struct.unpack(">i", raw)[0]
    if tag == TAG_BOOLEAN and raw:
        return raw[0] != 0
    if tag == TAG_DATETIME and len(raw) >= 11:
        year = struct.unpack(">H", raw[:2])[0]
        month, day, hour, minute, second, deci = raw[2:8]
        direction = chr(raw[8])
        off_h, off_m = raw[9], raw[10]
        return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}{direction}{off_h:02d}:{off_m:02d}"
    if tag in STRING_TAGS:
        return raw.decode("utf-8", errors="replace")
    return raw.hex()


def _store(attrs: dict[str, Any], name: str, value: Any) -> None:
    if name not in attrs:
        attrs[name] = value
    elif isinstance(attrs[name], list):
        attrs[name].append(value)
    else:
        attrs[name] = [attrs[name], value]


def parse_response(data: bytes) -> tuple[int, list[IppGroup]]:
    """Parse an IPP response into groups."""
    if len(data) < 9:
        raise CupsProtocolError("IPP response is too short")

    status = struct.unpack(">H", data[2:4])[0]
    pos = 8
    groups: list[IppGroup] = []
    current: IppGroup | None = None
    last_name = ""

    while pos < len(data):
        tag = data[pos]
        pos += 1

        if tag == TAG_END:
            break

        if tag in (TAG_OPERATION, TAG_JOB, TAG_PRINTER):
            current = IppGroup(tag, {})
            groups.append(current)
            last_name = ""
            continue

        if current is None or pos + 2 > len(data):
            raise CupsProtocolError("Malformed IPP response")

        name_len = struct.unpack(">H", data[pos:pos+2])[0]
        pos += 2
        if pos + name_len + 2 > len(data):
            raise CupsProtocolError("Malformed IPP attribute")
        if name_len:
            last_name = data[pos:pos+name_len].decode("utf-8", errors="replace")
        pos += name_len

        value_len = struct.unpack(">H", data[pos:pos+2])[0]
        pos += 2
        if pos + value_len > len(data):
            raise CupsProtocolError("Malformed IPP value")
        raw = data[pos:pos+value_len]
        pos += value_len

        if last_name:
            _store(current.attributes, last_name, _decode(tag, raw))

    return status, groups


class CupsClient:
    """Small async CUPS client using IPP."""

    def __init__(self, session: ClientSession, host: str, port: int = 631, use_ssl: bool = False) -> None:
        self.session = session
        self.host = host.strip().strip("/")
        self.port = port
        self.use_ssl = use_ssl
        self.scheme = "ipps" if use_ssl else "ipp"
        self.http_scheme = "https" if use_ssl else "http"

    def _http_url(self, path: str) -> str:
        return f"{self.http_scheme}://{self.host}:{self.port}{path}"

    def _ipp_uri(self, path: str) -> str:
        return f"{self.scheme}://{self.host}:{self.port}{path}"

    async def _post(self, path: str, body: bytes) -> list[IppGroup]:
        try:
            async with self.session.post(
                self._http_url(path),
                data=body,
                headers={"Content-Type": "application/ipp"},
                timeout=10,
                ssl=False if self.use_ssl else None,
            ) as response:
                response.raise_for_status()
                raw = await response.read()
        except (ClientError, TimeoutError) as err:
            raise CupsConnectionError(str(err)) from err

        status, groups = parse_response(raw)
        if status > STATUS_OK_MAX:
            raise CupsProtocolError(f"CUPS returned IPP status 0x{status:04x}")
        return groups

    async def get_printer(self, queue: str) -> dict[str, Any]:
        path = f"/printers/{queue}"
        body = _request(
            OP_GET_PRINTER_ATTRIBUTES,
            "printer-uri",
            self._ipp_uri(path),
            [
                "printer-name", "printer-info", "printer-location",
                "printer-state", "printer-state-message", "printer-state-reasons",
                "printer-make-and-model", "queued-job-count",
                "printer-is-accepting-jobs", "color-supported",
            ],
        )
        groups = await self._post(path, body)
        for group in groups:
            if group.tag == TAG_PRINTER:
                return group.attributes
        raise CupsProtocolError("No printer attributes returned")

    async def get_jobs(self, queue: str) -> list[dict[str, Any]]:
        path = f"/printers/{queue}"
        body = _request(
            OP_GET_JOBS,
            "printer-uri",
            self._ipp_uri(path),
            [
                "job-id", "job-uri", "job-name", "job-state", "job-state-reasons",
                "job-originating-user-name", "document-name-supplied",
                "document-format", "document-format-supplied",
                "job-impressions", "job-impressions-completed",
                "job-media-sheets", "job-media-sheets-completed",
                "job-k-octets", "copies", "media", "PageSize",
                "print-color-mode", "ColorModel", "sides",
                "date-time-at-creation", "date-time-at-processing",
                "date-time-at-completed",
            ],
            all_jobs=True,
        )
        groups = await self._post(path, body)
        return [group.attributes for group in groups if group.tag == TAG_JOB]

    async def discover_queues(self) -> list[str]:
        """Discover CUPS queues from the root printer collection.

        CUPS accepts Get-Printer-Attributes only for a queue, so use its
        standards-based /printers page solely to obtain queue links.
        """
        try:
            async with self.session.get(
                self._http_url("/printers/"),
                timeout=10,
                ssl=False if self.use_ssl else None,
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except (ClientError, TimeoutError) as err:
            raise CupsConnectionError(str(err)) from err

        # CUPS' own printer page exposes queues as /printers/<queue>.
        import re
        queues = {
            match.group(1)
            for match in re.finditer(r'href=["\']/printers/([^/"\'?#]+)', html, re.I)
        }
        return sorted(queues)
