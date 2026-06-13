"""Button entities for HomeCage."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeCageDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeCage buttons."""
    coordinator: HomeCageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeCageRequestLocationButton(coordinator, entry)])


class HomeCageRequestLocationButton(CoordinatorEntity[HomeCageDataUpdateCoordinator], ButtonEntity):
    """Button that asks the phone to report its location."""

    _attr_icon = "mdi:crosshairs-gps"
    _attr_has_entity_name = True
    _attr_translation_key = "request_location"

    def __init__(
        self,
        coordinator: HomeCageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_request_location"

    async def async_press(self) -> None:
        """Request a phone location report."""
        await self.coordinator.api.async_request_location()
        await self.coordinator.async_request_refresh()
