"""Sensor platform for CUPS Print Server."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CupsCoordinator

PRINTER_STATES = {
    3: "idle",
    4: "processing",
    5: "stopped",
}

PRINTER_STATE_OPTIONS = [
    "idle",
    "processing",
    "stopped",
    "unknown",
]

JOB_STATES = {
    3: "pending",
    4: "pending_held",
    5: "processing",
    6: "processing_stopped",
    7: "canceled",
    8: "aborted",
    9: "completed",
}

JOB_STATE_OPTIONS = [
    "pending",
    "pending_held",
    "processing",
    "processing_stopped",
    "canceled",
    "aborted",
    "completed",
    "unknown",
]


def _job_name(job: dict[str, Any] | None) -> str | None:
    """Return the best available display name for a print job."""
    if not job:
        return None

    return (
        job.get("job-name")
        or job.get("document-name-supplied")
        or (
            f"Job {job.get('job-id')}"
            if job.get("job-id") is not None
            else None
        )
    )


def _parse_datetime(value: Any) -> datetime | None:
    """Convert an IPP date/time value into a Home Assistant timestamp."""
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class CupsSensor(CoordinatorEntity[CupsCoordinator], SensorEntity):
    """Representation of a CUPS sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CupsCoordinator,
        queue: str,
        key: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.queue = queue
        self.key = key

        self._attr_translation_key = key
        self._attr_icon = icon
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{queue}_{key}"
        )

        if key == "last_job_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

        elif key == "printer_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = PRINTER_STATE_OPTIONS

        elif key == "current_job_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = JOB_STATE_OPTIONS

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.coordinator.data["queues"][self.queue]["printer"]

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.coordinator.entry.entry_id}_{self.queue}",
                )
            },
            name=data.get("printer-info") or self.queue,
            manufacturer="CUPS",
            model=data.get("printer-make-and-model") or "CUPS Printer",
            configuration_url=(
                f"{'https' if self.coordinator.entry.data.get('use_ssl') else 'http'}://"
                f"{self.coordinator.entry.data['host']}:"
                f"{self.coordinator.entry.data.get('port', 631)}"
                f"/printers/{self.queue}"
            ),
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        queue_data = self.coordinator.data["queues"][self.queue]

        printer = queue_data["printer"]
        current = queue_data["current_job"]
        last = queue_data["last_job"]

        if self.key == "printer_state":
            try:
                state = int(printer.get("printer-state", 0))
            except (TypeError, ValueError):
                return "unknown"

            return PRINTER_STATES.get(state, "unknown")

        if self.key == "queued_jobs":
            return int(
                printer.get(
                    "queued-job-count",
                    len(queue_data["active_jobs"]),
                )
            )

        if self.key == "current_job":
            return _job_name(current)

        if self.key == "current_job_id":
            return current.get("job-id") if current else None

        if self.key == "current_job_state":
            if not current:
                return None

            try:
                state = int(current.get("job-state", 0))
            except (TypeError, ValueError):
                return "unknown"

            return JOB_STATES.get(state, "unknown")

        if self.key == "pages_completed":
            if not current:
                return None

            return current.get(
                "job-media-sheets-completed",
                current.get("job-impressions-completed"),
            )

        if self.key == "last_job":
            return _job_name(last)

        if self.key == "last_job_time":
            if not last:
                return None

            value = (
                last.get("date-time-at-completed")
                or last.get("date-time-at-processing")
                or last.get("date-time-at-creation")
            )

            return _parse_datetime(value)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional job attributes."""
        queue_data = self.coordinator.data["queues"][self.queue]

        if self.key in (
            "current_job",
            "current_job_id",
            "current_job_state",
            "pages_completed",
        ):
            job = queue_data["current_job"]
        else:
            job = queue_data["last_job"]

        if self.key not in ("current_job", "last_job") or not job:
            return None

        keys = (
            "job-id",
            "job-state",
            "job-state-reasons",
            "job-originating-user-name",
            "document-name-supplied",
            "document-format",
            "job-k-octets",
            "copies",
            "media",
            "PageSize",
            "print-color-mode",
            "ColorModel",
            "sides",
            "job-impressions-completed",
            "job-media-sheets-completed",
            "date-time-at-creation",
            "date-time-at-processing",
            "date-time-at-completed",
        )

        return {
            key: job[key]
            for key in keys
            if key in job
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS sensors."""
    coordinator: CupsCoordinator = entry.runtime_data

    entities: list[CupsSensor] = []

    definitions = [
        ("printer_state", "mdi:printer"),
        ("queued_jobs", "mdi:format-list-numbered"),
        ("current_job", "mdi:file-document-outline"),
        ("current_job_id", "mdi:identifier"),
        ("current_job_state", "mdi:progress-clock"),
        ("pages_completed", "mdi:file-document-multiple-outline"),
        ("last_job", "mdi:history"),
        ("last_job_time", "mdi:clock-outline"),
    ]

    for queue in coordinator.data["queues"]:
        entities.extend(
            CupsSensor(
                coordinator,
                queue,
                key,
                icon,
            )
            for key, icon in definitions
        )

    async_add_entities(entities)
