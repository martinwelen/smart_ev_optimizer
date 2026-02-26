"""Smart EV Optimizer integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

SmartEVOptimizerConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: SmartEVOptimizerConfigEntry) -> bool:
    """Set up Smart EV Optimizer from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Coordinator will be created here in Task 7
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartEVOptimizerConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
