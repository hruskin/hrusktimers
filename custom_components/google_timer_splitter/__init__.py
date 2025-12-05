"""The Google Timer Splitter integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN

# List of platforms that this integration will support.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Google Timer Splitter from a config entry."""
    # Store an object for your platforms to access
    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ...

    # This will trigger the async_setup_entry function in sensor.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This will trigger the async_unload_entry function in sensor.py
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # if unload_ok:
    #     hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok