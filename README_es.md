# HomeCage

HomeCage es un launcher Android con lista de apps permitidas para dispositivos gestionados por un adulto. La pantalla principal muestra solo apps aprobadas y contactos de llamada rápida opcionales. El área de administración está protegida con PIN.

Otros idiomas: [English](README.md), [Русский](README_ru.md), [简体中文](README_zh-CN.md), [日本語](README_ja.md).

## Estado

- Nombre público: `HomeCage`
- Android application id: `com.homecage.kiosk`
- Android mínimo: API 26
- PIN inicial: `1234`
- Modo principal: Device Owner + Lock Task
- Protección alternativa: Device Admin + Accessibility
- Administración remota: servidor local/self-hosted opcional

## Checklist de release

- Usa `app/build/outputs/apk/release/app-release.apk`, no el APK debug.
- Firma el release con un keystore privado en `keystore.properties`.
- Verifica que el manifest de release no contenga `android:debuggable="true"`.
- No subas `keystore.properties`, `*.jks`, `.env`, APK, AAB ni datos del servidor.
- Usa HTTPS para el servidor en builds release. HTTP solo está habilitado en el manifest debug.
- Prueba instalación, cambio de PIN, llamada rápida, sincronización, reinicio, desinstalación y restricted settings en un teléfono real.

## Build

```bash
keytool -genkeypair \
  -v \
  -keystore homecage-release.jks \
  -alias homecage \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000

cp keystore.properties.example keystore.properties
./gradlew clean assembleRelease
```

APK:

```text
app/build/outputs/apk/release/app-release.apk
```

## Instalación

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dpm set-device-owner com.homecage.kiosk/.admin.KioskDeviceAdminReceiver
adb shell cmd package set-home-activity com.homecage.kiosk/.MainActivity
```

Device Owner normalmente requiere un dispositivo limpio antes de añadir cuentas.

## Permisos

| Permiso o capacidad | Motivo |
| --- | --- |
| `INTERNET` | Sincronización opcional con tu servidor HomeCage. |
| `ACCESS_NETWORK_STATE` | Programar sync solo cuando hay red disponible. |
| `RECEIVE_BOOT_COMPLETED` | Reprogramar sync después de reiniciar. |
| `CALL_PHONE` | Botones de llamada rápida. La app no lee contactos. |
| Device Admin / Device Owner | Evita que el niño quite la protección sin PIN y permite Lock Task. |
| Accessibility service | Protección alternativa: detecta el paquete en primer plano y vuelve a HomeCage si la pantalla no está permitida. |
| Visibilidad de apps launcher | Lista apps instaladas en la admin. No es `QUERY_ALL_PACKAGES`. |

No se usa: Usage Access (`PACKAGE_USAGE_STATS`), draw-over-other-apps (`SYSTEM_ALERT_WINDOW`), contactos, SMS, ubicación, cámara, micrófono, notification listener, VPN ni `QUERY_ALL_PACKAGES`.

## Accessibility y restricted settings

En Android 13+ un APK instalado fuera de Play puede necesitar:

1. Android Settings.
2. Apps -> HomeCage.
3. Menú de tres puntos.
4. `Allow restricted settings`.
5. Volver a HomeCage Admin y activar Accessibility.

## Desinstalación

Abre HomeCage, entra con el PIN y pulsa `Disable protection for removal`. Después desinstala desde Android settings o usa:

```bash
adb uninstall com.homecage.kiosk
```
