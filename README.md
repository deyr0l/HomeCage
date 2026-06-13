<p align="left">
  <img
    src="https://sun9-16.userapi.com/s/v1/ig2/6oMAy8inWJKIeIKT6NRFwlOtt4jKVIml2Cg5K0CJ4rFjaaFnqufiYxUyJ_HR6Vv6ki0Wl2twl14fLWfMm8csbocF.jpg?quality=95&amp;as=32x32,48x48,72x72,108x108,160x160,240x240,360x360,480x480,512x512&amp;from=bu&amp;u=s0exv-erGy0CAPQpK3_1aOvipvYbhcoCHd9PwImPC20&amp;cs=512x0"
    width="128"
    alt="HomeCage logo"
  >
</p>

# HomeCage

HomeCage is an Android allowlist launcher for parent-managed devices. It shows a small home screen with approved apps and optional quick-call contacts. The admin area is protected by a PIN.

Translations: [Русский](README_ru.md), [Español](README_es.md), [简体中文](README_zh-CN.md), [日本語](README_ja.md).

![Android](https://img.shields.io/badge/Android-8.0%2B-brightgreen)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)
![Kotlin](https://img.shields.io/badge/Kotlin-Android-purple)

## Social restrictions!!!!!
- HomeCage is not spyware.
- HomeCage does not read messages, contacts, location, camera, microphone, or notifications.
- HomeCage is not designed for covert monitoring.
- HomeCage is a visible launcher restriction tool for parent-managed devices.

## Screenshots

![Mainpage](https://sun9-8.userapi.com/s/v1/ig2/zU2RJN3tky2p0pF5EOtV70lFFi7Srfnor2Y2Kruci_8l_zdJa5phBg6sYhUzjIXdEi_8RTrNgL1MCHQJWZHVrzrv.jpg?quality=95&as=32x71,48x107,72x160,108x240,160x356,240x533,360x800,480x1067,540x1200,576x1280&from=bu&u=EoGoEDLcT_mLQOXXTQVxeZ9brqMDqBoh-qoxQAgYMMA&cs=576x0)
![Adminpage](https://sun9-72.userapi.com/s/v1/ig2/7UKyNwxAU0NZyxR4HuyktddcrDHqh4inMMcJBgUTW7r8t3MqhBQtgaN_-WqUCw44DgCTqfjgbJGEFUL1q_vOcSxf.jpg?quality=95&as=32x71,48x107,72x160,108x240,160x356,240x533,360x800,480x1067,540x1200,576x1280&from=bu&cs=576x0)


## Tech info

- Public app name: `HomeCage`
- Android application id: `com.homecage.kiosk`
- Minimum Android version: API 26
- Default PIN: `1234`
- Primary kiosk mode: Android Device Owner + Lock Task
- Fallback protection: Device Admin + Accessibility, for consumer devices where Device Owner is hard to enable
- Remote management: optional local/self-hosted server

## Release Checklist

Before sharing an APK outside your own test phone:

- Build `app/build/outputs/apk/release/app-release.apk`, not the debug APK.
- Sign release builds with a private release keystore from `keystore.properties`.
- Verify that the release manifest does not contain `android:debuggable="true"`.
- Keep `keystore.properties`, `*.jks`, `.env`, APK, AAB and server data out of Git.
- Use HTTPS for the remote server in release builds. Cleartext HTTP is enabled only in the debug manifest.
- Explain sensitive permissions to the person installing the app.
- Test install, PIN change, quick call, remote sync, reboot, removal flow, and MIUI restricted settings on a real device.

## Build

Create a release keystore once:

```bash
keytool -genkeypair \
  -v \
  -keystore homecage-release.jks \
  -alias homecage \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000
```

Create `keystore.properties` from the example:

```bash
cp keystore.properties.example keystore.properties
```

Then edit `keystore.properties` with your private passwords and build:

```bash
./gradlew clean assembleRelease
```

Release APK:

```text
app/build/outputs/apk/release/app-release.apk
```

Debug APK for local development:

```bash
./gradlew assembleDebug
```

## Install And Enable Kiosk Mode

Install the signed release APK:

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
```

For the strongest kiosk mode, assign Device Owner on a clean device before adding accounts:

```bash
adb shell dpm set-device-owner com.homecage.kiosk/.admin.KioskDeviceAdminReceiver
adb shell cmd package set-home-activity com.homecage.kiosk/.MainActivity
```

Open HomeCage, enter the default PIN `1234`, choose allowed apps, configure quick-call contacts if needed, then change the PIN.

## Permissions

HomeCage keeps the permission set intentionally small:

| Permission or capability | Why it is needed |
| --- | --- |
| `INTERNET` | Optional sync with your self-hosted HomeCage server. |
| `ACCESS_NETWORK_STATE` | Lets Android schedule sync only when a network is available. Required for JobScheduler network constraints. |
| `RECEIVE_BOOT_COMPLETED` | Re-schedules background sync after reboot. |
| `CALL_PHONE` | Optional quick-call buttons. The app does not read contacts. |
| `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION` | Optional server-requested location report for lost-device workflows. HomeCage reads the last known Android location only after the server asks for it. |
| Device Admin / Device Owner | Prevents a child from removing protection without the admin PIN and enables Lock Task policies. |
| Accessibility service | Fallback protection on devices where Device Owner is not active. It observes the current foreground package and returns to HomeCage when a blocked app, launcher, installer, or settings screen is opened. |
| Package visibility query for launcher apps | Lets the admin screen list installed launchable apps. This is not `QUERY_ALL_PACKAGES`. |

Not used: Usage Access (`PACKAGE_USAGE_STATS`), draw-over-other-apps (`SYSTEM_ALERT_WINDOW`), contacts, SMS, camera, microphone, notification listener, VPN, or `QUERY_ALL_PACKAGES`.

## Accessibility And Restricted Settings

On Android 13+ a sideloaded APK may be blocked from enabling Accessibility until restricted settings are allowed manually:

1. Open Android Settings.
2. Open Apps -> HomeCage.
3. Open the three-dot menu.
4. Tap `Allow restricted settings`.
5. Return to HomeCage Admin and enable the HomeCage Accessibility service.

Accessibility is only the fallback path. Device Owner + Lock Task is the preferred mode when the device can be provisioned cleanly.

## Remote Server

The app works without a server and keeps its local config. If a server is configured and reachable, server config overwrites the local allowlist.

For release builds, use HTTPS:

```text
https://homecage.example.local
```

Server setup:

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

Open the web admin:

```text
http://localhost:8000/
```

Supported web UI languages:

```text
/?lang=en
/?lang=ru
/?lang=es
/?lang=zh-CN
/?lang=ja
```

Remote config can also enable lost mode and request the device location. Lost mode blocks allowed apps, quick calls, launchers, installers, and settings until the server disables it again. If the phone has no network, it keeps the last local config and tries again later.

Background sync is scheduled roughly every 10 minutes when a network is available. Opening or returning to the HomeCage launcher also forces a sync attempt.

## Home Assistant

HomeCage Server exposes REST endpoints for Home Assistant:

```text
GET  /api/home-assistant/state
POST /api/home-assistant/config
```

`POST /api/home-assistant/config` accepts JSON such as:

```json
{
  "lockdownEnabled": true,
  "requestLocation": true,
  "allowedPackagesText": "com.android.dialer\norg.example.app"
}
```

Optional MQTT Discovery is available when these variables are set on the server:

```env
HOMECAGE_HA_MQTT_HOST=homeassistant.local
HOMECAGE_HA_MQTT_PORT=1883
HOMECAGE_HA_MQTT_USERNAME=
HOMECAGE_HA_MQTT_PASSWORD=
HOMECAGE_HA_MQTT_TOPIC_PREFIX=homecage
HOMECAGE_HA_MQTT_DISCOVERY_PREFIX=homeassistant
```

MQTT publishes a lost-mode switch, a request-location button, and state sensors for allowed apps, location status, and last phone report.

## Removal

Normal removal flow:

1. Open HomeCage.
2. Enter the admin PIN.
3. Tap `Disable protection for removal`.
4. HomeCage stops kiosk mode, clears Device Owner when possible, and opens the Android app details screen.
5. Uninstall the app from Android settings.

ADB after protection is disabled:

```bash
adb uninstall com.homecage.kiosk
```

If the app is still Device Owner, Android will block normal uninstall. Use the in-app removal flow or factory reset the device.

## Release Notes For Maintainers

- The debug manifest allows cleartext traffic for local development.
- The main/release manifest does not opt into cleartext traffic.
- Release signing is required by the Gradle release tasks.
- The repository intentionally ignores release keystores, local env files, generated APK/AAB files, and server data.
- License: GPLv3. See [LICENSE](LICENSE).
