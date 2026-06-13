# HomeCage

HomeCage 是一个面向家长管理设备的 Android allowlist 启动器。主屏幕只显示已允许的应用和可选的快速拨号联系人。管理区域受 PIN 保护。

其他语言：[English](README.md), [Русский](README_ru.md), [Español](README_es.md), [日本語](README_ja.md).

## 状态

- 应用名称：`HomeCage`
- Android application id：`com.homecage.kiosk`
- 最低 Android：API 26
- 初始 PIN：`1234`
- 主要模式：Device Owner + Lock Task
- 备用保护：Device Admin + Accessibility
- 远程管理：可选的本地/self-hosted 服务器

## 发布检查清单

- 使用 `app/build/outputs/apk/release/app-release.apk`，不要发布 debug APK。
- 使用 `keystore.properties` 中的私有 release keystore 签名。
- 确认 release manifest 中没有 `android:debuggable="true"`。
- 不要提交 `keystore.properties`、`*.jks`、`.env`、APK、AAB 和服务器数据。
- release 版本使用 HTTPS 服务器。HTTP 只在 debug manifest 中启用。
- 在真实设备上测试安装、修改 PIN、快速拨号、同步、重启、卸载和 restricted settings。

## 构建

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

APK：

```text
app/build/outputs/apk/release/app-release.apk
```

## 安装

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dpm set-device-owner com.homecage.kiosk/.admin.KioskDeviceAdminReceiver
adb shell cmd package set-home-activity com.homecage.kiosk/.MainActivity
```

Device Owner 通常需要在添加账号之前，在干净设备上设置。

## 权限

| 权限或能力 | 用途 |
| --- | --- |
| `INTERNET` | 与你的 HomeCage 服务器同步。 |
| `ACCESS_NETWORK_STATE` | 仅在网络可用时调度同步。 |
| `RECEIVE_BOOT_COMPLETED` | 重启后重新调度同步。 |
| `CALL_PHONE` | 快速拨号按钮。应用不会读取联系人。 |
| Device Admin / Device Owner | 防止孩子无 PIN 移除保护，并启用 Lock Task。 |
| Accessibility service | 备用保护：观察前台包名，如果打开未允许的屏幕则返回 HomeCage。 |
| launcher 应用可见性查询 | 在管理界面列出可启动应用。不是 `QUERY_ALL_PACKAGES`。 |

未使用：Usage Access (`PACKAGE_USAGE_STATS`)、悬浮窗 (`SYSTEM_ALERT_WINDOW`)、联系人、SMS、位置、相机、麦克风、notification listener、VPN、`QUERY_ALL_PACKAGES`。

## Accessibility 和 restricted settings

Android 13+ 上，侧载 APK 可能需要手动允许受限设置：

1. 打开 Android Settings。
2. Apps -> HomeCage。
3. 三点菜单。
4. `Allow restricted settings`。
5. 返回 HomeCage Admin 并启用 Accessibility。

## 卸载

打开 HomeCage，输入 PIN，点击 `Disable protection for removal`。解除保护后在 Android settings 卸载，或执行：

```bash
adb uninstall com.homecage.kiosk
```
