
"""Binary sensors for CUPS Print Server."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    def available(self) -> bool:
        """Return whether connectivity can be determined."""
        return (
            super().available
            and self._queue_data.get("printer_online")
            is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the physical printer is reachable."""
        return self._queue_data.get("printer_online")
