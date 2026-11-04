"""Regression tests for CUPS smart-plug power safety decisions."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "cups_print_server"


def load_power_module():
    """Load production power.py with minimal Home Assistant API stubs."""
    ha = types.ModuleType("homeassistant")
    ha.__path__ = []
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.STATE_OFF = "off"
    ha_const.STATE_ON = "on"
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.callback = lambda fn: fn
    ha_util = types.ModuleType("homeassistant.util")
    ha_util.__path__ = []
    ha_dt = types.ModuleType("homeassistant.util.dt")
    from datetime import datetime, timezone
    ha_dt.utcnow = lambda: datetime.now(timezone.utc)

    package = types.ModuleType("_cups_power_tests")
    package.__path__ = [str(ROOT)]
    spec_const = importlib.util.spec_from_file_location(
        "_cups_power_tests.const", ROOT / "const.py"
    )
    const = importlib.util.module_from_spec(spec_const)
    spec_const.loader.exec_module(const)

    modules = {
        "homeassistant": ha,
        "homeassistant.const": ha_const,
        "homeassistant.core": ha_core,
        "homeassistant.util": ha_util,
        "homeassistant.util.dt": ha_dt,
        "_cups_power_tests": package,
        "_cups_power_tests.const": const,
    }
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(
            "_cups_power_tests.power", ROOT / "power.py"
        )
        power = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(power)
    return power, const


power, const = load_power_module()


class TestPowerSafety(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.services = Mock()
        self.services.async_call = AsyncMock()
        self.hass = Mock()
        self.hass.services = self.services
        self.hass.states.get.return_value = Mock(state="on")
        self.entry = Mock()
        self.entry.options = {
            const.CONF_POWER_SWITCH: "switch.printer",
            const.CONF_AUTO_POWER_ON: True,
            const.CONF_AUTO_POWER_OFF: True,
            const.CONF_POWER_OFF_DELAY: 15,
        }
        self.coordinator = Mock()
        self.coordinator.last_update_success = True
        self.coordinator.data = {
            "queues": {"printer": {"data_fresh": True, "active_jobs": []}}
        }
        self.coordinator._async_update_data = AsyncMock(
            return_value=self.coordinator.data
        )
        self.manager = power.CupsPowerManager(
            self.hass, self.entry, self.coordinator
        )

    def assert_no_power_action(self):
        self.services.async_call.assert_not_awaited()

    async def test_active_job_prevents_power_off(self):
        self.coordinator.data["queues"]["printer"]["active_jobs"] = [{"job-id": 1}]
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        await self.manager._process()
        self.assert_no_power_action()
        self.assertIsNone(self.manager.idle_since)

    async def test_active_job_powers_on_disabled_printer(self):
        self.hass.states.get.return_value.state = "off"
        self.coordinator.data["queues"]["printer"]["active_jobs"] = [{"job-id": 1}]
        await self.manager._process()
        self.services.async_call.assert_awaited_once_with(
            "switch", "turn_on", {"entity_id": "switch.printer"}, blocking=True
        )

    async def test_no_shutdown_before_idle_delay(self):
        await self.manager._process()
        self.assertIsNotNone(self.manager.idle_since)
        await self.manager._process()
        self.assert_no_power_action()

    async def test_idle_shutdown_requires_fresh_verification(self):
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(minutes=16)
        await self.manager._process()
        self.coordinator._async_update_data.assert_awaited_once()
        self.services.async_call.assert_awaited_once_with(
            "switch", "turn_off", {"entity_id": "switch.printer"}, blocking=True
        )

    async def test_new_job_during_final_check_prevents_shutdown(self):
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(minutes=16)
        self.coordinator._async_update_data.return_value = {
            "queues": {"printer": {"data_fresh": True, "active_jobs": [{"job-id": 2}]}}
        }
        await self.manager._process()
        self.assert_no_power_action()

    async def test_stale_queue_prevents_power_action(self):
        self.coordinator.data["queues"]["printer"]["data_fresh"] = False
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        await self.manager._process()
        self.assert_no_power_action()
        self.assertIsNone(self.manager.idle_since)

    async def test_failed_final_verification_prevents_shutdown(self):
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        self.coordinator._async_update_data.side_effect = RuntimeError("CUPS offline")
        await self.manager._process()
        self.assert_no_power_action()
        self.assertIsNone(self.manager.idle_since)

    async def test_unavailable_switch_prevents_power_action(self):
        self.hass.states.get.return_value.state = "unavailable"
        await self.manager._process()
        self.assert_no_power_action()

    async def test_failed_coordinator_update_prevents_power_action(self):
        self.coordinator.last_update_success = False
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        await self.manager._process()
        self.assert_no_power_action()

    async def test_auto_off_disabled_prevents_shutdown(self):
        self.entry.options[const.CONF_AUTO_POWER_OFF] = False
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        await self.manager._process()
        self.assert_no_power_action()

    async def test_stale_data_on_any_queue_prevents_shutdown(self):
        self.coordinator.data["queues"]["second"] = {
            "data_fresh": False, "active_jobs": []
        }
        self.manager.idle_since = power.dt_util.utcnow() - timedelta(hours=1)
        await self.manager._process()
        self.assert_no_power_action()

    async def test_no_power_switch_configured(self):
        self.entry.options.pop(const.CONF_POWER_SWITCH)
        await self.manager._process()
        self.assert_no_power_action()


if __name__ == "__main__":
    unittest.main()
