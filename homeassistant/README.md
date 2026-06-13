# HomeCage Home Assistant Integration

HACS-ready custom integration for HomeCage.

This folder is intentionally separated from the Android app and the HomeCage server. To install it through HACS as a custom repository, publish the contents of this `homeassistant/` folder as the root of a GitHub repository or branch. HACS expects `hacs.json` and `custom_components/homecage/` at the repository root.

## Features

- Lost mode switch.
- Request location button.
- Sensors for allowed app count, location status, and last phone report.
- UI setup flow with server URL, optional admin token, and device selection.

## Server API

The integration talks to the generic HomeCage Server JSON API:

```text
GET  /api/config
POST /api/config
GET  /api/device-state
GET  /api/devices
```

No MQTT broker is required.

## HACS

1. Put this folder's contents in a dedicated GitHub repository or branch root.
2. In Home Assistant, open HACS.
3. Add the repository as a custom repository with category `Integration`.
4. Install `HomeCage`.
5. Restart Home Assistant.
6. Make sure each phone has synced with the HomeCage server at least once.
7. Add the integration from Settings -> Devices & services and choose the phone to control.

Use the same token that is configured in `HOMECAGE_ADMIN_TOKEN` on the HomeCage server.
