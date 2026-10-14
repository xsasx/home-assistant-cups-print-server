"""Power management for CUPS printer smart plugs."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AUTO_POWER_OFF,
    CONF_AUTO_POWER_ON,
    CONF_POWER_OFF_DELAY,
    CONF_POWER_SWITCH,
    DEFAULT_POWER_OFF_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class CupsPowerManager:
    """Manage printer power and idle shutdown."""

    def __init__(self, hass, entry, coordinator):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.idle_since = None
        self._remove_listener = None
        self._task = None
        self._pending_update = False

    @property
    def switch_entity_id(self):
        return self.entry.options.get(CONF_POWER_SWITCH)

    @property
    def auto_on(self):
        return self.entry.options.get(CONF_AUTO_POWER_ON, False)

    @property
    def auto_off(self):
        return self.entry.options.get(CONF_AUTO_POWER_OFF, False)

    @property
    def delay(self):
        return self.entry.options.get(
            CONF_POWER_OFF_DELAY, DEFAULT_POWER_OFF_DELAY
        )

    @property
    def remaining_seconds(self):
        if not self.auto_off or self.idle_since is None:
            return None

        deadline = self.idle_since + timedelta(minutes=self.delay)
        return max(
            0,
            int((deadline - dt_util.utcnow()).total_seconds()),
        )

    async def turn_on(self):
        if self.switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self.switch_entity_id},
                blocking=True,
            )

    async def turn_off(self):
        if self.switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self.switch_entity_id},
                blocking=True,
            )

    def start(self):
        self._remove_listener = self.coordinator.async_add_listener(
            self._on_update
        )
        self._on_update()

    @callback
    def _on_update(self):
        self._pending_update = True
        if self._task is None or self._task.done():
            self._task = self.hass.async_create_task(
                self._process_pending()
            )

    async def _process_pending(self):
        while self._pending_update:
            self._pending_update = False
            try:
                await self._process()
            except Exception:
                _LOGGER.exception(
                    "CUPS printer power management failed"
                )

    async def _process(self):
        if not self.coordinator.last_update_success:
            return

        entity_id = self.switch_entity_id
        if not entity_id:
            self.idle_since = None
            return

        state = self.hass.states.get(entity_id)
        if state is None or state.state not in (STATE_ON, STATE_OFF):
            self.idle_since = None
            return

        queues = self.coordinator.data.get("queues", {})
        if not queues:
            return

        # Never make power decisions using stale queue data.
        if any(
            data.get("data_fresh") is not True
            for data in queues.values()
        ):
            self.idle_since = None
            return

        has_jobs = any(
            data.get("active_jobs")
            for data in queues.values()
        )

        if has_jobs:
            self.idle_since = None
            if self.auto_on and state.state == STATE_OFF:
                await self.turn_on()
            return

        if state.state == STATE_OFF or not self.auto_off:
            self.idle_since = None
            return

        now = dt_util.utcnow()

        if self.idle_since is None:
            self.idle_since = now
            return

        if now - self.idle_since >= timedelta(minutes=self.delay):
            # Confirm current CUPS job state before powering off.
            try:
                fresh_data = await self.coordinator._async_update_data()
            except Exception:
                _LOGGER.warning(
                    "Power-off cancelled: CUPS verification failed"
                )
                self.idle_since = None
                return

            fresh_queues = fresh_data.get("queues", {})

            if not fresh_queues or any(
                not data.get("data_fresh")
                or data.get("active_jobs")
                for data in fresh_queues.values()
            ):
                self.idle_since = None
                return

            await self.turn_off()
            self.idle_since = None

    async def stop(self):
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

        self._pending_update = False

        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
