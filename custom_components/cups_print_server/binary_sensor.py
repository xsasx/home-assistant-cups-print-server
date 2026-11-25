
"""Binary sensors for CUPS Print Server."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
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
from .printer_status import problem_reasons


BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="printer_online",
        translation_key="printer_online",
        icon="mdi:printer-check",
    ),
    BinarySensorEntityDescription(
        key="printer_problem",
        translation_key="printer_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
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
    """Represent printer connectivity or problem state."""

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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{queue}")}
        )

    @property
    def _queue_data(self) -> dict[str, Any]:
        """Return current queue data."""
        return self.coordinator.data.get(
            "queues", {}
        ).get(self.queue, {})

    @property
    def available(self) -> bool:
        """Return whether the state can be determined."""
        if not super().available:
            return False

        if self.entity_description.key == "printer_online":
            return self._queue_data.get("printer_online") is not None

        # Never report alerts from stale queue data.
        return self._queue_data.get("data_fresh") is True

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if self.entity_description.key == "printer_online":
            return self._queue_data.get("printer_online")

        return bool(
            problem_reasons(self._queue_data.get("printer", {}))
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the reasons behind a problem."""
        if self.entity_description.key != "printer_problem":
            return None

        printer = self._queue_data.get("printer", {})

        return {
            "reasons": problem_reasons(printer),
            "state_message": (
                printer.get("printer-state-message") or None
            ),
        }
