
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
from .printer_alerts import problem_reasons


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

    async_add_entities(
        CupsPrinterProblemSensor(coordinator, entry, queue)
        for queue in queues
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


class CupsPrinterProblemSensor(
    CoordinatorEntity[CupsCoordinator],
    BinarySensorEntity,
):
    """Report printer alerts such as low toner, empty tray or paused queue."""

    _attr_has_entity_name = True
    _attr_translation_key = "printer_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: CupsCoordinator,
        entry: ConfigEntry,
        queue: str,
    ) -> None:
        super().__init__(coordinator)

        self.queue = queue

        self._attr_unique_id = f"{entry.entry_id}_{queue}_printer_problem"
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
        """Never report alerts from stale queue data."""
        return (
            super().available
            and self._queue_data.get("data_fresh") is True
        )

    @property
    def is_on(self) -> bool:
        """Return whether CUPS reports a printer problem."""
        return bool(
            problem_reasons(self._queue_data.get("printer", {}))
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the reasons behind a problem."""
        printer = self._queue_data.get("printer", {})

        return {
            "reasons": problem_reasons(printer),
            "state_message": (
                printer.get("printer-state-message") or None
            ),
        }
