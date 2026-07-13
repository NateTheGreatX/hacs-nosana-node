# custom_components/nosana_node/__init__.py
"""Nosana Node integration for Home Assistant."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .coordinator import NosanaNodeCoordinator, NosanaInfoCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nosana Node from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    node_address = entry.data["node_address"]
    info_coordinator = NosanaInfoCoordinator(hass, node_address)
    coordinator = NosanaNodeCoordinator(hass, node_address, info_coordinator)

    # Fetch initial data
    await info_coordinator.async_config_entry_first_refresh()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, "info_coordinator": info_coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
