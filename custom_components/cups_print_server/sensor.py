
"""Binary sensors for CUPS Print Server."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CupsCoordinator


BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="printer_online",
        translation_key="printer_online",
        name="Printer reachable",
        icon="mdi:printer-check",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS binary sensors."""
    coordinator: CupsCoordinator = entry.runtime_data
    queues = coordinator.data.get("queues", {})

    async_add_entities(
        CupsPrinterBinarySensor(
            coordinator,
            entry,
            queue,
            description,
        )
        for queue in queues
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class CupsPrinterBinarySensor(
    CoordinatorEntity[CupsCoordinator],
    BinarySensorEntity,
):
    """Represent physical printer connectivity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CupsCoordinator,
        entry: ConfigEntry,
        queue: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self.queue = queue
        self.entity_description = description

        self._attr_unique_id = (
            f"{entry.entry_id}_{queue}_{description.key}"
        )

    @property
    def _queue_data(self) -> dict[str, Any]:
        """Return current queue data."""
        return self.coordinator.data.get(
            "queues", {}
        ).get(self.queue, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Associate the sensor with the existing CUPS printer device."""
        entry = self.coordinator.entry
        printer = self._queue_data.get("printer", {})

        scheme = (
            "https"
            if entry.data.get("use_ssl")
            else "http"
        )

        host = entry.data["host"]
        port = entry.data.get("port", 631)
        queue_url = quote(self.queue, safe="")

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{entry.entry_id}_{self.queue}",
                )
            },
            name=printer.get("printer-info") or self.queue,
            manufacturer="CUPS",
            model=(
                printer.get("printer-make-and-model")
                or "CUPS Printer"
            ),
            configuration_url=(
                f"{scheme}://{host}:{port}"
                f"/printers/{queue_url}"
            ),
        )

    @property
    def available(self) -> bool:
        """Return whether connectivity can be determined."""
        return (
            super().available
            and self._queue_data.get("printer_online") is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the physical printer is reachable."""
        return self._queue_data.get("printer_online")
