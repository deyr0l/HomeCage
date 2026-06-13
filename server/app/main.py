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
DEVICES_PATH = DATA_DIR / "devices.json"
ADMIN_TOKEN = env_value("HOMECAGE_ADMIN_TOKEN", "")
LEGACY_DEVICE_ID = "legacy"
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
        "device": "Device",
        "device_id": "Device ID",
        "devices": "Devices",
        "extra_packages": "Additional package names",
        "extra_packages_help": "Packages missing from the last phone report",
        "language": "Language",
        "last_phone_report": "Phone report",
        "latest_location": "Latest location",
        "location_not_reported": "not reported",
        "location_no_request": "No location request has been sent yet.",
        "location_pending": "Request #{request_id} is waiting for the next phone sync.",
        "location_reported": "Request #{request_id} answered at {reported_at}.",
        "location_request": "Location request",
        "location_status": "Location status: {status}",
        "lockdown_enabled": "Enable lost mode",
        "lockdown_help": "When lost mode is enabled, the phone blocks apps, quick calls, launchers, installers, and settings until the server turns it off.",
        "lockdown_section": "Lost mode",
        "no_data": "no data",
        "no_devices": "No phones have reported to this server yet. Configure the server in HomeCage and run sync on the phone.",
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
        "device": "Устройство",
        "device_id": "ID устройства",
        "devices": "Устройства",
        "extra_packages": "Дополнительные package names",
        "extra_packages_help": "Пакеты, которых нет в последнем отчете телефона",
        "language": "Язык",
        "last_phone_report": "Отчет телефона",
        "latest_location": "Последняя локация",
        "location_not_reported": "не передавалась",
        "location_no_request": "Запрос локации еще не отправлялся.",
        "location_pending": "Запрос #{request_id} ждет следующей синхронизации телефона.",
        "location_reported": "Запрос #{request_id} обработан в {reported_at}.",
        "location_request": "Запрос локации",
        "location_status": "Статус локации: {status}",
        "lockdown_enabled": "Включить режим потерянного телефона",
        "lockdown_help": "Когда режим включен, телефон блокирует приложения, быстрые вызовы, лаунчеры, установщики и настройки, пока сервер не выключит режим.",
        "lockdown_section": "Режим потери",
        "no_data": "нет данных",
        "no_devices": "Телефоны еще не присылали отчеты на этот сервер. Укажите сервер в HomeCage и запустите синхронизацию на телефоне.",
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
        "device": "Dispositivo",
        "device_id": "ID de dispositivo",
        "devices": "Dispositivos",
        "extra_packages": "Nombres de paquete adicionales",
        "extra_packages_help": "Paquetes que no aparecen en el último informe del teléfono",
        "language": "Idioma",
        "last_phone_report": "Informe del teléfono",
        "latest_location": "Última ubicación",
        "location_not_reported": "sin reporte",
        "location_no_request": "Aún no se envió ninguna solicitud de ubicación.",
        "location_pending": "La solicitud #{request_id} espera la próxima sincronización del teléfono.",
        "location_reported": "La solicitud #{request_id} fue respondida a las {reported_at}.",
        "location_request": "Solicitud de ubicación",
        "location_status": "Estado de ubicación: {status}",
        "lockdown_enabled": "Activar modo perdido",
        "lockdown_help": "Cuando el modo perdido está activo, el teléfono bloquea apps, llamadas rápidas, launchers, instaladores y ajustes hasta que el servidor lo desactive.",
        "lockdown_section": "Modo perdido",
        "no_data": "sin datos",
        "no_devices": "Ningún teléfono informó a este servidor todavía. Configura el servidor en HomeCage y ejecuta la sincronización en el teléfono.",
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
        "device": "设备",
        "device_id": "设备 ID",
        "devices": "设备",
        "extra_packages": "额外包名",
        "extra_packages_help": "上次手机报告中缺失的包名",
        "language": "语言",
        "last_phone_report": "手机报告",
        "latest_location": "最新位置",
        "location_not_reported": "未上报",
        "location_no_request": "尚未发送位置请求。",
        "location_pending": "请求 #{request_id} 正在等待手机下次同步。",
        "location_reported": "请求 #{request_id} 已在 {reported_at} 响应。",
        "location_request": "位置请求",
        "location_status": "位置状态：{status}",
        "lockdown_enabled": "启用丢失模式",
        "lockdown_help": "启用丢失模式后，手机会阻止应用、快速拨号、启动器、安装器和设置，直到服务器关闭该模式。",
        "lockdown_section": "丢失模式",
        "no_data": "无数据",
        "no_devices": "还没有手机向此服务器上报。请在 HomeCage 中配置服务器并在手机上执行同步。",
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
        "device": "端末",
        "device_id": "端末 ID",
        "devices": "端末",
        "extra_packages": "追加パッケージ名",
        "extra_packages_help": "最後の電話レポートにないパッケージ",
        "language": "言語",
        "last_phone_report": "電話レポート",
        "latest_location": "最新の位置情報",
        "location_not_reported": "未報告",
        "location_no_request": "位置情報リクエストはまだ送信されていません。",
        "location_pending": "リクエスト #{request_id} は次回の電話同期を待っています。",
        "location_reported": "リクエスト #{request_id} は {reported_at} に応答されました。",
        "location_request": "位置情報リクエスト",
        "location_status": "位置情報ステータス: {status}",
        "lockdown_enabled": "紛失モードを有効化",
        "lockdown_help": "紛失モードが有効な間、サーバーが解除するまでアプリ、クイック通話、ランチャー、インストーラー、設定をブロックします。",
        "lockdown_section": "紛失モード",
        "no_data": "データなし",
        "no_devices": "このサーバーにはまだ電話からのレポートがありません。HomeCage でサーバーを設定し、電話で同期してください。",
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
    server_configured: bool
    updated_at: str


@dataclass(frozen=True)
class DeviceSummary:
    device_id: str
    name: str
    reported_at: str | None
    allowed_packages_count: int
    lockdown_enabled: bool


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


def default_config_data() -> dict[str, Any]:
    return {
        "allowedPackages": [],
        "pin": None,
        "lockdownEnabled": False,
        "locationRequestId": 0,
        "serverConfigured": False,
        "updatedAt": utc_now(),
    }


def default_device_state(device_id: str, device_name: str) -> dict[str, Any]:
    return {
        "deviceId": device_id,
        "deviceName": device_name,
        "reportedAt": None,
        "installedApps": [],
        "localAllowedPackages": [],
        "lockdownEnabled": False,
        "location": None,
    }


def config_from_data(data: dict[str, Any]) -> Config:
    has_configuration_marker = "serverConfigured" in data
    is_default_config = (
        not normalize_packages(data.get("allowedPackages", []))
        and not data.get("pin")
        and not parse_bool(data.get("lockdownEnabled"))
        and max(0, parse_int(data.get("locationRequestId"))) == 0
    )
    return Config(
        allowed_packages=normalize_packages(data.get("allowedPackages", [])),
        pin=data.get("pin") or None,
        lockdown_enabled=parse_bool(data.get("lockdownEnabled")),
        location_request_id=max(0, parse_int(data.get("locationRequestId"))),
        server_configured=(
            parse_bool(data.get("serverConfigured"))
            if has_configuration_marker
            else not is_default_config
        ),
        updated_at=data.get("updatedAt") or utc_now(),
    )


def config_to_data(config: Config) -> dict[str, Any]:
    return {
        "allowedPackages": config.allowed_packages,
        "pin": config.pin,
        "lockdownEnabled": config.lockdown_enabled,
        "locationRequestId": config.location_request_id,
        "serverConfigured": config.server_configured,
        "updatedAt": config.updated_at,
    }


def normalize_device_id(raw_device_id: Any) -> str:
    device_id = str(raw_device_id or "").strip()
    return device_id or LEGACY_DEVICE_ID


def normalize_device_name(raw_name: Any, fallback: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        name = fallback
    return name[:80]


def legacy_devices_store() -> dict[str, Any]:
    if not CONFIG_PATH.exists() and not DEVICE_STATE_PATH.exists():
        return {"schemaVersion": 1, "devices": {}}

    config_data = read_json(CONFIG_PATH, default_config_data())
    state = read_json(
        DEVICE_STATE_PATH,
        default_device_state(LEGACY_DEVICE_ID, "Legacy device"),
    )
    device_id = normalize_device_id(state.get("deviceId") or LEGACY_DEVICE_ID)
    device_name = normalize_device_name(
        state.get("deviceName") or state.get("deviceModel"),
        "Legacy device",
    )
    state["deviceId"] = device_id
    state["deviceName"] = device_name
    return {
        "schemaVersion": 1,
        "devices": {
            device_id: {
                "deviceId": device_id,
                "name": device_name,
                "config": config_data,
                "state": state,
            }
        },
    }


def read_devices_store() -> dict[str, Any]:
    store = read_json(DEVICES_PATH, {})
    devices = store.get("devices")
    if isinstance(devices, dict):
        return {"schemaVersion": 1, "devices": devices}
    return legacy_devices_store()


def write_devices_store(store: dict[str, Any]) -> None:
    write_json(DEVICES_PATH, {"schemaVersion": 1, "devices": store.get("devices", {})})


def ensure_device(
    store: dict[str, Any],
    device_id: str,
    device_name: str | None = None,
) -> dict[str, Any]:
    devices = store.setdefault("devices", {})
    normalized_id = normalize_device_id(device_id)
    existing = devices.get(normalized_id)
    name = normalize_device_name(device_name, normalized_id)
    if not isinstance(existing, dict):
        existing = {
            "deviceId": normalized_id,
            "name": name,
            "config": default_config_data(),
            "state": default_device_state(normalized_id, name),
        }
        devices[normalized_id] = existing
    elif device_name:
        existing["name"] = name
        state = existing.setdefault("state", default_device_state(normalized_id, name))
        if isinstance(state, dict):
            state["deviceName"] = name
    return existing


def first_device_id(store: dict[str, Any]) -> str | None:
    devices = store.get("devices", {})
    if not isinstance(devices, dict) or not devices:
        return None
    return sorted(devices.keys())[0]


def resolve_device_id(
    request: Request,
    store: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> str | None:
    raw_device_id = request.query_params.get("deviceId")
    if payload is not None and not raw_device_id:
        raw_device_id = payload.get("deviceId")
    if raw_device_id:
        return normalize_device_id(raw_device_id)
    return first_device_id(store)


def read_config(device_id: str) -> Config:
    store = read_devices_store()
    device = ensure_device(store, device_id)
    return config_from_data(device.get("config", default_config_data()))


def write_config(
    device_id: str,
    allowed_packages: list[str],
    pin: str | None,
    lockdown_enabled: bool,
    location_request_id: int,
    server_configured: bool = True,
) -> Config:
    config = Config(
        allowed_packages=normalize_packages(allowed_packages),
        pin=pin,
        lockdown_enabled=lockdown_enabled,
        location_request_id=max(0, int(location_request_id)),
        server_configured=server_configured,
        updated_at=utc_now(),
    )
    store = read_devices_store()
    device = ensure_device(store, device_id)
    device["config"] = config_to_data(config)
    write_devices_store(store)
    return config


def config_to_api(config: Config, device_id: str) -> dict[str, Any]:
    data = config_to_data(config)
    data["deviceId"] = device_id
    return data


def maybe_bootstrap_config_from_device_state(
    device: dict[str, Any],
    local_allowed_packages: Any,
) -> bool:
    config = config_from_data(device.get("config", default_config_data()))
    if config.server_configured:
        return False

    allowed_packages = normalize_packages(local_allowed_packages)
    if not allowed_packages:
        return False

    bootstrapped_config = Config(
        allowed_packages=allowed_packages,
        pin=config.pin,
        lockdown_enabled=config.lockdown_enabled,
        location_request_id=config.location_request_id,
        server_configured=True,
        updated_at=utc_now(),
    )
    device["config"] = config_to_data(bootstrapped_config)
    return True


def maybe_bootstrap_config_from_stored_state(
    store: dict[str, Any],
    device_id: str,
) -> bool:
    device = ensure_device(store, device_id)
    state = device.get("state") if isinstance(device.get("state"), dict) else {}
    return maybe_bootstrap_config_from_device_state(
        device,
        state.get("localAllowedPackages") if isinstance(state, dict) else None,
    )


def device_state_for(store: dict[str, Any], device_id: str) -> dict[str, Any]:
    device = ensure_device(store, device_id)
    state = device.get("state")
    if isinstance(state, dict):
        return state
    return default_device_state(device_id, str(device.get("name") or device_id))


def list_device_summaries(store: dict[str, Any]) -> list[DeviceSummary]:
    devices = store.get("devices", {})
    summaries: list[DeviceSummary] = []
    if not isinstance(devices, dict):
        return summaries
    for device_id, raw_device in devices.items():
        if not isinstance(raw_device, dict):
            continue
        config = config_from_data(raw_device.get("config", default_config_data()))
        state = raw_device.get("state") if isinstance(raw_device.get("state"), dict) else {}
        summaries.append(
            DeviceSummary(
                device_id=str(device_id),
                name=normalize_device_name(raw_device.get("name"), str(device_id)),
                reported_at=state.get("reportedAt"),
                allowed_packages_count=len(config.allowed_packages),
                lockdown_enabled=config.lockdown_enabled,
            )
        )
    return sorted(summaries, key=lambda item: (item.name.casefold(), item.device_id))


def device_summary_to_api(summary: DeviceSummary) -> dict[str, Any]:
    return {
        "deviceId": summary.device_id,
        "name": summary.name,
        "reportedAt": summary.reported_at,
        "allowedPackagesCount": summary.allowed_packages_count,
        "lockdownEnabled": summary.lockdown_enabled,
    }


def write_config_from_payload(
    device_id: str,
    payload: dict[str, Any],
    current_config: Config,
) -> Config:
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
        device_id=device_id,
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
            try:
                return [str(value) for value in getter(key)]
            except KeyError:
                return []

    value = form.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [str(value)]


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


def location_request_summary(config: Config, device_state: dict[str, Any], language: str) -> str:
    if config.location_request_id <= 0:
        return html.escape(message(language, "location_no_request"))

    location = device_state.get("location")
    reported_request_id = 0
    reported_at = message(language, "no_data")
    if isinstance(location, dict):
        reported_request_id = parse_int(location.get("requestId"))
        reported_at = str(location.get("reportedAt") or reported_at)

    if reported_request_id >= config.location_request_id:
        return html.escape(
            message(
                language,
                "location_reported",
                request_id=config.location_request_id,
                reported_at=reported_at,
            )
        )

    return html.escape(
        message(
            language,
            "location_pending",
            request_id=config.location_request_id,
        )
    )


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


def render_admin_page(
    config: Config,
    device_state: dict[str, Any],
    devices: list[DeviceSummary],
    selected_device_id: str | None,
    language: str,
) -> str:
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
    location_request_html = location_request_summary(config, device_state, language)
    page_title = html.escape(message(language, "title"))
    selected_device = next(
        (device for device in devices if device.device_id == selected_device_id),
        None,
    )
    device_links = " ".join(
        (
            f"<strong>{html.escape(device.name)}</strong>"
            if device.device_id == selected_device_id
            else (
                f"<a href='/?lang={quote(language)}&deviceId={quote(device.device_id)}'>"
                f"{html.escape(device.name)}</a>"
            )
        )
        for device in devices
    ) or f"<span>{html.escape(message(language, 'no_devices'))}</span>"
    device_query = f"&deviceId={quote(selected_device_id)}" if selected_device_id else ""
    language_links = " ".join(
        (
            f"<strong>{html.escape(LANGUAGE_LABELS[code])}</strong>"
            if code == language
            else f"<a href='/?lang={quote(code)}{device_query}'>{html.escape(LANGUAGE_LABELS[code])}</a>"
        )
        for code in SUPPORTED_LANGUAGES
    )
    form_action = f"/admin/config?lang={quote(language)}{device_query}"
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
    .language-switch strong,
    .device-switch a,
    .device-switch strong,
    .device-switch span {{
      color: white;
      text-decoration: none;
      border: 1px solid rgba(255, 255, 255, 0.24);
      border-radius: 999px;
      padding: 6px 10px;
    }}
    .language-switch strong,
    .device-switch strong {{
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
      <span>{html.escape(message(language, "device"))}: {html.escape(selected_device.name if selected_device else message(language, "no_data"))}</span>
    </div>
    <nav class="language-switch device-switch" aria-label="{html.escape(message(language, "devices"))}">
      {device_links}
    </nav>
    <nav class="language-switch" aria-label="{html.escape(message(language, "language"))}">
      {language_links}
    </nav>
  </header>
  <main>
    <form method="post" action="{form_action}">
      <input type="hidden" name="deviceId" value="{html.escape(selected_device_id or '')}">
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
        <p class="muted">{location_request_html}</p>
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
    store = read_devices_store()
    selected_device_id = resolve_device_id(request, store)
    devices = list_device_summaries(store)
    if selected_device_id:
        if maybe_bootstrap_config_from_stored_state(store, selected_device_id):
            write_devices_store(store)
            devices = list_device_summaries(store)
        config = read_config(selected_device_id)
        device_state = device_state_for(store, selected_device_id)
    else:
        config = config_from_data(default_config_data())
        device_state = default_device_state("", "")
    return Response(
        content=render_admin_page(
            config,
            device_state,
            devices,
            selected_device_id,
            language,
        ),
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
    store = read_devices_store()
    device_id = resolve_device_id(request, store, {"deviceId": form.get("deviceId")})
    if not device_id:
        return Response(
            content=message(language, "no_devices"),
            status_code=400,
            media_type="text/plain",
        )
    current_config = read_config(device_id)
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
        device_id,
        selected_packages + manual_packages,
        pin,
        lockdown_enabled,
        location_request_id,
    )
    return Redirect(path=f"/?lang={quote(language)}&deviceId={quote(device_id)}")


@get("/api/config")
async def api_config(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    store = read_devices_store()
    device_id = resolve_device_id(request, store)
    if not device_id:
        device_id = normalize_device_id(request.query_params.get("deviceId"))
        ensure_device(
            store,
            device_id,
            request.query_params.get("deviceName"),
        )
        write_devices_store(store)
    elif maybe_bootstrap_config_from_stored_state(store, device_id):
        write_devices_store(store)
    return Response(
        content=json.dumps(
            config_to_api(read_config(device_id), device_id),
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


@get("/api/devices")
async def api_devices(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    store = read_devices_store()
    devices = [device_summary_to_api(device) for device in list_device_summaries(store)]
    return Response(
        content=json.dumps({"devices": devices}, ensure_ascii=False),
        media_type="application/json",
    )


@post("/api/config", status_code=200)
async def api_update_config(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()

    payload = await request.json()
    store = read_devices_store()
    device_id = resolve_device_id(request, store, payload)
    if not device_id:
        return Response(
            content="deviceId is required",
            status_code=400,
            media_type="text/plain",
        )
    ensure_device(store, device_id, payload.get("deviceName"))
    write_devices_store(store)
    try:
        config = write_config_from_payload(device_id, payload, read_config(device_id))
    except ValueError as error:
        return Response(
            content=str(error),
            status_code=400,
            media_type="text/plain",
        )

    return Response(
        content=json.dumps(config_to_api(config, device_id), ensure_ascii=False),
        media_type="application/json",
    )


@get("/api/device-state")
async def api_get_device_state(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()
    store = read_devices_store()
    device_id = resolve_device_id(request, store)
    if not device_id:
        return Response(
            content="deviceId is required",
            status_code=400,
            media_type="text/plain",
        )
    return Response(
        content=json.dumps(device_state_for(store, device_id), ensure_ascii=False),
        media_type="application/json",
    )


@post("/api/device-state", status_code=200)
async def api_device_state(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()

    payload = await request.json()
    device_id = normalize_device_id(payload.get("deviceId"))
    device_name = normalize_device_name(payload.get("deviceName"), device_id)
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
    store = read_devices_store()
    device = ensure_device(store, device_id, device_name)
    maybe_bootstrap_config_from_device_state(
        device,
        payload.get("localAllowedPackages"),
    )
    previous_state = device.get("state") if isinstance(device.get("state"), dict) else {}
    previous_location = previous_state.get("location") if isinstance(previous_state, dict) else None
    location = (
        normalize_location_payload(payload.get("location"))
        if "location" in payload
        else previous_location
    )
    state = {
        "deviceId": device_id,
        "deviceName": device_name,
        "reportedAt": utc_now(),
        "installedApps": normalized_apps,
        "localAllowedPackages": normalize_packages(payload.get("localAllowedPackages") or []),
        "lockdownEnabled": parse_bool(payload.get("lockdownEnabled")),
        "location": location,
    }
    device["name"] = device_name
    device["state"] = state
    write_devices_store(store)
    return Response(content=json.dumps({"ok": True}), media_type="application/json")


app = Litestar(
    route_handlers=[
        admin,
        update_config,
        api_config,
        api_devices,
        api_update_config,
        api_get_device_state,
        api_device_state,
    ]
)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=env_value("HOMECAGE_HOST", "0.0.0.0"),
        port=int(env_value("HOMECAGE_PORT", "8000")),
        reload=env_value("HOMECAGE_RELOAD", "") == "1",
    )
