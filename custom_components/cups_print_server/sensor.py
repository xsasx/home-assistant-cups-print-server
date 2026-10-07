"""Sensor platform for CUPS Print Server."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CupsCoordinator

PRINTER_STATES = {3: "idle", 4: "processing", 5: "stopped"}
JOB_STATES = {
    3: "pending",
    4: "pending_held",
    5: "processing",
    6: "processing_stopped",
    7: "canceled",
    8: "aborted",
    9: "completed",
}


def _job_name(job: dict[str, Any] | None) -> str | None:
    if not job:
        return None
    return (
        job.get("job-name")
        or job.get("document-name-supplied")
        or (f"Job {job.get('job-id')}" if job.get("job-id") is not None else None)
    )


class CupsSensor(CoordinatorEntity[CupsCoordinator], SensorEntity):
    """Base CUPS sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CupsCoordinator, queue: str, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self.queue = queue
        self.key = key
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{queue}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data["queues"][self.queue]["printer"]
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.entry.entry_id}_{self.queue}")},
            name=data.get("printer-info") or self.queue,
            manufacturer="CUPS",
            model=data.get("printer-make-and-model") or "CUPS Printer",
            configuration_url=(
                f"{'https' if self.coordinator.entry.data.get('use_ssl') else 'http'}://"
                f"{self.coordinator.entry.data['host']}:{self.coordinator.entry.data.get('port', 631)}"
                f"/printers/{self.queue}"
            ),
        )

    @property
    def native_value(self) -> Any:
        q = self.coordinator.data["queues"][self.queue]
        printer = q["printer"]
        current = q["current_job"]
        last = q["last_job"]

        if self.key == "printer_state":
            return PRINTER_STATES.get(int(printer.get("printer-state", 0)), str(printer.get("printer-state", "unknown")))
        if self.key == "queued_jobs":
            return int(printer.get("queued-job-count", len(q["active_jobs"])))
        if self.key == "current_job":
            return _job_name(current)
        if self.key == "current_job_id":
            return current.get("job-id") if current else None
        if self.key == "current_job_state":
            return JOB_STATES.get(int(current.get("job-state", 0)), "unknown") if current else None
        if self.key == "pages_completed":
            return current.get("job-media-sheets-completed", current.get("job-impressions-completed")) if current else None
        if self.key == "last_job":
            return _job_name(last)
        if self.key == "last_job_time":
            if not last:
                return None
            return last.get("date-time-at-completed") or last.get("date-time-at-processing") or last.get("date-time-at-creation")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        q = self.coordinator.data["queues"][self.queue]
        job = q["current_job"] if self.key.startswith("current_job") or self.key == "pages_completed" else q["last_job"]
        if self.key not in ("current_job", "last_job") or not job:
            return None
        keys = (
            "job-id", "job-state", "job-state-reasons", "job-originating-user-name",
            "document-name-supplied", "document-format", "job-k-octets", "copies",
            "media", "PageSize", "print-color-mode", "ColorModel", "sides",
            "job-impressions-completed", "job-media-sheets-completed",
            "date-time-at-creation", "date-time-at-processing", "date-time-at-completed",
        )
        return {k: job[k] for k in keys if k in job}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS sensors."""
    coordinator: CupsCoordinator = entry.runtime_data
    entities: list[CupsSensor] = []

    definitions = [
        ("printer_state", "Status", "mdi:printer"),
        ("queued_jobs", "Queued jobs", "mdi:format-list-numbered"),
        ("current_job", "Current job", "mdi:file-document-outline"),
        ("current_job_id", "Current job ID", "mdi:identifier"),
        ("current_job_state", "Current job status", "mdi:progress-clock"),
        ("pages_completed", "Pages completed", "mdi:file-document-multiple-outline"),
        ("last_job", "Last job", "mdi:history"),
        ("last_job_time", "Last print time", "mdi:clock-outline"),
    ]

    for queue in coordinator.data["queues"]:
        entities.extend(
            CupsSensor(coordinator, queue, key, name, icon)
            for key, name, icon in definitions
        )

    async_add_entities(entities)
