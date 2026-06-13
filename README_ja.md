# HomeCage

HomeCage は、保護者が管理する端末向けの Android allowlist ランチャーです。ホーム画面には許可したアプリと、任意のクイック通話先だけを表示します。管理画面は PIN で保護されます。

他の言語: [English](README.md), [Русский](README_ru.md), [Español](README_es.md), [简体中文](README_zh-CN.md).

## 状態

- アプリ名: `HomeCage`
- Android application id: `com.homecage.kiosk`
- 最小 Android: API 26
- 初期 PIN: `1234`
- 主な保護: Device Owner + Lock Task
- 代替保護: Device Admin + Accessibility
- リモート管理: 任意のローカル/self-hosted サーバー

## リリースチェックリスト

- debug APK ではなく `app/build/outputs/apk/release/app-release.apk` を配布する。
- `keystore.properties` の private release keystore で署名する。
- release manifest に `android:debuggable="true"` がないことを確認する。
- `keystore.properties`、`*.jks`、`.env`、APK、AAB、サーバーデータを Git に入れない。
- release では HTTPS サーバーを使う。HTTP は debug manifest のみ。
- 実機でインストール、PIN 変更、クイック通話、同期、再起動、削除、restricted settings を確認する。

## ビルド

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

## インストール

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dpm set-device-owner com.homecage.kiosk/.admin.KioskDeviceAdminReceiver
adb shell cmd package set-home-activity com.homecage.kiosk/.MainActivity
```

Device Owner は通常、アカウントを追加する前の初期化済み端末で設定する必要があります。

## 権限

| 権限または機能 | 理由 |
| --- | --- |
| `INTERNET` | HomeCage サーバーとの任意同期。 |
| `ACCESS_NETWORK_STATE` | ネットワーク利用可能時だけ同期をスケジュールするため。 |
| `RECEIVE_BOOT_COMPLETED` | 再起動後に同期を再スケジュールするため。 |
| `CALL_PHONE` | クイック通話ボタン。連絡先は読みません。 |
| `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION` | サーバーが要求した場合の任意の位置情報レポート。 |
| Device Admin / Device Owner | PIN なしで保護を解除されることを防ぎ、Lock Task を有効にするため。 |
| Accessibility service | 代替保護。前面パッケージを見て、許可されていない画面なら HomeCage に戻します。 |
| launcher アプリの可視性クエリ | 管理画面で起動可能アプリを表示するため。`QUERY_ALL_PACKAGES` ではありません。 |

使用しません: Usage Access (`PACKAGE_USAGE_STATS`)、他のアプリの上に表示 (`SYSTEM_ALERT_WINDOW`)、連絡先、SMS、カメラ、マイク、notification listener、VPN、`QUERY_ALL_PACKAGES`。

## Accessibility と restricted settings

Android 13+ では、sideload APK の Accessibility が制限される場合があります。

1. Android Settings を開く。
2. Apps -> HomeCage。
3. 三点メニュー。
4. `Allow restricted settings`。
5. HomeCage Admin に戻り、Accessibility を有効にする。

## リモートサーバー

アプリはサーバーなしでも動作し、ローカル設定を保持します。サーバーが設定され到達可能な場合、サーバー設定がローカルの許可リストを上書きします。

サーバーは紛失モードを有効にし、端末の位置情報を要求できます。紛失モードでは、サーバーが解除するまで許可済みアプリ、クイック通話、ランチャー、インストーラー、設定をブロックします。

ネットワーク利用可能時、同期は約 10 分ごとにスケジュールされます。HomeCage ランチャーを開く、または戻る操作でも同期を試みます。ネットワークがない場合、最後のローカル設定を維持します。

Linux service としてサーバーを自動インストール:

```bash
cd server
sudo ./install-service.sh
```

サーバーは複数の電話をサポートします。各電話は Android `ANDROID_ID` と HomeCage Admin -> Remote management で設定した端末名で識別されます。Web 管理画面で編集する電話を選択できます。

## Home Assistant

Home Assistant 連携は [`homeassistant/`](homeassistant/) に分離された HACS custom integration として配置しています。サーバーには Home Assistant 専用コードを入れず、汎用 JSON endpoints のみを提供します。

## 削除

HomeCage を開き、PIN を入力し、`Disable protection for removal` を押します。保護解除後に Android settings から削除するか、次を実行します。

```bash
adb uninstall com.homecage.kiosk
```
