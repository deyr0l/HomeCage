"""Config flow for HomeCage."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HomeCageApiError, HomeCageAuthError, HomeCageClient
from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DOMAIN


class HomeCageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a HomeCage config flow."""

    VERSION = 1
    _connection_data: dict[str, str]
    _devices: list[dict[str, Any]]

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                api = HomeCageClient(
                    session=session,
                    base_url=user_input[CONF_URL],
                    token=user_input.get(CONF_TOKEN, ""),
                )
                devices = await api.async_get_devices()
            except HomeCageAuthError:
                errors["base"] = "invalid_auth"
            except HomeCageApiError:
                errors["base"] = "cannot_connect"
            else:
                self._connection_data = {
                    CONF_URL: api.base_url,
                    CONF_TOKEN: user_input.get(CONF_TOKEN, "").strip(),
                }
                if not devices:
                    errors["base"] = "no_devices"
                elif len(devices) == 1:
                    return await self._async_create_device_entry(api, devices[0])
                else:
                    self._devices = devices
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Optional(CONF_TOKEN, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Let the user choose a HomeCage device."""
        errors: dict[str, str] = {}
        devices = getattr(self, "_devices", [])
        device_options = {
            str(device.get("deviceId")): str(device.get("name") or device.get("deviceId"))
            for device in devices
            if device.get("deviceId")
        }

        if user_input is not None:
            selected_device_id = user_input[CONF_DEVICE_ID]
            selected_device = next(
                (
                    device
                    for device in devices
                    if str(device.get("deviceId")) == selected_device_id
                ),
                None,
            )
            if selected_device is None:
                errors["base"] = "unknown"
            else:
                session = async_get_clientsession(self.hass)
                api = HomeCageClient(
                    session=session,
                    base_url=self._connection_data[CONF_URL],
                    token=self._connection_data.get(CONF_TOKEN, ""),
                    device_id=selected_device_id,
                )
                return await self._async_create_device_entry(api, selected_device)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(device_options)}),
            errors=errors,
        )

    async def _async_create_device_entry(
        self,
        api: HomeCageClient,
        device: dict[str, Any],
    ) -> FlowResult:
        device_id = str(device["deviceId"])
        device_name = str(device.get("name") or device_id)
        await self.async_set_unique_id(f"{api.base_url}/{device_id}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"HomeCage {device_name}",
            data={
                CONF_URL: api.base_url,
                CONF_TOKEN: getattr(self, "_connection_data", {}).get(CONF_TOKEN, ""),
                CONF_DEVICE_ID: device_id,
                CONF_DEVICE_NAME: device_name,
            },
        )
