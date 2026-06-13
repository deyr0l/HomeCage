"""Config flow for HomeCage."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HomeCageApiError, HomeCageAuthError, HomeCageClient
from .const import DOMAIN


class HomeCageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a HomeCage config flow."""

    VERSION = 1

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
                await api.async_get_config()
            except HomeCageAuthError:
                errors["base"] = "invalid_auth"
            except HomeCageApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(api.base_url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="HomeCage",
                    data={
                        CONF_URL: api.base_url,
                        CONF_TOKEN: user_input.get(CONF_TOKEN, "").strip(),
                    },
                )

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
