"""Data coordinator for CUPS Print Server."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PORT, CONF_USE_SSL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_USE_SSL, DOMAIN
from .ipp import CupsClient, CupsIppError

_LOGGER = logging.getLogger(__name__)


class CupsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate polling of a CUPS server."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
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
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            queues = await self.client.discover_queues()
            data: dict[str, Any] = {"queues": {}}
            for queue in queues:
                printer = await self.client.get_printer(queue)
                jobs = await self.client.get_jobs(queue)
                jobs.sort(key=lambda item: int(item.get("job-id", 0)), reverse=True)
                active = [j for j in jobs if int(j.get("job-state", 0)) in (3, 4, 5, 6)]
                completed = [j for j in jobs if int(j.get("job-state", 0)) == 9]
                data["queues"][queue] = {
                    "printer": printer,
                    "jobs": jobs,
                    "active_jobs": active,
                    "current_job": active[0] if active else None,
                    "last_job": completed[0] if completed else (jobs[0] if jobs else None),
                }
            return data
        except CupsIppError as err:
            raise UpdateFailed(f"Error communicating with CUPS: {err}") from err
