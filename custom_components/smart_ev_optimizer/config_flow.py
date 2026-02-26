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
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXPORT_COMPENSATION,
    CONF_FUSE_SIZE,
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
    DEFAULT_FUSE_SIZE,
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
            EntitySelectorConfig(domain="sensor", device_class="monetary"),
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
                step=0.00001,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(CONF_GRID_FEE_EXPORT): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=10,
                step=0.00001,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(CONF_EXPORT_COMPENSATION): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=10,
                step=0.00001,
                unit_of_measurement="SEK/kWh",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Optional(CONF_VAT_RATE, default=DEFAULT_VAT_RATE): NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=1,
                step=0.00001,
                mode=NumberSelectorMode.BOX,
            ),
        ),
    }
)

STEP_POWER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_POWER_LIMIT_KW, default=DEFAULT_POWER_LIMIT_KW): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=50,
                step=0.5,
                unit_of_measurement="kW",
                mode=NumberSelectorMode.BOX,
            ),
        ),
        vol.Optional(CONF_FUSE_SIZE, default=DEFAULT_FUSE_SIZE): NumberSelector(
            NumberSelectorConfig(
                min=10,
                max=63,
                step=1,
                unit_of_measurement="A",
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
        vol.Optional(CONF_VEHICLE_TARGET_SOC, default=DEFAULT_TARGET_SOC): NumberSelector(
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
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the site sensor mapping step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_SITE_SCHEMA,
            )

        self._site_data = user_input
        return await self.async_step_economics()

    # Step 2: Economics
    async def async_step_economics(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the economics configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="economics",
                data_schema=STEP_ECONOMICS_SCHEMA,
            )

        self._economics_data = user_input
        return await self.async_step_power()

    # Step 3: Power limits
    async def async_step_power(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the power limit configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="power",
                data_schema=STEP_POWER_SCHEMA,
            )

        self._power_data = user_input
        return await self.async_step_vehicle()

    # Step 4: Vehicle setup (first vehicle required during initial config)
    async def async_step_vehicle(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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

    MENU_GENERAL = "general_settings"
    MENU_ADD = "add_vehicle"
    MENU_EDIT = "edit_vehicle"
    MENU_REMOVE = "remove_vehicle"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise with existing config entry."""
        super().__init__()
        self._config_entry = config_entry
        self._selected_vehicle_name: str | None = None

    # ----- Menu -----

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show menu: add, edit, or remove vehicle."""
        if user_input is not None:
            action = user_input.get("action")
            if action == self.MENU_GENERAL:
                return await self.async_step_general_settings()
            if action == self.MENU_ADD:
                return await self.async_step_add_vehicle()
            if action == self.MENU_EDIT:
                return await self.async_step_edit_vehicle()
            if action == self.MENU_REMOVE:
                return await self.async_step_remove_vehicle()

        menu_schema = vol.Schema(
            {
                vol.Required("action"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": self.MENU_GENERAL, "label": "General settings"},
                            {"value": self.MENU_ADD, "label": "Add vehicle"},
                            {"value": self.MENU_EDIT, "label": "Edit vehicle"},
                            {"value": self.MENU_REMOVE, "label": "Remove vehicle"},
                        ],
                        mode=SelectSelectorMode.LIST,
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=menu_schema)

    # ----- General Settings -----

    async def async_step_general_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit economics and power limit settings."""
        existing_data = dict(self._config_entry.data)

        if user_input is not None:
            existing_data.update(user_input)
            return self.async_create_entry(title="", data=existing_data)

        general_schema = vol.Schema(
            {
                vol.Required(
                    CONF_GRID_FEE_IMPORT,
                    default=float(existing_data.get(CONF_GRID_FEE_IMPORT, 0.0)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.00001,
                        unit_of_measurement="SEK/kWh",
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
                vol.Required(
                    CONF_GRID_FEE_EXPORT,
                    default=float(existing_data.get(CONF_GRID_FEE_EXPORT, 0.0)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.00001,
                        unit_of_measurement="SEK/kWh",
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
                vol.Required(
                    CONF_EXPORT_COMPENSATION,
                    default=float(existing_data.get(CONF_EXPORT_COMPENSATION, 0.0)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.00001,
                        unit_of_measurement="SEK/kWh",
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
                vol.Optional(
                    CONF_VAT_RATE,
                    default=float(existing_data.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=1,
                        step=0.00001,
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
                vol.Optional(
                    CONF_POWER_LIMIT_KW,
                    default=float(existing_data.get(CONF_POWER_LIMIT_KW, DEFAULT_POWER_LIMIT_KW)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=50,
                        step=0.5,
                        unit_of_measurement="kW",
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
                vol.Optional(
                    CONF_FUSE_SIZE,
                    default=int(existing_data.get(CONF_FUSE_SIZE, DEFAULT_FUSE_SIZE)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=10,
                        max=63,
                        step=1,
                        unit_of_measurement="A",
                        mode=NumberSelectorMode.BOX,
                    ),
                ),
            }
        )
        return self.async_show_form(
            step_id="general_settings",
            data_schema=general_schema,
        )

    # ----- Add -----

    async def async_step_add_vehicle(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add a new vehicle."""
        if user_input is None:
            return self.async_show_form(
                step_id="add_vehicle",
                data_schema=STEP_VEHICLE_SCHEMA,
            )

        existing_data = dict(self._config_entry.data)
        vehicles = list(existing_data.get(CONF_VEHICLES, []))
        vehicles.append(user_input)
        existing_data[CONF_VEHICLES] = vehicles
        return self.async_create_entry(title="", data=existing_data)

    # ----- Edit -----

    async def async_step_edit_vehicle(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Select which vehicle to edit."""
        vehicles = list(self._config_entry.data.get(CONF_VEHICLES, []))
        names = [v.get(CONF_VEHICLE_NAME, f"Vehicle {i + 1}") for i, v in enumerate(vehicles)]

        if not names:
            return self.async_create_entry(title="", data=dict(self._config_entry.data))

        if user_input is not None:
            self._selected_vehicle_name = user_input.get("vehicle")
            return await self.async_step_edit_vehicle_detail()

        select_schema = vol.Schema(
            {
                vol.Required("vehicle"): SelectSelector(
                    SelectSelectorConfig(
                        options=names,
                        mode=SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="edit_vehicle", data_schema=select_schema)

    async def async_step_edit_vehicle_detail(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show pre-filled form for the selected vehicle."""
        existing_data = dict(self._config_entry.data)
        vehicles = list(existing_data.get(CONF_VEHICLES, []))

        idx = None
        for i, v in enumerate(vehicles):
            if v.get(CONF_VEHICLE_NAME) == self._selected_vehicle_name:
                idx = i
                break

        if idx is None:
            return self.async_create_entry(title="", data=existing_data)

        if user_input is not None:
            vehicles[idx] = user_input
            existing_data[CONF_VEHICLES] = vehicles
            return self.async_create_entry(title="", data=existing_data)

        current = vehicles[idx]
        prefilled_schema = vol.Schema(
            {
                vol.Required(
                    CONF_VEHICLE_NAME,
                    default=current.get(CONF_VEHICLE_NAME, ""),
                ): TextSelector(TextSelectorConfig(type="text")),
                vol.Required(
                    CONF_VEHICLE_PRIORITY,
                    default=current.get(CONF_VEHICLE_PRIORITY, 1),
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=10, step=1, mode=NumberSelectorMode.BOX),
                ),
                vol.Required(
                    CONF_VEHICLE_CHARGER_ENTITY,
                    default=current.get(CONF_VEHICLE_CHARGER_ENTITY, ""),
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_VEHICLE_SOC_ENTITY,
                    default=current.get(CONF_VEHICLE_SOC_ENTITY, ""),
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_VEHICLE_TARGET_SOC,
                    default=current.get(CONF_VEHICLE_TARGET_SOC, DEFAULT_TARGET_SOC),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=10,
                        max=100,
                        step=5,
                        unit_of_measurement="%",
                        mode=NumberSelectorMode.SLIDER,
                    ),
                ),
                vol.Optional(
                    CONF_VEHICLE_DEPARTURE_ENTITY,
                    default=current.get(CONF_VEHICLE_DEPARTURE_ENTITY, ""),
                ): EntitySelector(
                    EntitySelectorConfig(domain=["sensor", "input_datetime"]),
                ),
            }
        )
        return self.async_show_form(
            step_id="edit_vehicle_detail",
            data_schema=prefilled_schema,
        )

    # ----- Remove -----

    async def async_step_remove_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select and remove a vehicle."""
        existing_data = dict(self._config_entry.data)
        vehicles = list(existing_data.get(CONF_VEHICLES, []))
        names = [v.get(CONF_VEHICLE_NAME, f"Vehicle {i + 1}") for i, v in enumerate(vehicles)]

        if not names:
            return self.async_create_entry(title="", data=existing_data)

        if user_input is not None:
            remove_name = user_input.get("vehicle")
            vehicles = [v for v in vehicles if v.get(CONF_VEHICLE_NAME) != remove_name]
            existing_data[CONF_VEHICLES] = vehicles
            return self.async_create_entry(title="", data=existing_data)

        select_schema = vol.Schema(
            {
                vol.Required("vehicle"): SelectSelector(
                    SelectSelectorConfig(
                        options=names,
                        mode=SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="remove_vehicle", data_schema=select_schema)
