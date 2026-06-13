"""Constants for the HomeCage integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "homecage"
PLATFORMS = [Platform.SWITCH, Platform.BUTTON, Platform.SENSOR]
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"
