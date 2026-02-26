"""Tests for Smart EV Optimizer config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_ev_optimizer.const import (
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXPORT_COMPENSATION,
    CONF_GRID_FEE_EXPORT,
    CONF_GRID_FEE_IMPORT,
    CONF_GRID_REWARDS_ENTITY,
    CONF_GRID_SENSOR,
    CONF_NORDPOOL_SENSOR,
    CONF_POWER_LIMIT_KW,
    CONF_SOLAR_SENSOR,
    CONF_VAT_RATE,
    CONF_VEHICLE_CHARGER_ENTITY,
    CONF_VEHICLE_DEPARTURE_ENTITY,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_PRIORITY,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VEHICLE_TARGET_SOC,
    CONF_VEHICLES,
    DEFAULT_POWER_LIMIT_KW,
    DEFAULT_TARGET_SOC,
    DEFAULT_VAT_RATE,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SITE_DATA = {
    CONF_GRID_SENSOR: "sensor.grid_power",
    CONF_SOLAR_SENSOR: "sensor.solar_power",
    CONF_BATTERY_POWER_SENSOR: "sensor.battery_power",
    CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
    CONF_NORDPOOL_SENSOR: "sensor.nordpool",
    CONF_GRID_REWARDS_ENTITY: "",
}

ECONOMICS_DATA = {
    CONF_GRID_FEE_IMPORT: 0.40,
    CONF_GRID_FEE_EXPORT: 0.05,
    CONF_EXPORT_COMPENSATION: 0.10,
    CONF_VAT_RATE: 0.25,
}

POWER_DATA = {
    CONF_POWER_LIMIT_KW: 11.0,
}

VEHICLE_DATA = {
    CONF_VEHICLE_NAME: "Family Car",
    CONF_VEHICLE_PRIORITY: 1,
    CONF_VEHICLE_CHARGER_ENTITY: "sensor.easee_status",
    CONF_VEHICLE_SOC_ENTITY: "sensor.car_soc",
    CONF_VEHICLE_TARGET_SOC: 80,
    CONF_VEHICLE_DEPARTURE_ENTITY: "",
}


# ---------------------------------------------------------------------------
# Import / existence tests
# ---------------------------------------------------------------------------


def test_config_flow_import():
    """Verify config flow module can be imported."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    assert SmartEVOptimizerConfigFlow.VERSION == 1


def test_config_flow_has_required_steps():
    """Verify all required step methods exist."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    assert hasattr(flow, "async_step_user")
    assert hasattr(flow, "async_step_economics")
    assert hasattr(flow, "async_step_power")
    assert hasattr(flow, "async_step_vehicle")


def test_config_flow_domain():
    """Config flow must declare the correct DOMAIN."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    assert SmartEVOptimizerConfigFlow.DOMAIN == DOMAIN


# ---------------------------------------------------------------------------
# assemble_config_data helper
# ---------------------------------------------------------------------------


def test_assemble_config_data():
    """Test the helper that assembles final config from all steps."""
    from custom_components.smart_ev_optimizer.config_flow import assemble_config_data

    result = assemble_config_data(
        SITE_DATA, ECONOMICS_DATA, POWER_DATA, [VEHICLE_DATA]
    )

    # Site sensors
    assert result[CONF_GRID_SENSOR] == "sensor.grid_power"
    assert result[CONF_SOLAR_SENSOR] == "sensor.solar_power"
    assert result[CONF_BATTERY_POWER_SENSOR] == "sensor.battery_power"
    assert result[CONF_BATTERY_SOC_SENSOR] == "sensor.battery_soc"
    assert result[CONF_NORDPOOL_SENSOR] == "sensor.nordpool"
    assert result[CONF_GRID_REWARDS_ENTITY] == ""

    # Economics
    assert result[CONF_GRID_FEE_IMPORT] == 0.40
    assert result[CONF_GRID_FEE_EXPORT] == 0.05
    assert result[CONF_EXPORT_COMPENSATION] == 0.10
    assert result[CONF_VAT_RATE] == 0.25

    # Power
    assert result[CONF_POWER_LIMIT_KW] == 11.0

    # Vehicles
    assert len(result[CONF_VEHICLES]) == 1
    assert result[CONF_VEHICLES][0][CONF_VEHICLE_NAME] == "Family Car"
    assert result[CONF_VEHICLES][0][CONF_VEHICLE_PRIORITY] == 1
    assert result[CONF_VEHICLES][0][CONF_VEHICLE_TARGET_SOC] == 80


def test_assemble_config_data_multiple_vehicles():
    """Config data should support multiple vehicles."""
    from custom_components.smart_ev_optimizer.config_flow import assemble_config_data

    second_vehicle = {
        CONF_VEHICLE_NAME: "Work Van",
        CONF_VEHICLE_PRIORITY: 2,
        CONF_VEHICLE_CHARGER_ENTITY: "sensor.charger_2",
        CONF_VEHICLE_SOC_ENTITY: "",
        CONF_VEHICLE_TARGET_SOC: 90,
        CONF_VEHICLE_DEPARTURE_ENTITY: "",
    }
    result = assemble_config_data(
        SITE_DATA, ECONOMICS_DATA, POWER_DATA, [VEHICLE_DATA, second_vehicle]
    )
    assert len(result[CONF_VEHICLES]) == 2
    assert result[CONF_VEHICLES][1][CONF_VEHICLE_NAME] == "Work Van"
    assert result[CONF_VEHICLES][1][CONF_VEHICLE_PRIORITY] == 2


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


def test_site_schema_accepts_valid_data():
    """Site step schema should accept valid entity IDs."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_SITE_SCHEMA

    result = STEP_SITE_SCHEMA(SITE_DATA)
    assert result[CONF_GRID_SENSOR] == "sensor.grid_power"


def test_economics_schema_accepts_valid_data():
    """Economics step schema should accept valid numeric values."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_ECONOMICS_SCHEMA

    result = STEP_ECONOMICS_SCHEMA(ECONOMICS_DATA)
    assert result[CONF_GRID_FEE_IMPORT] == 0.40


def test_power_schema_accepts_valid_data():
    """Power step schema should accept valid power limit."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_POWER_SCHEMA

    result = STEP_POWER_SCHEMA(POWER_DATA)
    assert result[CONF_POWER_LIMIT_KW] == 11.0


def test_vehicle_schema_accepts_valid_data():
    """Vehicle step schema should accept valid vehicle config."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_VEHICLE_SCHEMA

    result = STEP_VEHICLE_SCHEMA(VEHICLE_DATA)
    assert result[CONF_VEHICLE_NAME] == "Family Car"


def test_power_schema_uses_default():
    """Power step should default to DEFAULT_POWER_LIMIT_KW."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_POWER_SCHEMA

    result = STEP_POWER_SCHEMA({})
    assert result[CONF_POWER_LIMIT_KW] == DEFAULT_POWER_LIMIT_KW


def test_economics_schema_uses_vat_default():
    """Economics step should default VAT rate."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_ECONOMICS_SCHEMA

    result = STEP_ECONOMICS_SCHEMA(
        {
            CONF_GRID_FEE_IMPORT: 0.40,
            CONF_GRID_FEE_EXPORT: 0.05,
            CONF_EXPORT_COMPENSATION: 0.10,
        }
    )
    assert result[CONF_VAT_RATE] == DEFAULT_VAT_RATE


def test_vehicle_schema_uses_target_soc_default():
    """Vehicle step should default target SoC."""
    from custom_components.smart_ev_optimizer.config_flow import STEP_VEHICLE_SCHEMA

    result = STEP_VEHICLE_SCHEMA(
        {
            CONF_VEHICLE_NAME: "Test",
            CONF_VEHICLE_PRIORITY: 1,
            CONF_VEHICLE_CHARGER_ENTITY: "sensor.charger",
        }
    )
    assert result[CONF_VEHICLE_TARGET_SOC] == DEFAULT_TARGET_SOC


# ---------------------------------------------------------------------------
# Options flow existence
# ---------------------------------------------------------------------------


def test_options_flow_exists():
    """Integration should expose an OptionsFlow for vehicle management."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerOptionsFlow,
    )

    assert hasattr(SmartEVOptimizerOptionsFlow, "async_step_init")


# ---------------------------------------------------------------------------
# Step data flow (async integration-style tests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_user_shows_form():
    """async_step_user with no input should show the site form."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_step_user_advances_to_economics():
    """Submitting site data should advance to the economics step."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(user_input=dict(SITE_DATA))
    assert result["type"] == "form"
    assert result["step_id"] == "economics"


@pytest.mark.asyncio
async def test_step_economics_advances_to_power():
    """Submitting economics data should advance to the power step."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    flow.hass = MagicMock()
    flow._site_data = dict(SITE_DATA)

    result = await flow.async_step_economics(user_input=dict(ECONOMICS_DATA))
    assert result["type"] == "form"
    assert result["step_id"] == "power"


@pytest.mark.asyncio
async def test_step_power_advances_to_vehicle():
    """Submitting power data should advance to the vehicle step."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    flow.hass = MagicMock()
    flow._site_data = dict(SITE_DATA)
    flow._economics_data = dict(ECONOMICS_DATA)

    result = await flow.async_step_power(user_input=dict(POWER_DATA))
    assert result["type"] == "form"
    assert result["step_id"] == "vehicle"


@pytest.mark.asyncio
async def test_step_vehicle_creates_entry():
    """Submitting vehicle data should create the config entry."""
    from custom_components.smart_ev_optimizer.config_flow import (
        SmartEVOptimizerConfigFlow,
    )

    flow = SmartEVOptimizerConfigFlow()
    flow.hass = MagicMock()
    flow._site_data = dict(SITE_DATA)
    flow._economics_data = dict(ECONOMICS_DATA)
    flow._power_data = dict(POWER_DATA)

    # Mock async_create_entry (it is called by the flow)
    flow.async_create_entry = MagicMock(
        return_value={"type": "create_entry", "title": "Smart EV Optimizer"}
    )

    result = await flow.async_step_vehicle(user_input=dict(VEHICLE_DATA))
    assert result["type"] == "create_entry"
    flow.async_create_entry.assert_called_once()
    call_kwargs = flow.async_create_entry.call_args[1]
    assert CONF_VEHICLES in call_kwargs["data"]
    assert len(call_kwargs["data"][CONF_VEHICLES]) == 1
