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
| `CAMERA` | Botón de linterna dentro de HomeCage. Solo usa el modo linterna; no captura imágenes. |
| `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION` | Reporte opcional de ubicación cuando el servidor lo solicita. |
| `PACKAGE_USAGE_STATS` | Capa opcional para modo consumer: segunda señal de app en primer plano cuando Accessibility es incompleto. |
| `SYSTEM_ALERT_WINDOW` | Capa opcional para modo consumer: permite usar overlay normal de Android para la pantalla de bloqueo. |
| Device Admin / Device Owner | Evita que el niño quite la protección sin PIN y permite Lock Task. |
| Accessibility service | Protección alternativa: detecta el paquete en primer plano y vuelve a HomeCage si la pantalla no está permitida. |
| Visibilidad de apps launcher | Lista apps instaladas en la admin. No es `QUERY_ALL_PACKAGES`. |

No se usa: contactos, SMS, captura de cámara, micrófono, notification listener, VPN ni `QUERY_ALL_PACKAGES`.

## Accessibility y restricted settings

En Android 13+ un APK instalado fuera de Play puede necesitar:

1. Android Settings.
2. Apps -> HomeCage.
3. Menú de tres puntos.
4. `Allow restricted settings`.
5. Volver a HomeCage Admin y activar Accessibility.

## Servidor remoto

La app funciona sin servidor y conserva la configuración local. Si el servidor está configurado y disponible, su configuración sobrescribe la lista local de apps permitidas.

El servidor puede activar el modo perdido y solicitar la ubicación del dispositivo. En modo perdido se bloquean apps permitidas, llamadas rápidas, launchers, instaladores y ajustes hasta que el servidor lo desactive.

La sincronización se programa aproximadamente cada 10 minutos cuando hay red. Abrir o volver al launcher HomeCage también fuerza un intento de sincronización. Si no hay red, la app mantiene la última configuración local.

Instalación automática del servidor como servicio Linux:

```sh
# Ejecutar como root desde la carpeta server.
cd server
./install-service.sh
```

En Alpine/OpenRC, instala primero las dependencias: `apk add python3 py3-pip py3-virtualenv openrc`. El script crea el usuario/grupo de servicio `homecage`, busca un puerto libre y activa el servicio al inicio.

El servidor soporta varios teléfonos. Cada teléfono se identifica por Android `ANDROID_ID` y por el nombre configurado en HomeCage Admin -> Remote management. La admin web permite elegir qué teléfono editar.

En el primer contacto, un dispositivo nuevo en el servidor adopta la lista local de apps permitidas del teléfono. Después de guardar la configuración en la admin web o API, el servidor pasa a ser la fuente de verdad para ese dispositivo.

## Home Assistant

La integración de Home Assistant vive por separado en [`homeassistant/`](homeassistant/) como custom integration para HACS. El servidor no contiene código específico de Home Assistant y expone solo endpoints JSON genéricos.

## Desinstalación

Abre HomeCage, entra con el PIN y pulsa `Disable protection for removal`. Después desinstala desde Android settings o usa:

```bash
adb uninstall com.homecage.kiosk
```
