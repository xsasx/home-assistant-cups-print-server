
"""Sensors for CUPS Print Server."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CupsCoordinator


SENSOR_DEFINITIONS = (
    ("printer_state", "mdi:printer"),
    ("queued_jobs", "mdi:printer-alert"),
    ("current_job", "mdi:file-document-outline"),
    ("current_job_id", "mdi:identifier"),
    ("current_job_state", "mdi:progress-clock"),
    ("pages_completed", "mdi:file-document-check-outline"),
    ("last_job", "mdi:history"),
    ("last_job_time", "mdi:clock-outline"),
)

PRINTER_STATES = {
    3: "idle",
    4: "processing",
    5: "stopped",
}

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
    "idle",
    *JOB_STATES.values(),
    "unknown",
]


def _integer(value: Any) -> int | None:
    """Convert IPP values to integers."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _job_name(job: dict[str, Any] | None) -> str | None:
    """Return a human-readable job name."""
    if not job:
        return None

    return (
        job.get("job-name")
        or job.get("document-name-supplied")
        or str(job.get("job-id", "Unknown"))
    )


def _job_timestamp(job: dict[str, Any] | None) -> datetime | None:
    """Return the best available job timestamp."""
    if not job:
        return None

    for key in (
        "date-time-at-completed",
        "date-time-at-processing",
        "date-time-at-creation",
    ):
        value = job.get(key)

        if isinstance(value, datetime):
            return (
                value.replace(tzinfo=timezone.utc)
                if value.tzinfo is None
                else value
            )

        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
                return (
                    parsed.replace(tzinfo=timezone.utc)
                    if parsed.tzinfo is None
                    else parsed
                )
            except ValueError:
                continue

    for key in (
        "time-at-completed",
        "time-at-processing",
        "time-at-creation",
    ):
        value = _integer(job.get(key))

        if value is not None and value > 0:
            try:
                return datetime.fromtimestamp(
                    value,
                    tz=timezone.utc,
                )
            except (ValueError, OverflowError, OSError):
                continue

    return None


class CupsSensor(CoordinatorEntity[CupsCoordinator], SensorEntity):
    """Represent a CUPS printer sensor."""

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

        # Preserve existing entity registry identifiers.
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{queue}_{key}"
        )

        if key == "last_job_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

        elif key == "printer_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [
                "idle",
                "processing",
                "stopped",
                "unknown",
            ]

        elif key == "current_job_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = JOB_STATE_OPTIONS

    @property
    def _queue_data(self) -> dict[str, Any]:
        """Return data for this queue."""
        return self.coordinator.data["queues"][self.queue]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        printer = self._queue_data["printer"]

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.coordinator.entry.entry_id}_{self.queue}",
                )
            },
            name=printer.get("printer-info") or self.queue,
            manufacturer="CUPS",
            model=(
                printer.get("printer-make-and-model")
                or "CUPS Printer"
            ),
            configuration_url=(
                f"http://{self.coordinator.entry.data['host']}:"
                f"{self.coordinator.entry.data.get('port', 631)}"
                f"/printers/{quote(self.queue, safe='')}"
            ),
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        queue_data = self._queue_data
        printer = queue_data["printer"]
        current_job = queue_data.get("current_job")
        last_job = queue_data.get("last_job")

        if self.key == "printer_state":
            state = _integer(printer.get("printer-state"))
            return PRINTER_STATES.get(state, "unknown")

        if self.key == "queued_jobs":
            return (
                _integer(printer.get("queued-job-count"))
                or 0
            )

        if self.key == "current_job":
            return _job_name(current_job) or "Kein Druckauftrag"

        if self.key == "current_job_id":
            if not current_job:
                return 0

            return _integer(current_job.get("job-id")) or 0

        if self.key == "current_job_state":
            if not current_job:
                return "idle"

            state = _integer(current_job.get("job-state"))
            return JOB_STATES.get(state, "unknown")

        if self.key == "pages_completed":
            if not current_job:
                return 0

            return (
                _integer(
                    current_job.get("job-media-sheets-completed")
                )
                or _integer(
                    current_job.get("job-impressions-completed")
                )
                or 0
            )

        if self.key == "last_job":
            return _job_name(last_job)

        if self.key == "last_job_time":
            return _job_timestamp(last_job)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        queue_data = self._queue_data

        return {
            "queue": self.queue,
            "printer_state": queue_data["printer"].get(
                "printer-state"
            ),
            "active_jobs": len(
                queue_data.get("active_jobs", [])
            ),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS sensors from a config entry."""
    coordinator: CupsCoordinator = entry.runtime_data

    entities = [
        CupsSensor(coordinator, queue, key, icon)
        for queue in coordinator.data["queues"]
        for key, icon in SENSOR_DEFINITIONS
    ]

    async_add_entities(entities)
