"""Sensor entities for HomeCage."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import HomeCageDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeCage sensors."""
    coordinator: HomeCageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HomeCageAllowedAppsSensor(coordinator, entry),
            HomeCageLocationStatusSensor(coordinator, entry),
            HomeCageLastPhoneReportSensor(coordinator, entry),
        ]
    )


class HomeCageBaseSensor(CoordinatorEntity[HomeCageDataUpdateCoordinator], SensorEntity):
    """Base HomeCage sensor."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: HomeCageDataUpdateCoordinator,
        entry: ConfigEntry,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

    @property
    def config(self) -> dict[str, Any]:
        """Return HomeCage config data."""
        return self.coordinator.data.get("config", {})

    @property
    def device_state(self) -> dict[str, Any]:
        """Return latest phone report."""
        return self.coordinator.data.get("device_state", {})


class HomeCageAllowedAppsSensor(HomeCageBaseSensor):
    """Allowed app count."""

    _attr_icon = "mdi:apps"
    _attr_translation_key = "allowed_apps"

    def __init__(self, coordinator: HomeCageDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "allowed_apps")

    @property
    def native_value(self) -> int:
        """Return allowed app count."""
        return len(self.config.get("allowedPackages") or [])


class HomeCageLocationStatusSensor(HomeCageBaseSensor):
    """Latest location status."""

    _attr_icon = "mdi:map-marker"
    _attr_translation_key = "location_status"

    def __init__(self, coordinator: HomeCageDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "location_status")

    @property
    def native_value(self) -> str:
        """Return latest location status."""
        location = self.device_state.get("location") or {}
        requested_id = self._location_request_id(self.config)
        reported_id = self._location_request_id(location)
        if requested_id > 0 and reported_id < requested_id:
            return "pending"
        return str(location.get("status") or "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return location attributes."""
        requested_id = self._location_request_id(self.config)
        location = self.device_state.get("location")
        if not isinstance(location, dict):
            return {"requestedId": requested_id} if requested_id > 0 else {}
        attributes = {
            key: value
            for key, value in location.items()
            if key
            in {
                "requestId",
                "latitude",
                "longitude",
                "accuracyMeters",
                "provider",
                "capturedAt",
                "reportedAt",
            }
        }
        if requested_id > 0:
            attributes["requestedId"] = requested_id
        return attributes

    @staticmethod
    def _location_request_id(payload: dict[str, Any]) -> int:
        try:
            return int(payload.get("locationRequestId") or payload.get("requestId") or 0)
        except (TypeError, ValueError):
            return 0


class HomeCageLastPhoneReportSensor(HomeCageBaseSensor):
    """Last phone report timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check"
    _attr_translation_key = "last_phone_report"

    def __init__(self, coordinator: HomeCageDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_phone_report")

    @property
    def native_value(self) -> object:
        """Return latest phone report timestamp."""
        reported_at = self.device_state.get("reportedAt")
        if not reported_at:
            return None
        return dt_util.parse_datetime(str(reported_at))
