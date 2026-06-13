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

Automated Linux service install:

```sh
# Run as root from this directory.
./install-service.sh
```

On Alpine/OpenRC, install the base packages first:

```sh
apk add python3 py3-pip py3-virtualenv openrc
```

The installer detects systemd or OpenRC, creates the `homecage` service user/group, copies the server to `/opt/homecage-server`, creates a virtual environment, finds a free port starting at `8000`, writes `/etc/homecage-server.env`, and enables the service on boot.

You can override install defaults with environment variables:

```sh
HOMECAGE_ADMIN_TOKEN="change-me" HOMECAGE_PORT=8000 ./install-service.sh
```

For very small systems where service users are not available, run explicitly as root:

```sh
SERVICE_USER=root SERVICE_GROUP=root ./install-service.sh
```

OpenRC troubleshooting:

```sh
rc-service homecage-server stop
grep HOMECAGE_PORT /etc/conf.d/homecage-server /etc/homecage-server.env
vi /etc/conf.d/homecage-server
vi /etc/homecage-server.env
rc-service homecage-server restart
```

The OpenRC service sources `/etc/conf.d/homecage-server` and exports the `HOMECAGE_*` variables before starting the Python server.

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
```

## API

- `POST /api/device-state` - app list report from the phone.
- `GET /api/devices` - known phones.
- `GET /api/config?deviceId=<id>` - allowlist and remote PIN config for one phone.
- `POST /api/config?deviceId=<id>` - partial JSON config update for one phone.
- `GET /api/device-state?deviceId=<id>` - latest phone report for one phone.

With token auth:

```bash
curl -H "Authorization: Bearer change-this-token" http://localhost:8000/api/devices
```

For release phone builds, put this server behind HTTPS.

## Multiple Devices

Each phone is identified by the Android `ANDROID_ID` fingerprint and can also send a human-readable device name from the app's Admin -> Remote management section.

The server stores per-device config and state in `devices.json`. The old single-device `config.json` and `device_state.json` files are used only for migration when `devices.json` does not exist yet.

On first contact, a new server-side device adopts the phone's local allowed-app list. After the config is saved in the web admin or API, the server becomes the source of truth for that device.

## Config Updates

The JSON endpoint accepts partial updates:

```bash
curl \
  -H "Authorization: Bearer change-this-token" \
  -H "Content-Type: application/json" \
  -d '{"lockdownEnabled": true, "requestLocation": true}' \
  'http://localhost:8000/api/config?deviceId=android-id-here'
```

Home Assistant support is shipped as a separate HACS custom integration in `../homeassistant`. The server intentionally exposes only generic JSON endpoints.
