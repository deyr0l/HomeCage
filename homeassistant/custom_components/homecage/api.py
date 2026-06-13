"""Client for the HomeCage Server API."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode, urljoin

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout


class HomeCageApiError(Exception):
    """Base HomeCage API error."""


class HomeCageAuthError(HomeCageApiError):
    """HomeCage authentication failed."""


class HomeCageClient:
    """Small async client for HomeCage Server."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
        device_id: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = self._normalize_base_url(base_url)
        self._token = token.strip()
        self._device_id = (device_id or "").strip()

    @property
    def base_url(self) -> str:
        """Return the normalized server URL."""
        return self._base_url

    async def async_get_config(self) -> dict[str, Any]:
        """Fetch server config."""
        return await self._request("GET", self._device_path("/api/config"))

    async def async_update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update server config."""
        return await self._request("POST", self._device_path("/api/config"), json_data=payload)

    async def async_get_device_state(self) -> dict[str, Any]:
        """Fetch the latest phone report."""
        return await self._request("GET", self._device_path("/api/device-state"))

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch known HomeCage devices."""
        payload = await self._request("GET", "/api/devices")
        devices = payload.get("devices")
        return devices if isinstance(devices, list) else []

    async def async_set_lockdown(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable lost mode."""
        return await self.async_update_config({"lockdownEnabled": enabled})

    async def async_request_location(self) -> dict[str, Any]:
        """Ask the phone to report location on its next sync."""
        return await self.async_update_config({"requestLocation": True})

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with self._session.request(
                method,
                urljoin(f"{self._base_url}/", path.lstrip("/")),
                headers=headers,
                json=json_data,
                timeout=ClientTimeout(total=10),
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
                    raise HomeCageAuthError("HomeCage server rejected the token")
                if response.status >= 400:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=text,
                        headers=response.headers,
                    )
                if not text:
                    return {}
                return await response.json(content_type=None)
        except HomeCageApiError:
            raise
        except (asyncio.TimeoutError, ClientError) as error:
            raise HomeCageApiError(str(error)) from error

    def _device_path(self, path: str) -> str:
        if not self._device_id:
            return path
        separator = "&" if "?" in path else "?"
        return f"{path}{separator}{urlencode({'deviceId': self._device_id})}"

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if not normalized:
            raise HomeCageApiError("Server URL is empty")
        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized}"
        return normalized
