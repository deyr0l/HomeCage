# HomeCage Server

Local web admin and configuration API for HomeCage.

## Run

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
set -a
. ./.env
set +a
homecage-server
```

Open:

```text
http://localhost:8000/
```

The web UI follows the browser `Accept-Language` header. You can also choose a language explicitly:

```text
http://localhost:8000/?lang=en
http://localhost:8000/?lang=ru
http://localhost:8000/?lang=es
http://localhost:8000/?lang=zh-CN
http://localhost:8000/?lang=ja
```

If `HOMECAGE_ADMIN_TOKEN` is set, the browser asks for Basic Auth. Any username is accepted; the password is the token. The same token must be configured in the HomeCage Android admin screen.

## Environment

```env
HOMECAGE_ADMIN_TOKEN=change-this-token
HOMECAGE_HOST=0.0.0.0
HOMECAGE_PORT=8000
HOMECAGE_DATA_DIR=./data
HOMECAGE_HA_MQTT_HOST=
HOMECAGE_HA_MQTT_PORT=1883
HOMECAGE_HA_MQTT_USERNAME=
HOMECAGE_HA_MQTT_PASSWORD=
HOMECAGE_HA_MQTT_TOPIC_PREFIX=homecage
HOMECAGE_HA_MQTT_DISCOVERY_PREFIX=homeassistant
```

## API

- `POST /api/device-state` - app list report from the phone.
- `GET /api/config` - allowlist and remote PIN config for the phone.
- `GET /api/home-assistant/state` - Home Assistant-friendly state snapshot.
- `POST /api/home-assistant/config` - Home Assistant config update endpoint.

With token auth:

```bash
curl -H "Authorization: Bearer change-this-token" http://localhost:8000/api/config
```

For release phone builds, put this server behind HTTPS.

## Home Assistant

The REST endpoint accepts partial updates:

```bash
curl \
  -H "Authorization: Bearer change-this-token" \
  -H "Content-Type: application/json" \
  -d '{"lockdownEnabled": true, "requestLocation": true}' \
  http://localhost:8000/api/home-assistant/config
```

If `HOMECAGE_HA_MQTT_HOST` is set, the server also publishes MQTT Discovery entities:

- `switch.homecage_lost_mode`
- `button.homecage_request_location`
- sensors for allowed app count, location status, and last phone report

MQTT commands update the same config file used by the web admin.
