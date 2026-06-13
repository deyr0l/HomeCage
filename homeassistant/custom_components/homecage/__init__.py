"""The HomeCage integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HomeCageClient
from .const import CONF_DEVICE_ID, DOMAIN, PLATFORMS
from .coordinator import HomeCageDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeCage from a config entry."""
    session = async_get_clientsession(hass)
    api = HomeCageClient(
        session=session,
        base_url=entry.data[CONF_URL],
        token=entry.data.get(CONF_TOKEN, ""),
        device_id=entry.data[CONF_DEVICE_ID],
    )
    coordinator = HomeCageDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HomeCage config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
