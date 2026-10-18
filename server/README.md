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

### Safe Updates

Update and restart the server before updating the Android app. The app requires
`configValid: true`, `configSchemaVersion: 1`, a matching `deviceId`, and a complete
config. Older servers without these fields are rejected; local phone settings stay
unchanged. A confirmed empty app list is valid, but missing fields are not.

Unreadable or corrupt storage returns HTTP 503 without overwriting the file.
If server data is lost, a phone that has already applied a remote config will not
bootstrap a replacement with empty restrictions. Restore a backup or explicitly
save the desired device config in the web admin. Do not delete corrupt data to
make the error disappear.
The app also rejects revisions older than the one it already applied. After
restoring an older backup, review and save its config to publish a new revision.

The location button only requests location; it no longer saves edits in the form.
Saving from a stale page returns HTTP 409 and requires reloading the page.

Run the Russian regression tests from the repository root:

```sh
python3 -m unittest discover -s server/tests -v
./gradlew testDebugUnitTest
```

The JSON endpoint accepts partial updates:

```bash
curl \
  -H "Authorization: Bearer change-this-token" \
  -H "Content-Type: application/json" \
  -d '{"restrictionMode": "parental", "scheduleRulesText": "Weekdays 22:00-07:00 parental", "requestLocation": true}' \
  'http://localhost:8000/api/config?deviceId=android-id-here'
```

Use `"restrictionMode": "lost"` for full lost-phone lockdown. The legacy
`lockdownEnabled` boolean is still accepted and maps to `"lost"`.
Scheduled rules use one line per rule: `<days> <HH:MM-HH:MM> <mode>`, where
days can be `All`, `Weekdays`, `Weekends`, `Mon-Fri`, or comma-separated day
names. Modes are `parental` or `lost`.

Home Assistant support is shipped as a separate HACS custom integration in `../homeassistant`. The server intentionally exposes only generic JSON endpoints.
