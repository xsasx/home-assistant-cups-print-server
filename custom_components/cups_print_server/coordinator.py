
"""Data coordinator for CUPS Print Server."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_PORT,
    CONF_USE_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DOMAIN,
)
from .ipp import CupsClient, CupsIppError

_LOGGER = logging.getLogger(__name__)

ACTIVE_JOB_STATES = {3, 4, 5, 6}
COMPLETED_JOB_STATE = 9

# Supported direct network printing protocols.
DEVICE_PORTS = {
    "socket": 9100,
    "ipp": 631,
    "ipps": 631,
    "http": 80,
    "https": 443,
    "lpd": 515,
}

PRINTER_CONNECT_TIMEOUT = 3


def _job_integer(
    job: dict[str, Any],
    key: str,
    default: int = 0,
) -> int:
    """Safely convert a job attribute to an integer."""
    try:
        return int(job.get(key, default))
    except (TypeError, ValueError, OverflowError):
        return default


def _job_sort_key(job: dict[str, Any]) -> int:
    """Return a sortable job ID."""
    return _job_integer(job, "job-id")


def _printer_endpoint(
    printer: dict[str, Any],
) -> tuple[str, int] | None:
    """Extract a supported TCP endpoint from the CUPS device URI."""
    device_uri = printer.get("device-uri")

    if isinstance(device_uri, list):
        device_uri = next(
            (
                value
                for value in device_uri
                if isinstance(value, str)
            ),
            None,
        )

    if not isinstance(device_uri, str):
        return None

    try:
        parsed = urlparse(device_uri)
        scheme = parsed.scheme.lower()

        if scheme not in DEVICE_PORTS:
            return None

        # Do not probe device URIs containing credentials.
        if parsed.username is not None or parsed.password is not None:
            return None

        host = parsed.hostname
        port = parsed.port or DEVICE_PORTS[scheme]

        if not host or not 1 <= port <= 65535:
            return None

        return host, port

    except ValueError:
        return None


async def _async_check_printer(
    endpoint: tuple[str, int],
) -> bool:
    """Check whether the physical printer accepts TCP connections."""
    host, port = endpoint

    writer: asyncio.StreamWriter | None = None

    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=PRINTER_CONNECT_TIMEOUT,
        )
        return True

    except (
        OSError,
        TimeoutError,
        ValueError,
    ):
        return False

    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


class CupsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate CUPS queue and physical printer data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.entry = entry

        self.client = CupsClient(
            async_get_clientsession(hass),
            entry.data["host"],
            entry.data.get(CONF_PORT, DEFAULT_PORT),
            entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=DEFAULT_SCAN_INTERVAL
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch CUPS data and check physical printer connectivity."""
        try:
            queues = await self.client.discover_queues()

        except CupsIppError as err:
            raise UpdateFailed(
                f"Error discovering CUPS queues: {err}"
            ) from err

        previous_queues = (
            self.data.get("queues", {})
            if self.data
            else {}
        )

        data: dict[str, Any] = {"queues": {}}
        successful_queues = 0

        for queue in queues:
            try:
                printer = await self.client.get_printer(queue)
                jobs = await self.client.get_jobs(queue)

                jobs = [
                    job
                    for job in jobs
                    if isinstance(job, dict)
                ]

                jobs.sort(
                    key=_job_sort_key,
                    reverse=True,
                )

                active = [
                    job
                    for job in jobs
                    if _job_integer(job, "job-state")
                    in ACTIVE_JOB_STATES
                ]

                completed = [
                    job
                    for job in jobs
                    if _job_integer(job, "job-state")
                    == COMPLETED_JOB_STATE
                ]

                endpoint = _printer_endpoint(printer)

                # None means the printer cannot be checked
                # using a supported direct TCP connection.
                printer_online: bool | None = None

                if endpoint is not None:
                    printer_online = await _async_check_printer(
                        endpoint
                    )

                data["queues"][queue] = {
                    "printer": printer,
                    "jobs": jobs,
                    "active_jobs": active,
                    "current_job": (
                        active[0] if active else None
                    ),
                    "last_job": (
                        completed[0]
                        if completed
                        else (jobs[0] if jobs else None)
                    ),
                    "printer_online": printer_online,
                }

                successful_queues += 1

            except CupsIppError as err:
                _LOGGER.warning(
                    "Could not update CUPS queue %s: %s",
                    queue,
                    err,
                )

                if queue in previous_queues:
                    previous = previous_queues[queue].copy()

                    # A failed queue update must not present an
                    # old connectivity result as a fresh reading.
                    previous["printer_online"] = None

                    data["queues"][queue] = previous

        if queues and successful_queues == 0:
            raise UpdateFailed(
                "Could not update any CUPS printer queue"
            )

        return data
