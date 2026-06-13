# HomeCage

HomeCage - Android launcher с allowlist-режимом для устройства под контролем родителя. На главном экране видны только разрешенные приложения и, при необходимости, быстрые вызовы. Админка защищена PIN-кодом.

Другие языки: [English](README.md), [Español](README_es.md), [简体中文](README_zh-CN.md), [日本語](README_ja.md).

## Статус

- Имя приложения: `HomeCage`
- Android application id: `com.homecage.kiosk`
- Минимальная версия Android: API 26
- PIN по умолчанию: `1234`
- Основной режим защиты: Android Device Owner + Lock Task
- Резервная защита: Device Admin + Accessibility
- Удаленное управление: опциональный локальный/self-hosted сервер

## Релизный чек-лист

- Используйте `app/build/outputs/apk/release/app-release.apk`, не debug APK.
- Подписывайте release приватным release keystore из `keystore.properties`.
- Проверьте, что в release manifest нет `android:debuggable="true"`.
- Не коммитьте `keystore.properties`, `*.jks`, `.env`, APK, AAB и данные сервера.
- Для release используйте HTTPS-сервер. HTTP включен только в debug manifest.
- Проверьте установку, смену PIN, быстрый вызов, синхронизацию, перезагрузку, удаление и MIUI restricted settings на реальном телефоне.

## Сборка

Создайте release key один раз:

```bash
keytool -genkeypair \
  -v \
  -keystore homecage-release.jks \
  -alias homecage \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000
```

Создайте `keystore.properties`:

```bash
cp keystore.properties.example keystore.properties
```

Заполните пароли и соберите APK:

```bash
./gradlew clean assembleRelease
```

Готовый файл:

```text
app/build/outputs/apk/release/app-release.apk
```

## Установка

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dpm set-device-owner com.homecage.kiosk/.admin.KioskDeviceAdminReceiver
adb shell cmd package set-home-activity com.homecage.kiosk/.MainActivity
```

Device Owner обычно назначается только на чистом устройстве до добавления аккаунтов.

## Разрешения

| Разрешение или возможность | Зачем нужно |
| --- | --- |
| `INTERNET` | Синхронизация с вашим HomeCage-сервером. |
| `ACCESS_NETWORK_STATE` | Android запускает синхронизацию только при доступной сети. |
| `RECEIVE_BOOT_COMPLETED` | Повторно планирует синхронизацию после перезагрузки. |
| `CALL_PHONE` | Быстрые вызовы. Приложение не читает контакты. |
| `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION` | Опциональный отчёт локации по запросу сервера для режима потерянного устройства. |
| Device Admin / Device Owner | Защита от удаления без PIN и включение Lock Task policies. |
| Accessibility service | Резервная защита: отслеживает открытый пакет и возвращает в HomeCage, если открыт запрещенный экран. |
| Package visibility для launcher-приложений | Список приложений в админке. Это не `QUERY_ALL_PACKAGES`. |

Не используется: Usage Access (`PACKAGE_USAGE_STATS`), поверх окон (`SYSTEM_ALERT_WINDOW`), контакты, SMS, камера, микрофон, notification listener, VPN и `QUERY_ALL_PACKAGES`.

## Accessibility и Restricted Settings

На Android 13+ sideload APK может быть заблокирован для Accessibility:

1. Откройте Android Settings.
2. Apps -> HomeCage.
3. Меню с тремя точками.
4. `Allow restricted settings`.
5. Вернитесь в HomeCage Admin и включите Accessibility service.

## Удаленный сервер

Приложение работает без сервера и хранит локальный конфиг. Если сервер задан и доступен, серверный конфиг перезаписывает локальный allowlist.

Сервер может включить режим потерянного устройства и запросить локацию. В режиме потери блокируются разрешенные приложения, быстрые вызовы, лаунчеры, установщики и настройки, пока сервер не выключит режим.

Синхронизация планируется примерно раз в 10 минут при доступной сети. Открытие или возврат на главный экран HomeCage также запускает попытку синхронизации. Если сети нет, приложение остается на прежнем локальном конфиге.

Автоустановка сервера как Linux service:

```sh
# Запускать от root из папки server.
cd server
./install-service.sh
```

На Alpine/OpenRC сначала поставьте зависимости: `apk add python3 py3-pip py3-virtualenv openrc`. Скрипт сам создает service user/group `homecage`, ищет свободный порт и включает сервис в автозагрузку.

Сервер поддерживает несколько телефонов. Каждый телефон определяется по Android `ANDROID_ID` и имени устройства из HomeCage Admin -> Remote management. В веб-админке можно выбрать, какой телефон редактировать.

## Home Assistant

Интеграция Home Assistant лежит отдельно в [`homeassistant/`](homeassistant/) как HACS custom integration. Сервер не содержит Home Assistant-специфичный код и отдает только обычные JSON endpoints.

## Удаление

1. Откройте HomeCage.
2. Введите PIN.
3. Нажмите `Disable protection for removal`.
4. После снятия защиты удалите приложение в Android settings.

ADB после снятия защиты:

```bash
adb uninstall com.homecage.kiosk
```

Если приложение все еще Device Owner, Android не даст удалить его обычным способом.
