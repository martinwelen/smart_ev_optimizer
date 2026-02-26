"""Constants for the Smart EV Optimizer integration."""

from typing import Final

DOMAIN: Final = "smart_ev_optimizer"

PLATFORMS: Final = ["sensor", "binary_sensor", "switch", "number", "select"]

# Config keys — site
CONF_GRID_SENSOR: Final = "grid_sensor"
CONF_SOLAR_SENSOR: Final = "solar_sensor"
CONF_BATTERY_POWER_SENSOR: Final = "battery_power_sensor"
CONF_BATTERY_SOC_SENSOR: Final = "battery_soc_sensor"
CONF_NORDPOOL_SENSOR: Final = "nordpool_sensor"
CONF_GRID_REWARDS_ENTITY: Final = "grid_rewards_entity"

# Config keys — power limits
CONF_POWER_LIMIT_KW: Final = "power_limit_kw"
CONF_CALENDAR_HOUR_TRACKING: Final = "calendar_hour_tracking"

# Config keys — economics
CONF_GRID_FEE_IMPORT: Final = "grid_fee_import"
CONF_GRID_FEE_EXPORT: Final = "grid_fee_export"
CONF_EXPORT_COMPENSATION: Final = "export_compensation"
CONF_VAT_RATE: Final = "vat_rate"

# Config keys — vehicles
CONF_VEHICLES: Final = "vehicles"
CONF_VEHICLE_NAME: Final = "name"
CONF_VEHICLE_PRIORITY: Final = "priority"
CONF_VEHICLE_CHARGER_ENTITY: Final = "charger_entity"
CONF_VEHICLE_SOC_ENTITY: Final = "soc_entity"
CONF_VEHICLE_TARGET_SOC: Final = "target_soc"
CONF_VEHICLE_DEPARTURE_ENTITY: Final = "departure_entity"

# Defaults
DEFAULT_POWER_LIMIT_KW: Final = 11.0
# Calendar hour tracking is always enabled (matches Swedish effekttaxa billing)
DEFAULT_VAT_RATE: Final = 0.25
DEFAULT_TARGET_SOC: Final = 80
DEFAULT_SCAN_INTERVAL: Final = 30

# Safety
OBC_COOLDOWN_SECONDS: Final = 30

# SoC source classification
SOC_SOURCE_API: Final = "api"
SOC_SOURCE_MANUAL: Final = "manual"
SOC_SOURCE_NONE: Final = "none"
