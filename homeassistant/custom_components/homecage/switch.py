"""Switch entities for HomeCage."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up HomeCage switches."""
    coordinator: HomeCageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HomeCageLostModeSwitch(coordinator, entry),
            HomeCageParentRestrictionSwitch(coordinator, entry),
        ]
    )


class HomeCageLostModeSwitch(CoordinatorEntity[HomeCageDataUpdateCoordinator], SwitchEntity):
    """Lost mode switch."""

    _attr_icon = "mdi:cellphone-lock"
    _attr_has_entity_name = True
    _attr_translation_key = "lost_mode"

    def __init__(
        self,
        coordinator: HomeCageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_lost_mode"

    @property
    def is_on(self) -> bool:
        """Return true if lost mode is active."""
        return self.coordinator.data.get("config", {}).get("restrictionMode") == "lost"

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable lost mode."""
        await self.coordinator.api.async_set_lockdown(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable lost mode."""
        if self.is_on:
            await self.coordinator.api.async_set_lockdown(False)
        await self.coordinator.async_request_refresh()


class HomeCageParentRestrictionSwitch(
    CoordinatorEntity[HomeCageDataUpdateCoordinator],
    SwitchEntity,
):
    """Parent restriction switch."""

    _attr_icon = "mdi:account-child"
    _attr_has_entity_name = True
    _attr_translation_key = "parent_restriction"

    def __init__(
        self,
        coordinator: HomeCageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_parent_restriction"

    @property
    def is_on(self) -> bool:
        """Return true if parent restriction is active."""
        return self.coordinator.data.get("config", {}).get("restrictionMode") == "parental"

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable parent restriction."""
        await self.coordinator.api.async_set_parental_restriction(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable parent restriction."""
        if self.is_on:
            await self.coordinator.api.async_set_parental_restriction(False)
        await self.coordinator.async_request_refresh()
