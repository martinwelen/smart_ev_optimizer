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
    ha_selector = ModuleType("homeassistant.helpers.selector")
    ha_data_entry_flow = ModuleType("homeassistant.data_entry_flow")
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

    # ConfigFlow / OptionsFlow stubs for config_flow.py
    class _FakeConfigFlow:
        """Minimal ConfigFlow stub for testing."""

        VERSION = 1
        DOMAIN = ""

        def __init__(self):
            self.hass = None
            self._site_data: dict = {}
            self._economics_data: dict = {}
            self._power_data: dict = {}

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        @staticmethod
        def async_get_options_flow(config_entry):
            return None

        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            if domain is not None:
                cls.DOMAIN = domain

    class _FakeOptionsFlow:
        """Minimal OptionsFlow stub for testing."""

        def __init__(self, config_entry=None):
            self.config_entry = config_entry
            self.hass = None

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    ha_config_entries.ConfigFlow = _FakeConfigFlow  # type: ignore[attr-defined]
    ha_config_entries.OptionsFlow = _FakeOptionsFlow  # type: ignore[attr-defined]

    # Selector stubs — each returns a no-op validator (passes data through)
    class _SelectorStub:
        """Generic selector that acts as a passthrough for vol schemas."""

        def __init__(self, config=None):
            self.config = config

        def __call__(self, value):
            return value

    class _SelectorConfigStub:
        """Generic selector config dataclass stub."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    ha_selector.EntitySelector = _SelectorStub  # type: ignore[attr-defined]
    ha_selector.EntitySelectorConfig = _SelectorConfigStub  # type: ignore[attr-defined]
    ha_selector.NumberSelector = _SelectorStub  # type: ignore[attr-defined]
    ha_selector.NumberSelectorConfig = _SelectorConfigStub  # type: ignore[attr-defined]
    ha_selector.NumberSelectorMode = type(  # type: ignore[attr-defined]
        "NumberSelectorMode", (), {"BOX": "box", "SLIDER": "slider"}
    )
    ha_selector.TextSelector = _SelectorStub  # type: ignore[attr-defined]
    ha_selector.TextSelectorConfig = _SelectorConfigStub  # type: ignore[attr-defined]
    ha_selector.SelectSelector = _SelectorStub  # type: ignore[attr-defined]
    ha_selector.SelectSelectorConfig = _SelectorConfigStub  # type: ignore[attr-defined]
    ha_selector.SelectSelectorMode = type(  # type: ignore[attr-defined]
        "SelectSelectorMode", (), {"LIST": "list", "DROPDOWN": "dropdown"}
    )
    ha_selector.selector = _SelectorStub  # type: ignore[attr-defined]

    # FlowResult type alias (just a dict)
    ha_data_entry_flow.FlowResult = dict  # type: ignore[attr-defined]

    # CoordinatorEntity stub for entity platforms
    class _FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    ha_update_coord.CoordinatorEntity = _FakeCoordinatorEntity  # type: ignore[attr-defined]

    # Entity platform stubs
    ha_components = ModuleType("homeassistant.components")
    ha_sensor = ModuleType("homeassistant.components.sensor")
    ha_binary_sensor = ModuleType("homeassistant.components.binary_sensor")
    ha_switch = ModuleType("homeassistant.components.switch")
    ha_number = ModuleType("homeassistant.components.number")
    ha_select = ModuleType("homeassistant.components.select")

    class _FakeSensorEntity:
        pass

    class _FakeSensorDeviceClass:
        POWER = "power"
        CURRENT = "current"
        MONETARY = "monetary"

    class _FakeSensorStateClass:
        MEASUREMENT = "measurement"

    ha_sensor.SensorEntity = _FakeSensorEntity  # type: ignore[attr-defined]
    ha_sensor.SensorDeviceClass = _FakeSensorDeviceClass  # type: ignore[attr-defined]
    ha_sensor.SensorStateClass = _FakeSensorStateClass  # type: ignore[attr-defined]

    class _FakeBinarySensorEntity:
        pass

    class _FakeBinarySensorDeviceClass:
        POWER = "power"
        RUNNING = "running"
        BATTERY_CHARGING = "battery_charging"

    ha_binary_sensor.BinarySensorEntity = _FakeBinarySensorEntity  # type: ignore[attr-defined]
    ha_binary_sensor.BinarySensorDeviceClass = _FakeBinarySensorDeviceClass  # type: ignore[attr-defined]

    class _FakeSwitchEntity:
        pass

    class _FakeSwitchDeviceClass:
        SWITCH = "switch"

    ha_switch.SwitchEntity = _FakeSwitchEntity  # type: ignore[attr-defined]
    ha_switch.SwitchDeviceClass = _FakeSwitchDeviceClass  # type: ignore[attr-defined]

    class _FakeNumberEntity:
        pass

    class _FakeNumberDeviceClass:
        POWER = "power"
        BATTERY = "battery"

    class _FakeNumberMode:
        BOX = "box"
        SLIDER = "slider"

    ha_number.NumberEntity = _FakeNumberEntity  # type: ignore[attr-defined]
    ha_number.NumberDeviceClass = _FakeNumberDeviceClass  # type: ignore[attr-defined]
    ha_number.NumberMode = _FakeNumberMode  # type: ignore[attr-defined]

    class _FakeSelectEntity:
        pass

    ha_select.SelectEntity = _FakeSelectEntity  # type: ignore[attr-defined]

    # Helper entity module
    ha_helpers_entity = ModuleType("homeassistant.helpers.entity")

    class _FakeEntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    ha_helpers_entity.EntityCategory = _FakeEntityCategory  # type: ignore[attr-defined]

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_update_coord
    sys.modules["homeassistant.helpers.entity"] = ha_helpers_entity
    sys.modules["homeassistant.helpers.selector"] = ha_selector
    sys.modules["homeassistant.data_entry_flow"] = ha_data_entry_flow
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.sensor"] = ha_sensor
    sys.modules["homeassistant.components.binary_sensor"] = ha_binary_sensor
    sys.modules["homeassistant.components.switch"] = ha_switch
    sys.modules["homeassistant.components.number"] = ha_number
    sys.modules["homeassistant.components.select"] = ha_select
