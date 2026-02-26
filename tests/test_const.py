"""Tests for constants module."""
from custom_components.smart_ev_optimizer.const import (
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_CALENDAR_HOUR_TRACKING,
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
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_SOC,
    DEFAULT_VAT_RATE,
    DOMAIN,
    OBC_COOLDOWN_SECONDS,
    PLATFORMS,
    SOC_SOURCE_API,
    SOC_SOURCE_MANUAL,
    SOC_SOURCE_NONE,
)


def test_domain_is_string():
    assert isinstance(DOMAIN, str)
    assert DOMAIN == "smart_ev_optimizer"


def test_platforms_contains_expected():
    assert "sensor" in PLATFORMS
    assert "binary_sensor" in PLATFORMS
    assert "switch" in PLATFORMS
    assert "number" in PLATFORMS
    assert "select" in PLATFORMS


def test_defaults_are_sensible():
    assert DEFAULT_POWER_LIMIT_KW > 0
    assert CONF_CALENDAR_HOUR_TRACKING is not None
    assert DEFAULT_VAT_RATE == 0.25
    assert DEFAULT_TARGET_SOC == 80
    assert DEFAULT_SCAN_INTERVAL == 30
    assert OBC_COOLDOWN_SECONDS == 30


def test_soc_source_types():
    assert SOC_SOURCE_API == "api"
    assert SOC_SOURCE_MANUAL == "manual"
    assert SOC_SOURCE_NONE == "none"


def test_all_config_keys_are_strings():
    """Verify all config key constants are non-empty strings."""
    config_keys = [
        CONF_GRID_SENSOR,
        CONF_SOLAR_SENSOR,
        CONF_BATTERY_POWER_SENSOR,
        CONF_BATTERY_SOC_SENSOR,
        CONF_NORDPOOL_SENSOR,
        CONF_GRID_REWARDS_ENTITY,
        CONF_POWER_LIMIT_KW,
        CONF_CALENDAR_HOUR_TRACKING,
        CONF_GRID_FEE_IMPORT,
        CONF_GRID_FEE_EXPORT,
        CONF_EXPORT_COMPENSATION,
        CONF_VAT_RATE,
        CONF_VEHICLES,
        CONF_VEHICLE_NAME,
        CONF_VEHICLE_PRIORITY,
        CONF_VEHICLE_CHARGER_ENTITY,
        CONF_VEHICLE_SOC_ENTITY,
        CONF_VEHICLE_TARGET_SOC,
        CONF_VEHICLE_DEPARTURE_ENTITY,
    ]
    for key in config_keys:
        assert isinstance(key, str), f"Expected string, got {type(key)}"
        assert len(key) > 0, "Config key must not be empty"
