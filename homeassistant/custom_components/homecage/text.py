"""Text entities for HomeCage."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
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
    """Set up HomeCage text entities."""
    coordinator: HomeCageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeCageScheduleRulesText(coordinator, entry)])


class HomeCageScheduleRulesText(CoordinatorEntity[HomeCageDataUpdateCoordinator], TextEntity):
    """Editable scheduled restriction rules."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"
    _attr_mode = TextMode.TEXT
    _attr_native_max = 2048
    _attr_translation_key = "schedule_rules"

    def __init__(
        self,
        coordinator: HomeCageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_schedule_rules"

    @property
    def native_value(self) -> str:
        """Return the current schedule text."""
        return str(self.coordinator.data.get("config", {}).get("scheduleRulesText") or "")

    async def async_set_value(self, value: str) -> None:
        """Update scheduled restriction rules."""
        await self.coordinator.api.async_set_schedule_rules_text(value)
        await self.coordinator.async_request_refresh()
