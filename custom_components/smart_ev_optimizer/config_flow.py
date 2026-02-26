"""Config flow for Smart EV Optimizer integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
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

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voluptuous schemas with HA selectors
# ---------------------------------------------------------------------------

STEP_SITE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GRID_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(CONF_SOLAR_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(CONF_BATTERY_POWER_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(CONF_BATTERY_SOC_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(CONF_NORDPOOL_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Optional(CONF_GRID_REWARDS_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "binary_sensor"]),
        ),
    }
)

STEP_ECONOMICS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GRID_FEE_IMPORT): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=10,
                step=0.01,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(CONF_GRID_FEE_EXPORT): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=10,
                step=0.01,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(CONF_EXPORT_COMPENSATION): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=10,
                step=0.01,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Optional(CONF_VAT_RATE, default=DEFAULT_VAT_RATE): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=1,
                step=0.01,
                mode=NumberSelectorMode.BOX,
            ),
        ),
    }
)

STEP_POWER_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_POWER_LIMIT_KW, default=DEFAULT_POWER_LIMIT_KW
        ): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=50,
                step=0.5,
                unit_of_measurement="kW",
                mode=NumberSelectorMode.BOX,
            ),
        ),
    }
)

STEP_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_NAME): TextSelector(
            TextSelectorConfig(type="text"),
        ),
        vol.Required(CONF_VEHICLE_PRIORITY): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=10,
                step=1,
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(CONF_VEHICLE_CHARGER_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Optional(CONF_VEHICLE_SOC_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="sensor"),
        ),
        vol.Optional(
            CONF_VEHICLE_TARGET_SOC, default=DEFAULT_TARGET_SOC
        ): NumberSelector(
            NumberSelectorConfig(
                min=10,
                max=100,
                step=5,
                unit_of_measurement="%",
                mode=NumberSelectorMode.SLIDER,
            ),
        ),
        vol.Optional(CONF_VEHICLE_DEPARTURE_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "input_datetime"]),
        ),
    }
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def assemble_config_data(
    site_data: dict[str, Any],
    economics_data: dict[str, Any],
    power_data: dict[str, Any],
    vehicles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge data from all config flow steps into a single config dict."""
    data: dict[str, Any] = {}
    data.update(site_data)
    data.update(economics_data)
    data.update(power_data)
    data[CONF_VEHICLES] = list(vehicles)
    return data


# ---------------------------------------------------------------------------
# Config Flow
# ---------------------------------------------------------------------------


class SmartEVOptimizerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a multi-step config flow for Smart EV Optimizer."""

    VERSION = 1
    DOMAIN = DOMAIN

    def __init__(self) -> None:
        """Initialise flow and intermediate storage."""
        super().__init__()
        self._site_data: dict[str, Any] = {}
        self._economics_data: dict[str, Any] = {}
        self._power_data: dict[str, Any] = {}

    # Step 1: Site sensors
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the site sensor mapping step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_SITE_SCHEMA,
            )

        self._site_data = user_input
        return await self.async_step_economics()

    # Step 2: Economics
    async def async_step_economics(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the economics configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="economics",
                data_schema=STEP_ECONOMICS_SCHEMA,
            )

        self._economics_data = user_input
        return await self.async_step_power()

    # Step 3: Power limits
    async def async_step_power(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the power limit configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="power",
                data_schema=STEP_POWER_SCHEMA,
            )

        self._power_data = user_input
        return await self.async_step_vehicle()

    # Step 4: Vehicle setup (first vehicle required during initial config)
    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the vehicle setup step."""
        if user_input is None:
            return self.async_show_form(
                step_id="vehicle",
                data_schema=STEP_VEHICLE_SCHEMA,
            )

        vehicles = [user_input]
        config_data = assemble_config_data(
            self._site_data,
            self._economics_data,
            self._power_data,
            vehicles,
        )
        return self.async_create_entry(
            title="Smart EV Optimizer",
            data=config_data,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return SmartEVOptimizerOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options Flow (add / edit vehicles after initial setup)
# ---------------------------------------------------------------------------


class SmartEVOptimizerOptionsFlow(OptionsFlow):
    """Handle options flow — manage vehicles after initial setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise with existing config entry."""
        super().__init__()
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show vehicle form for adding a new vehicle."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=STEP_VEHICLE_SCHEMA,
            )

        # Append to existing vehicles list
        existing_data = dict(self.config_entry.data)
        vehicles = list(existing_data.get(CONF_VEHICLES, []))
        vehicles.append(user_input)
        existing_data[CONF_VEHICLES] = vehicles

        return self.async_create_entry(title="", data=existing_data)
