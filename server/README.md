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
```

## API

- `POST /api/device-state` - app list report from the phone.
- `GET /api/config` - allowlist and remote PIN config for the phone.

With token auth:

```bash
curl -H "Authorization: Bearer change-this-token" http://localhost:8000/api/config
```

For release phone builds, put this server behind HTTPS.
