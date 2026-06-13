from __future__ import annotations

import base64
import html
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from litestar import Litestar, Request, get, post
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_401_UNAUTHORIZED


def env_value(name: str, default: str) -> str:
    return os.getenv(name) or default


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(env_value("HOMECAGE_DATA_DIR", str(ROOT_DIR / "data")))
CONFIG_PATH = DATA_DIR / "config.json"
DEVICE_STATE_PATH = DATA_DIR / "device_state.json"
ADMIN_TOKEN = env_value("HOMECAGE_ADMIN_TOKEN", "")
MQTT_CLIENT = None
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "ru", "es", "zh-CN", "ja")
LANGUAGE_LABELS = {
    "en": "English",
    "ru": "Русский",
    "es": "Español",
    "zh-CN": "简体中文",
    "ja": "日本語",
}
MESSAGES = {
    "en": {
        "app_list_empty": "The phone has not reported its app list yet. Open HomeCage and run sync.",
        "auth_disabled": "Disabled",
        "auth_enabled": "Enabled",
        "auth_note": "Token auth",
        "clear_remote_pin": "Clear remote PIN command",
        "config": "Config",
        "extra_packages": "Additional package names",
        "extra_packages_help": "Packages missing from the last phone report",
        "language": "Language",
        "last_phone_report": "Phone report",
        "latest_location": "Latest location",
        "location_not_reported": "not reported",
        "location_request": "Location request",
        "location_status": "Location status: {status}",
        "lockdown_enabled": "Enable lost mode",
        "lockdown_help": "When lost mode is enabled, the phone blocks apps, quick calls, launchers, installers, and settings until the server turns it off.",
        "lockdown_section": "Lost mode",
        "no_data": "no data",
        "pin_label": "New PIN, 4-12 digits. Leave empty to keep current. Current state: {pin_status}.",
        "pin_invalid": "PIN must contain 4-12 digits",
        "pin_section": "App PIN",
        "pin_set": "set",
        "pin_unset": "not set",
        "save_config": "Save config",
        "system_badge": "system",
        "title": "HomeCage Admin",
        "allowed_apps": "Allowed apps",
        "request_location": "Request location",
    },
    "ru": {
        "app_list_empty": "Телефон еще не прислал список приложений. Откройте HomeCage и нажмите синхронизацию.",
        "auth_disabled": "Отключена",
        "auth_enabled": "Включена",
        "auth_note": "Token auth",
        "clear_remote_pin": "Очистить remote PIN-команду",
        "config": "Конфиг",
        "extra_packages": "Дополнительные package names",
        "extra_packages_help": "Пакеты, которых нет в последнем отчете телефона",
        "language": "Язык",
        "last_phone_report": "Отчет телефона",
        "latest_location": "Последняя локация",
        "location_not_reported": "не передавалась",
        "location_request": "Запрос локации",
        "location_status": "Статус локации: {status}",
        "lockdown_enabled": "Включить режим потерянного телефона",
        "lockdown_help": "Когда режим включен, телефон блокирует приложения, быстрые вызовы, лаунчеры, установщики и настройки, пока сервер не выключит режим.",
        "lockdown_section": "Режим потери",
        "no_data": "нет данных",
        "pin_label": "Новый PIN, 4-12 цифр. Оставьте пустым, чтобы не менять. Сейчас: {pin_status}.",
        "pin_invalid": "PIN должен содержать 4-12 цифр",
        "pin_section": "PIN приложения",
        "pin_set": "задан",
        "pin_unset": "не задан",
        "save_config": "Сохранить конфиг",
        "system_badge": "системное",
        "title": "HomeCage Admin",
        "allowed_apps": "Разрешенные приложения",
        "request_location": "Запросить локацию",
    },
    "es": {
        "app_list_empty": "El teléfono aún no envió la lista de apps. Abre HomeCage y ejecuta la sincronización.",
        "auth_disabled": "Desactivada",
        "auth_enabled": "Activada",
        "auth_note": "Autenticación por token",
        "clear_remote_pin": "Borrar comando remoto de PIN",
        "config": "Config",
        "extra_packages": "Nombres de paquete adicionales",
        "extra_packages_help": "Paquetes que no aparecen en el último informe del teléfono",
        "language": "Idioma",
        "last_phone_report": "Informe del teléfono",
        "latest_location": "Última ubicación",
        "location_not_reported": "sin reporte",
        "location_request": "Solicitud de ubicación",
        "location_status": "Estado de ubicación: {status}",
        "lockdown_enabled": "Activar modo perdido",
        "lockdown_help": "Cuando el modo perdido está activo, el teléfono bloquea apps, llamadas rápidas, launchers, instaladores y ajustes hasta que el servidor lo desactive.",
        "lockdown_section": "Modo perdido",
        "no_data": "sin datos",
        "pin_label": "Nuevo PIN, 4-12 dígitos. Déjalo vacío para no cambiarlo. Estado actual: {pin_status}.",
        "pin_invalid": "El PIN debe contener 4-12 dígitos",
        "pin_section": "PIN de la app",
        "pin_set": "configurado",
        "pin_unset": "no configurado",
        "save_config": "Guardar config",
        "system_badge": "sistema",
        "title": "HomeCage Admin",
        "allowed_apps": "Apps permitidas",
        "request_location": "Solicitar ubicación",
    },
    "zh-CN": {
        "app_list_empty": "手机尚未上报应用列表。请打开 HomeCage 并执行同步。",
        "auth_disabled": "已停用",
        "auth_enabled": "已启用",
        "auth_note": "令牌认证",
        "clear_remote_pin": "清除远程 PIN 命令",
        "config": "配置",
        "extra_packages": "额外包名",
        "extra_packages_help": "上次手机报告中缺失的包名",
        "language": "语言",
        "last_phone_report": "手机报告",
        "latest_location": "最新位置",
        "location_not_reported": "未上报",
        "location_request": "位置请求",
        "location_status": "位置状态：{status}",
        "lockdown_enabled": "启用丢失模式",
        "lockdown_help": "启用丢失模式后，手机会阻止应用、快速拨号、启动器、安装器和设置，直到服务器关闭该模式。",
        "lockdown_section": "丢失模式",
        "no_data": "无数据",
        "pin_label": "新 PIN，4-12 位数字。留空则不更改。当前状态：{pin_status}。",
        "pin_invalid": "PIN 必须包含 4-12 位数字",
        "pin_section": "应用 PIN",
        "pin_set": "已设置",
        "pin_unset": "未设置",
        "save_config": "保存配置",
        "system_badge": "系统",
        "title": "HomeCage Admin",
        "allowed_apps": "允许的应用",
        "request_location": "请求位置",
    },
    "ja": {
        "app_list_empty": "電話からアプリ一覧がまだ送信されていません。HomeCage を開いて同期してください。",
        "auth_disabled": "無効",
        "auth_enabled": "有効",
        "auth_note": "トークン認証",
        "clear_remote_pin": "リモート PIN コマンドを消去",
        "config": "設定",
        "extra_packages": "追加パッケージ名",
        "extra_packages_help": "最後の電話レポートにないパッケージ",
        "language": "言語",
        "last_phone_report": "電話レポート",
        "latest_location": "最新の位置情報",
        "location_not_reported": "未報告",
        "location_request": "位置情報リクエスト",
        "location_status": "位置情報ステータス: {status}",
        "lockdown_enabled": "紛失モードを有効化",
        "lockdown_help": "紛失モードが有効な間、サーバーが解除するまでアプリ、クイック通話、ランチャー、インストーラー、設定をブロックします。",
        "lockdown_section": "紛失モード",
        "no_data": "データなし",
        "pin_label": "新しい PIN、4-12 桁。変更しない場合は空のままにします。現在: {pin_status}。",
        "pin_invalid": "PIN は 4-12 桁の数字で入力してください",
        "pin_section": "アプリ PIN",
        "pin_set": "設定済み",
        "pin_unset": "未設定",
        "save_config": "設定を保存",
        "system_badge": "システム",
        "title": "HomeCage Admin",
        "allowed_apps": "許可されたアプリ",
        "request_location": "位置情報をリクエスト",
    },
}


@dataclass(frozen=True)
class Config:
    allowed_packages: list[str]
    pin: str | None
    lockdown_enabled: bool
    location_request_id: int
    updated_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_language(raw_language: str | None) -> str:
    if not raw_language:
        return DEFAULT_LANGUAGE

    language = raw_language.strip().replace("_", "-")
    if not language:
        return DEFAULT_LANGUAGE

    lower_language = language.lower()
    if lower_language in {"zh", "zh-cn", "zh-hans", "zh-hans-cn"}:
        return "zh-CN"

    base_language = lower_language.split("-", 1)[0]
    if base_language in SUPPORTED_LANGUAGES:
        return base_language
    return DEFAULT_LANGUAGE


def language_from_accept_language(header_value: str | None) -> str:
    if not header_value:
        return DEFAULT_LANGUAGE

    for item in header_value.split(","):
        language = normalize_language(item.split(";", 1)[0])
        if language != DEFAULT_LANGUAGE or item.strip().lower().startswith("en"):
            return language
    return DEFAULT_LANGUAGE


def resolve_language(request: Request) -> str:
    query_language = normalize_language(request.query_params.get("lang"))
    if request.query_params.get("lang"):
        return query_language
    return language_from_accept_language(request.headers.get("accept-language"))


def message(language: str, key: str, **kwargs: Any) -> str:
    template = MESSAGES.get(language, MESSAGES[DEFAULT_LANGUAGE]).get(
        key,
        MESSAGES[DEFAULT_LANGUAGE][key],
    )
    return template.format(**kwargs)


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def normalize_packages(packages: Any) -> list[str]:
    if isinstance(packages, str):
        source_packages = split_packages(packages)
    elif isinstance(packages, (list, tuple, set)):
        source_packages = packages
    else:
        source_packages = []

    cleaned = []
    seen = set()
    for package in source_packages:
        package = str(package).strip()
        if not package or package in seen:
            continue
        seen.add(package)
        cleaned.append(package)
    return sorted(cleaned)


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    ensure_data_dir()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_data_dir()
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def read_config() -> Config:
    data = read_json(
        CONFIG_PATH,
        {
            "allowedPackages": [],
            "pin": None,
            "lockdownEnabled": False,
            "locationRequestId": 0,
            "updatedAt": utc_now(),
        },
    )
    return Config(
        allowed_packages=normalize_packages(data.get("allowedPackages", [])),
        pin=data.get("pin") or None,
        lockdown_enabled=parse_bool(data.get("lockdownEnabled")),
        location_request_id=max(0, parse_int(data.get("locationRequestId"))),
        updated_at=data.get("updatedAt") or utc_now(),
    )


def write_config(
    allowed_packages: list[str],
    pin: str | None,
    lockdown_enabled: bool,
    location_request_id: int,
) -> Config:
    config = Config(
        allowed_packages=normalize_packages(allowed_packages),
        pin=pin,
        lockdown_enabled=lockdown_enabled,
        location_request_id=max(0, int(location_request_id)),
        updated_at=utc_now(),
    )
    write_json(
        CONFIG_PATH,
        {
            "allowedPackages": config.allowed_packages,
            "pin": config.pin,
            "lockdownEnabled": config.lockdown_enabled,
            "locationRequestId": config.location_request_id,
            "updatedAt": config.updated_at,
        },
    )
    return config


def config_to_api(config: Config) -> dict[str, Any]:
    return {
        "allowedPackages": config.allowed_packages,
        "pin": config.pin,
        "lockdownEnabled": config.lockdown_enabled,
        "locationRequestId": config.location_request_id,
        "updatedAt": config.updated_at,
    }


def home_assistant_state_payload(
    config: Config,
    device_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "allowedPackages": config.allowed_packages,
        "allowedPackagesText": "\n".join(config.allowed_packages),
        "allowedPackagesCount": len(config.allowed_packages),
        "pinSet": config.pin is not None,
        "lockdownEnabled": config.lockdown_enabled,
        "locationRequestId": config.location_request_id,
        "configUpdatedAt": config.updated_at,
        "deviceId": device_state.get("deviceId"),
        "deviceReportedAt": device_state.get("reportedAt"),
        "localAllowedPackages": device_state.get("localAllowedPackages") or [],
        "location": device_state.get("location"),
    }


def write_config_from_payload(payload: dict[str, Any], current_config: Config) -> Config:
    allowed_packages = current_config.allowed_packages
    if "allowedPackages" in payload:
        raw_packages = payload.get("allowedPackages") or []
        if isinstance(raw_packages, str):
            allowed_packages = split_packages(raw_packages)
        else:
            allowed_packages = [str(package) for package in raw_packages]
    elif "allowedPackagesText" in payload:
        allowed_packages = split_packages(str(payload.get("allowedPackagesText") or ""))

    pin = current_config.pin
    if parse_bool(payload.get("clearPin")):
        pin = None
    elif "pin" in payload:
        raw_pin = payload.get("pin")
        pin = str(raw_pin).strip() if raw_pin is not None else None
        if pin == "":
            pin = current_config.pin
    if pin is not None and (not pin.isdigit() or len(pin) not in range(4, 13)):
        raise ValueError("PIN must contain 4-12 digits")

    location_request_id = current_config.location_request_id
    if parse_bool(payload.get("requestLocation")):
        location_request_id += 1

    return write_config(
        allowed_packages=allowed_packages,
        pin=pin,
        lockdown_enabled=parse_bool(
            payload.get("lockdownEnabled"),
            default=current_config.lockdown_enabled,
        ),
        location_request_id=location_request_id,
    )


def unauthorized() -> Response:
    return Response(
        content="Unauthorized",
        status_code=HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": 'Basic realm="HomeCage"'},
    )


def is_authorized(request: Request) -> bool:
    if not ADMIN_TOKEN:
        return True

    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip() == ADMIN_TOKEN

    if authorization.startswith("Basic "):
        encoded = authorization.removeprefix("Basic ").strip()
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        _, _, password = decoded.partition(":")
        return password == ADMIN_TOKEN

    return False


def split_packages(raw: str) -> list[str]:
    packages = []
    for line in raw.replace(",", "\n").splitlines():
        line = line.strip()
        if line:
            packages.append(line)
    return packages


def get_form_list(form: Any, key: str) -> list[str]:
    for method_name in ("getall", "getlist"):
        getter = getattr(form, method_name, None)
        if callable(getter):
            return [str(value) for value in getter(key)]

    value = form.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [str(value)]


def read_device_state() -> dict[str, Any]:
    return read_json(
        DEVICE_STATE_PATH,
        {
            "deviceId": None,
            "reportedAt": None,
            "installedApps": [],
            "localAllowedPackages": [],
            "lockdownEnabled": False,
            "location": None,
        },
    )


def location_summary(device_state: dict[str, Any], language: str) -> str:
    location = device_state.get("location")
    if not isinstance(location, dict):
        return message(language, "location_not_reported")

    status = str(location.get("status") or "unknown")
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if status == "ok" and latitude is not None and longitude is not None:
        accuracy = location.get("accuracyMeters")
        provider = location.get("provider") or "unknown"
        captured_at = location.get("capturedAt") or message(language, "no_data")
        map_url = f"https://maps.google.com/?q={quote(str(latitude))},{quote(str(longitude))}"
        accuracy_text = f", +/- {accuracy} m" if accuracy is not None else ""
        return (
            f"<a href='{map_url}' target='_blank' rel='noreferrer'>"
            f"{html.escape(str(latitude))}, {html.escape(str(longitude))}</a>"
            f"{html.escape(accuracy_text)}<br>"
            f"<small>{html.escape(provider)} · {html.escape(str(captured_at))}</small>"
        )
    return html.escape(message(language, "location_status", status=status))


def normalize_location_payload(raw_location: Any) -> dict[str, Any] | None:
    if not isinstance(raw_location, dict):
        return None

    location: dict[str, Any] = {
        "requestId": max(0, parse_int(raw_location.get("requestId"))),
        "status": str(raw_location.get("status") or "unknown"),
        "reportedAt": utc_now(),
    }
    for key in ("latitude", "longitude", "accuracyMeters"):
        value = raw_location.get(key)
        if value is not None:
            try:
                location[key] = float(value)
            except (TypeError, ValueError):
                pass
    provider = raw_location.get("provider")
    if provider:
        location["provider"] = str(provider)
    captured_at_millis = raw_location.get("capturedAtMillis")
    if captured_at_millis:
        captured_at = datetime.fromtimestamp(
            parse_int(captured_at_millis) / 1000,
            tz=timezone.utc,
        )
        location["capturedAt"] = captured_at.isoformat()
    return location


def render_admin_page(config: Config, device_state: dict[str, Any], language: str) -> str:
    installed_apps = device_state.get("installedApps", [])
    known_packages = {app.get("packageName") for app in installed_apps}
    extra_packages = [pkg for pkg in config.allowed_packages if pkg not in known_packages]
    pin_status = message(language, "pin_set") if config.pin else message(language, "pin_unset")

    app_rows = []
    for app in installed_apps:
        package_name = str(app.get("packageName", ""))
        if not package_name:
            continue
        label = html.escape(str(app.get("label") or package_name))
        escaped_package = html.escape(package_name)
        checked = "checked" if package_name in config.allowed_packages else ""
        system_badge = (
            f"<span class='badge'>{html.escape(message(language, 'system_badge'))}</span>"
            if app.get("isSystem")
            else ""
        )
        app_rows.append(
            f"""
            <label class="app-row">
              <input type="checkbox" name="package" value="{escaped_package}" {checked}>
              <span>
                <strong>{label}</strong>
                <small>{escaped_package} {system_badge}</small>
              </span>
            </label>
            """
        )

    app_list = "\n".join(app_rows) or f"<p class='muted'>{html.escape(message(language, 'app_list_empty'))}</p>"
    manual_packages = html.escape("\n".join(extra_packages))
    auth_note = message(language, "auth_enabled") if ADMIN_TOKEN else message(language, "auth_disabled")
    reported_at = html.escape(str(device_state.get("reportedAt") or message(language, "no_data")))
    updated_at = html.escape(config.updated_at)
    lockdown_checked = "checked" if config.lockdown_enabled else ""
    location_html = location_summary(device_state, language)
    page_title = html.escape(message(language, "title"))
    language_links = " ".join(
        (
            f"<strong>{html.escape(LANGUAGE_LABELS[code])}</strong>"
            if code == language
            else f"<a href='/?lang={quote(code)}'>{html.escape(LANGUAGE_LABELS[code])}</a>"
        )
        for code in SUPPORTED_LANGUAGES
    )
    form_action = f"/admin/config?lang={quote(language)}"
    pin_label = html.escape(message(language, "pin_label", pin_status=pin_status))

    return f"""<!doctype html>
<html lang="{html.escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f8fafc;
      color: #111827;
    }}
    body {{
      margin: 0;
      background: #f8fafc;
    }}
    header {{
      background: #0f172a;
      color: white;
      padding: 20px min(6vw, 48px);
    }}
    main {{
      width: min(980px, calc(100vw - 32px));
      margin: 24px auto 48px;
    }}
    h1, h2 {{
      margin: 0;
      letter-spacing: 0;
    }}
    h1 {{
      font-size: 28px;
    }}
    h2 {{
      font-size: 18px;
      margin-bottom: 14px;
    }}
    .panel {{
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 16px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin-top: 12px;
      color: #475569;
      font-size: 14px;
    }}
    .language-switch {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
      font-size: 14px;
    }}
    .language-switch a,
    .language-switch strong {{
      color: white;
      text-decoration: none;
      border: 1px solid rgba(255, 255, 255, 0.24);
      border-radius: 999px;
      padding: 6px 10px;
    }}
    .language-switch strong {{
      background: #2563eb;
      border-color: #2563eb;
    }}
    .app-list {{
      display: grid;
      gap: 8px;
      max-height: 52vh;
      overflow: auto;
      padding-right: 4px;
    }}
    .app-row {{
      display: grid;
      grid-template-columns: 24px 1fr;
      align-items: center;
      gap: 10px;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 10px;
      cursor: pointer;
    }}
    .app-row small {{
      display: block;
      color: #64748b;
      margin-top: 2px;
      word-break: break-word;
    }}
    .badge {{
      display: inline-block;
      color: #334155;
      background: #e2e8f0;
      border-radius: 999px;
      padding: 1px 6px;
      margin-left: 6px;
    }}
    textarea, input[type="text"], input[type="password"] {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
    }}
    textarea {{
      min-height: 96px;
      resize: vertical;
    }}
    label.field {{
      display: grid;
      gap: 8px;
      color: #334155;
      font-weight: 600;
      margin: 12px 0;
    }}
    button {{
      border: 0;
      border-radius: 8px;
      background: #2563eb;
      color: white;
      font: inherit;
      font-weight: 700;
      padding: 12px 16px;
      cursor: pointer;
    }}
    .muted {{
      color: #64748b;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{page_title}</h1>
    <div class="meta">
      <span>{html.escape(message(language, "config"))}: {updated_at}</span>
      <span>{html.escape(message(language, "last_phone_report"))}: {reported_at}</span>
      <span>{html.escape(message(language, "auth_note"))}: {html.escape(auth_note)}</span>
    </div>
    <nav class="language-switch" aria-label="{html.escape(message(language, "language"))}">
      {language_links}
    </nav>
  </header>
  <main>
    <form method="post" action="{form_action}">
      <section class="panel">
        <h2>{html.escape(message(language, "allowed_apps"))}</h2>
        <div class="app-list">{app_list}</div>
      </section>
      <section class="panel">
        <h2>{html.escape(message(language, "extra_packages"))}</h2>
        <label class="field">
          {html.escape(message(language, "extra_packages_help"))}
          <textarea name="manualPackages" spellcheck="false">{manual_packages}</textarea>
        </label>
      </section>
      <section class="panel">
        <h2>{html.escape(message(language, "lockdown_section"))}</h2>
        <label>
          <input type="checkbox" name="lockdownEnabled" value="1" {lockdown_checked}>
          {html.escape(message(language, "lockdown_enabled"))}
        </label>
        <p class="muted">{html.escape(message(language, "lockdown_help"))}</p>
      </section>
      <section class="panel">
        <h2>{html.escape(message(language, "location_request"))}</h2>
        <p class="muted"><strong>{html.escape(message(language, "latest_location"))}:</strong><br>{location_html}</p>
        <button type="submit" name="action" value="requestLocation">{html.escape(message(language, "request_location"))}</button>
      </section>
      <section class="panel">
        <h2>{html.escape(message(language, "pin_section"))}</h2>
        <label class="field">
          {pin_label}
          <input type="password" name="pin" inputmode="numeric" pattern="[0-9]{{4,12}}">
        </label>
        <label>
          <input type="checkbox" name="clearPin" value="1">
          {html.escape(message(language, "clear_remote_pin"))}
        </label>
        <button type="submit" name="action" value="save">{html.escape(message(language, "save_config"))}</button>
      </section>
    </form>
  </main>
</body>
</html>"""


@get("/")
async def admin(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    language = resolve_language(request)
    return Response(
        content=render_admin_page(read_config(), read_device_state(), language),
        media_type="text/html",
    )


@post("/admin/config")
async def update_config(request: Request) -> Redirect | Response:
    if not is_authorized(request):
        return unauthorized()

    language = resolve_language(request)
    form = await request.form()
    selected_packages = get_form_list(form, "package")
    manual_packages = split_packages(str(form.get("manualPackages") or ""))
    current_config = read_config()
    action = str(form.get("action") or "save")
    lockdown_enabled = form.get("lockdownEnabled") == "1"
    location_request_id = current_config.location_request_id
    if action == "requestLocation":
        location_request_id += 1
    pin = str(form.get("pin") or "").strip() or current_config.pin
    if form.get("clearPin") == "1":
        pin = None
    if pin is not None and (not pin.isdigit() or len(pin) not in range(4, 13)):
        return Response(
            content=message(language, "pin_invalid"),
            status_code=400,
            media_type="text/plain",
        )

    config = write_config(
        selected_packages + manual_packages,
        pin,
        lockdown_enabled,
        location_request_id,
    )
    publish_home_assistant_state(config, read_device_state())
    return Redirect(path=f"/?lang={quote(language)}")


@get("/api/config")
async def api_config(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    return Response(
        content=json.dumps(config_to_api(read_config()), ensure_ascii=False),
        media_type="application/json",
    )


@get("/api/home-assistant/state")
async def api_home_assistant_state(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    return Response(
        content=json.dumps(
            home_assistant_state_payload(read_config(), read_device_state()),
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


@post("/api/home-assistant/config", status_code=200)
async def api_home_assistant_config(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()

    payload = await request.json()
    try:
        config = write_config_from_payload(payload, read_config())
    except ValueError as error:
        return Response(
            content=str(error),
            status_code=400,
            media_type="text/plain",
        )

    device_state = read_device_state()
    publish_home_assistant_state(config, device_state)
    return Response(
        content=json.dumps(
            home_assistant_state_payload(config, device_state),
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


@post("/api/device-state", status_code=200)
async def api_device_state(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()

    payload = await request.json()
    installed_apps = payload.get("installedApps") or []
    normalized_apps = []
    for app in installed_apps:
        package_name = str(app.get("packageName") or "").strip()
        if not package_name:
            continue
        normalized_apps.append(
            {
                "label": str(app.get("label") or package_name),
                "packageName": package_name,
                "isSystem": bool(app.get("isSystem")),
            }
        )

    normalized_apps.sort(key=lambda app: (app["label"].casefold(), app["packageName"]))
    location = normalize_location_payload(payload.get("location"))
    state = {
        "deviceId": payload.get("deviceId"),
        "reportedAt": utc_now(),
        "installedApps": normalized_apps,
        "localAllowedPackages": normalize_packages(payload.get("localAllowedPackages") or []),
        "lockdownEnabled": parse_bool(payload.get("lockdownEnabled")),
        "location": location,
    }
    write_json(DEVICE_STATE_PATH, state)
    publish_home_assistant_state(read_config(), state)
    return Response(content=json.dumps({"ok": True}), media_type="application/json")


def mqtt_env(name: str, default: str = "") -> str:
    return os.getenv(f"HOMECAGE_HA_MQTT_{name}", default)


def mqtt_topic_prefix() -> str:
    return mqtt_env("TOPIC_PREFIX", "homecage").strip().strip("/") or "homecage"


def mqtt_discovery_prefix() -> str:
    return mqtt_env("DISCOVERY_PREFIX", "homeassistant").strip().strip("/") or "homeassistant"


def publish_home_assistant_state(
    config: Config | None = None,
    device_state: dict[str, Any] | None = None,
) -> None:
    client = MQTT_CLIENT
    if client is None:
        return

    payload = home_assistant_state_payload(
        config or read_config(),
        device_state or read_device_state(),
    )
    client.publish(
        f"{mqtt_topic_prefix()}/state",
        json.dumps(payload, ensure_ascii=False),
        retain=True,
    )


def publish_home_assistant_discovery(client: Any) -> None:
    state_topic = f"{mqtt_topic_prefix()}/state"
    command_prefix = f"{mqtt_topic_prefix()}/command"
    discovery_prefix = mqtt_discovery_prefix()
    device = {
        "identifiers": ["homecage_server"],
        "name": "HomeCage",
        "manufacturer": "HomeCage",
        "model": "HomeCage Server",
    }
    configs = {
        f"{discovery_prefix}/switch/homecage/lost_mode/config": {
            "name": "Lost mode",
            "unique_id": "homecage_lost_mode",
            "state_topic": state_topic,
            "command_topic": f"{command_prefix}/lockdown",
            "value_template": "{{ value_json.lockdownEnabled }}",
            "payload_on": "true",
            "payload_off": "false",
            "state_on": "true",
            "state_off": "false",
            "device": device,
        },
        f"{discovery_prefix}/button/homecage/request_location/config": {
            "name": "Request location",
            "unique_id": "homecage_request_location",
            "command_topic": f"{command_prefix}/request_location",
            "payload_press": "request",
            "device": device,
        },
        f"{discovery_prefix}/sensor/homecage/allowed_apps/config": {
            "name": "Allowed apps",
            "unique_id": "homecage_allowed_apps",
            "state_topic": state_topic,
            "value_template": "{{ value_json.allowedPackagesCount }}",
            "json_attributes_topic": state_topic,
            "device": device,
        },
        f"{discovery_prefix}/sensor/homecage/location_status/config": {
            "name": "Location status",
            "unique_id": "homecage_location_status",
            "state_topic": state_topic,
            "value_template": "{{ value_json.location.status if value_json.location else 'unknown' }}",
            "json_attributes_topic": state_topic,
            "device": device,
        },
        f"{discovery_prefix}/sensor/homecage/last_seen/config": {
            "name": "Last phone report",
            "unique_id": "homecage_last_seen",
            "state_topic": state_topic,
            "value_template": "{{ value_json.deviceReportedAt }}",
            "device_class": "timestamp",
            "device": device,
        },
    }
    for topic, payload in configs.items():
        client.publish(topic, json.dumps(payload), retain=True)


def handle_home_assistant_command(topic: str, payload: str) -> None:
    command_prefix = f"{mqtt_topic_prefix()}/command"
    current_config = read_config()
    if topic == f"{command_prefix}/lockdown":
        config = write_config_from_payload(
            {"lockdownEnabled": payload.strip().lower() in {"1", "true", "on"}},
            current_config,
        )
    elif topic == f"{command_prefix}/request_location":
        config = write_config_from_payload({"requestLocation": True}, current_config)
    elif topic == f"{command_prefix}/allowed_packages":
        config = write_config_from_payload({"allowedPackagesText": payload}, current_config)
    else:
        return
    publish_home_assistant_state(config, read_device_state())


def start_home_assistant_mqtt() -> None:
    global MQTT_CLIENT
    host = mqtt_env("HOST")
    if not host:
        return

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        return

    def on_connect(client: Any, _userdata: Any, _flags: Any, _reason_code: Any, _properties: Any = None) -> None:
        command_prefix = f"{mqtt_topic_prefix()}/command"
        client.subscribe(f"{command_prefix}/lockdown")
        client.subscribe(f"{command_prefix}/request_location")
        client.subscribe(f"{command_prefix}/allowed_packages")
        publish_home_assistant_discovery(client)
        publish_home_assistant_state()

    def on_message(_client: Any, _userdata: Any, message: Any) -> None:
        payload = message.payload.decode("utf-8", errors="replace")
        handle_home_assistant_command(message.topic, payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=mqtt_env("CLIENT_ID", "homecage-server"))
    username = mqtt_env("USERNAME")
    password = mqtt_env("PASSWORD")
    if username:
        client.username_pw_set(username, password or None)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, int(mqtt_env("PORT", "1883")), keepalive=60)
    except OSError:
        return
    MQTT_CLIENT = client
    client.loop_start()


def stop_home_assistant_mqtt() -> None:
    global MQTT_CLIENT
    client = MQTT_CLIENT
    MQTT_CLIENT = None
    if client is None:
        return
    client.loop_stop()
    client.disconnect()


app = Litestar(
    route_handlers=[
        admin,
        update_config,
        api_config,
        api_home_assistant_state,
        api_home_assistant_config,
        api_device_state,
    ],
    on_startup=[start_home_assistant_mqtt],
    on_shutdown=[stop_home_assistant_mqtt],
)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=env_value("HOMECAGE_HOST", "0.0.0.0"),
        port=int(env_value("HOMECAGE_PORT", "8000")),
        reload=env_value("HOMECAGE_RELOAD", "") == "1",
    )
