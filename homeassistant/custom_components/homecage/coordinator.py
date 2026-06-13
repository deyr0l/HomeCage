"""Data coordinator for the HomeCage integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HomeCageApiError, HomeCageClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HomeCageDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll HomeCage config and phone state."""

    def __init__(self, hass: HomeAssistant, api: HomeCageClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            config = await self.api.async_get_config()
            device_state = await self.api.async_get_device_state()
        except HomeCageApiError as error:
            raise UpdateFailed(str(error)) from error
        return {
            "config": config,
            "device_state": device_state,
        }
