"""Shared test fixtures for Smart EV Optimizer."""
import datetime
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Shim datetime.UTC for Python < 3.11 (project targets 3.12, CI uses 3.12).
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # type: ignore[attr-defined]  # noqa: UP017

# Mock homeassistant packages so tests can run without HA installed.
# CI uses pytest-homeassistant-custom-component which provides real stubs;
# locally we just need enough for the package __init__.py to import.
if "homeassistant" not in sys.modules:
    ha = ModuleType("homeassistant")
    ha_core = ModuleType("homeassistant.core")
    ha_config_entries = ModuleType("homeassistant.config_entries")
    ha_helpers = ModuleType("homeassistant.helpers")
    ha_update_coord = ModuleType("homeassistant.helpers.update_coordinator")
    ha_core.HomeAssistant = MagicMock  # type: ignore[attr-defined]
    ha_config_entries.ConfigEntry = type("ConfigEntry", (), {})  # type: ignore[attr-defined]

    # DataUpdateCoordinator stub for coordinator.py
    class _FakeDataUpdateCoordinator:
        def __init__(self, hass, logger, *, name, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None

        def __class_getitem__(cls, item):
            return cls

    ha_update_coord.DataUpdateCoordinator = _FakeDataUpdateCoordinator  # type: ignore[attr-defined]
    ha_update_coord.UpdateFailed = type("UpdateFailed", (Exception,), {})  # type: ignore[attr-defined]

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_update_coord
