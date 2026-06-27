from __future__ import annotations

import base64
import html
import json
import os
import threading
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
RESTRICTION_NONE = "none"
RESTRICTION_PARENTAL = "parental"
RESTRICTION_LOST = "lost"
SUPPORTED_RESTRICTION_MODES = (RESTRICTION_NONE, RESTRICTION_PARENTAL, RESTRICTION_LOST)
SUPPORTED_LANGUAGES = ("en", "ru", "es", "zh-CN", "ja")
MAX_SECURITY_EVENTS = 50
MAX_SECURITY_TRAIL_ENTRIES = 10
MAX_SECURITY_FIELD_LENGTH = 180
DATA_LOCK = threading.RLock()
DAY_ALIASES = {
    "mon": 1,
    "monday": 1,
    "tue": 2,
    "tues": 2,
    "tuesday": 2,
    "wed": 3,
    "wednesday": 3,
    "thu": 4,
    "thur": 4,
    "thurs": 4,
    "thursday": 4,
    "fri": 5,
    "friday": 5,
    "sat": 6,
    "saturday": 6,
    "sun": 7,
    "sunday": 7,
}
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
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
        "config_apply_pending": "Waiting for this phone to apply config from {updated_at}.",
        "config_apply_skipped": "Phone skipped app-list update because local settings changed during sync. Restriction mode was still applied.",
        "config_apply_status": "Phone sync",
        "config_apply_success": "Phone applied config from {updated_at}.",
        "no_data": "no data",
        "no_devices": "No phones have reported to this server yet. Configure the server in HomeCage and run sync on the phone.",
        "pin_label": "New PIN, 4-12 digits. Leave empty to keep current. Current state: {pin_status}.",
        "pin_invalid": "PIN must contain 4-12 digits",
        "pin_section": "App PIN",
        "pin_set": "set",
        "pin_unset": "not set",
        "protection_health": "Protection health",
        "protection_health_missing": "not reported",
        "protection_health_summary": "{enabled}/{total} layers enabled",
        "save_config": "Save config",
        "system_badge": "system",
        "title": "HomeCage Admin",
        "allowed_apps": "Allowed apps",
        "request_location": "Request location",
        "restriction_help": "Parent restriction blocks apps but keeps quick calls available. Lost phone blocks both apps and quick calls.",
        "restriction_lost": "Lost phone: full block",
        "restriction_none": "No remote block",
        "restriction_parental": "Parent restriction: allow quick calls",
        "restriction_section": "Remote block mode",
        "schedule_help": "One rule per line: Mon-Fri 22:00-07:00 parental. Supported days: All, Weekdays, Weekends, Mon-Sun. Modes: parental or lost.",
        "schedule_section": "Scheduled block",
        "security_events": "Security events",
        "security_events_empty": "No blocked escape attempts reported yet.",
        "security_event_reason": "Reason",
        "security_event_trail": "Trail",
        "security_event_trigger": "Trigger",
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
        "config_apply_pending": "Ждем, пока телефон применит конфиг от {updated_at}.",
        "config_apply_skipped": "Телефон пропустил обновление списка приложений: локальные настройки изменились во время синхронизации. Режим ограничения все равно применен.",
        "config_apply_status": "Синхронизация телефона",
        "config_apply_success": "Телефон применил конфиг от {updated_at}.",
        "no_data": "нет данных",
        "no_devices": "Телефоны еще не присылали отчеты на этот сервер. Укажите сервер в HomeCage и запустите синхронизацию на телефоне.",
        "pin_label": "Новый PIN, 4-12 цифр. Оставьте пустым, чтобы не менять. Сейчас: {pin_status}.",
        "pin_invalid": "PIN должен содержать 4-12 цифр",
        "pin_section": "PIN приложения",
        "pin_set": "задан",
        "pin_unset": "не задан",
        "protection_health": "Состояние защиты",
        "protection_health_missing": "не передавалось",
        "protection_health_summary": "{enabled}/{total} слоев включено",
        "save_config": "Сохранить конфиг",
        "system_badge": "системное",
        "title": "HomeCage Admin",
        "allowed_apps": "Разрешенные приложения",
        "request_location": "Запросить локацию",
        "restriction_help": "Родительское ограничение блокирует приложения, но оставляет быстрые звонки. Потерянный телефон блокирует и приложения, и быстрые звонки.",
        "restriction_lost": "Телефон утерян: полная блокировка",
        "restriction_none": "Без удаленной блокировки",
        "restriction_parental": "Родительское ограничение: быстрые звонки доступны",
        "restriction_section": "Режим удаленной блокировки",
        "schedule_help": "Одно правило на строку: Mon-Fri 22:00-07:00 parental. Дни: All, Weekdays, Weekends, Mon-Sun. Режимы: parental или lost.",
        "schedule_section": "Блокировка по расписанию",
        "security_events": "События защиты",
        "security_events_empty": "Заблокированные попытки обхода пока не передавались.",
        "security_event_reason": "Причина",
        "security_event_trail": "Цепочка",
        "security_event_trigger": "Триггер",
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
        "config_apply_pending": "Esperando a que este teléfono aplique la config de {updated_at}.",
        "config_apply_skipped": "El teléfono omitió la lista de apps porque los ajustes locales cambiaron durante la sincronización. El modo de restricción sí se aplicó.",
        "config_apply_status": "Sincronización del teléfono",
        "config_apply_success": "El teléfono aplicó la config de {updated_at}.",
        "no_data": "sin datos",
        "no_devices": "Ningún teléfono informó a este servidor todavía. Configura el servidor en HomeCage y ejecuta la sincronización en el teléfono.",
        "pin_label": "Nuevo PIN, 4-12 dígitos. Déjalo vacío para no cambiarlo. Estado actual: {pin_status}.",
        "pin_invalid": "El PIN debe contener 4-12 dígitos",
        "pin_section": "PIN de la app",
        "pin_set": "configurado",
        "pin_unset": "no configurado",
        "protection_health": "Estado de protección",
        "protection_health_missing": "sin reporte",
        "protection_health_summary": "{enabled}/{total} capas activas",
        "save_config": "Guardar config",
        "system_badge": "sistema",
        "title": "HomeCage Admin",
        "allowed_apps": "Apps permitidas",
        "request_location": "Solicitar ubicación",
        "restriction_help": "La restricción parental bloquea apps pero mantiene llamadas rápidas. Modo perdido bloquea apps y llamadas rápidas.",
        "restriction_lost": "Teléfono perdido: bloqueo total",
        "restriction_none": "Sin bloqueo remoto",
        "restriction_parental": "Restricción parental: llamadas rápidas permitidas",
        "restriction_section": "Modo de bloqueo remoto",
        "schedule_help": "Una regla por línea: Mon-Fri 22:00-07:00 parental. Días: All, Weekdays, Weekends, Mon-Sun. Modos: parental o lost.",
        "schedule_section": "Bloqueo programado",
        "security_events": "Eventos de seguridad",
        "security_events_empty": "Aún no se reportaron intentos de evasión bloqueados.",
        "security_event_reason": "Motivo",
        "security_event_trail": "Secuencia",
        "security_event_trigger": "Disparador",
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
        "config_apply_pending": "正在等待此手机应用 {updated_at} 的配置。",
        "config_apply_skipped": "手机跳过了应用列表更新，因为同步时本地设置发生了变化。限制模式仍已应用。",
        "config_apply_status": "手机同步",
        "config_apply_success": "手机已应用 {updated_at} 的配置。",
        "no_data": "无数据",
        "no_devices": "还没有手机向此服务器上报。请在 HomeCage 中配置服务器并在手机上执行同步。",
        "pin_label": "新 PIN，4-12 位数字。留空则不更改。当前状态：{pin_status}。",
        "pin_invalid": "PIN 必须包含 4-12 位数字",
        "pin_section": "应用 PIN",
        "pin_set": "已设置",
        "pin_unset": "未设置",
        "protection_health": "保护状态",
        "protection_health_missing": "未上报",
        "protection_health_summary": "{enabled}/{total} 层已启用",
        "save_config": "保存配置",
        "system_badge": "系统",
        "title": "HomeCage Admin",
        "allowed_apps": "允许的应用",
        "request_location": "请求位置",
        "restriction_help": "家长限制会阻止应用，但保留快速拨号。丢失模式会同时阻止应用和快速拨号。",
        "restriction_lost": "手机丢失：完全阻止",
        "restriction_none": "无远程阻止",
        "restriction_parental": "家长限制：允许快速拨号",
        "restriction_section": "远程阻止模式",
        "schedule_help": "每行一条规则：Mon-Fri 22:00-07:00 parental。日期：All、Weekdays、Weekends、Mon-Sun。模式：parental 或 lost。",
        "schedule_section": "定时阻止",
        "security_events": "安全事件",
        "security_events_empty": "尚未报告被阻止的绕过尝试。",
        "security_event_reason": "原因",
        "security_event_trail": "轨迹",
        "security_event_trigger": "触发项",
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
        "config_apply_pending": "この端末が {updated_at} の設定を適用するのを待っています。",
        "config_apply_skipped": "同期中にローカル設定が変更されたため、端末はアプリ一覧の更新をスキップしました。制限モードは適用済みです。",
        "config_apply_status": "端末同期",
        "config_apply_success": "端末は {updated_at} の設定を適用しました。",
        "no_data": "データなし",
        "no_devices": "このサーバーにはまだ電話からのレポートがありません。HomeCage でサーバーを設定し、電話で同期してください。",
        "pin_label": "新しい PIN、4-12 桁。変更しない場合は空のままにします。現在: {pin_status}。",
        "pin_invalid": "PIN は 4-12 桁の数字で入力してください",
        "pin_section": "アプリ PIN",
        "pin_set": "設定済み",
        "pin_unset": "未設定",
        "protection_health": "保護状態",
        "protection_health_missing": "未報告",
        "protection_health_summary": "{enabled}/{total} レイヤー有効",
        "save_config": "設定を保存",
        "system_badge": "システム",
        "title": "HomeCage Admin",
        "allowed_apps": "許可されたアプリ",
        "request_location": "位置情報をリクエスト",
        "restriction_help": "保護者制限はアプリをブロックし、クイック通話は許可します。紛失モードはアプリとクイック通話の両方をブロックします。",
        "restriction_lost": "紛失端末: 完全ブロック",
        "restriction_none": "リモートブロックなし",
        "restriction_parental": "保護者制限: クイック通話を許可",
        "restriction_section": "リモートブロックモード",
        "schedule_help": "1 行に 1 ルール: Mon-Fri 22:00-07:00 parental。曜日: All, Weekdays, Weekends, Mon-Sun。モード: parental または lost。",
        "schedule_section": "スケジュールブロック",
        "security_events": "セキュリティイベント",
        "security_events_empty": "ブロックされた回避試行はまだ報告されていません。",
        "security_event_reason": "理由",
        "security_event_trail": "履歴",
        "security_event_trigger": "トリガー",
    },
}


@dataclass(frozen=True)
class Config:
    allowed_packages: list[str]
    pin: str | None
    restriction_mode: str
    schedule_rules: list[dict[str, Any]]
    location_request_id: int
    server_configured: bool
    updated_at: str


@dataclass(frozen=True)
class DeviceSummary:
    device_id: str
    name: str
    reported_at: str | None
    allowed_packages_count: int
    restriction_mode: str


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


def normalize_restriction_mode(
    raw_mode: Any,
    legacy_lockdown: Any = None,
    legacy_parental: Any = None,
) -> str:
    mode = str(raw_mode or "").strip().lower().replace("-", "_")
    if mode in {"parental", "parental_lock", "parentalrestriction"}:
        return RESTRICTION_PARENTAL
    if mode in {"lost", "lost_phone", "lockdown"}:
        return RESTRICTION_LOST
    if parse_bool(legacy_parental):
        return RESTRICTION_PARENTAL
    if parse_bool(legacy_lockdown):
        return RESTRICTION_LOST
    return RESTRICTION_NONE


def parse_time(value: Any) -> str | None:
    text = str(value or "").strip()
    if ":" not in text:
        return None
    hours_text, minutes_text = text.split(":", 1)
    try:
        hours = int(hours_text)
        minutes = int(minutes_text)
    except ValueError:
        return None
    if hours not in range(0, 24) or minutes not in range(0, 60):
        return None
    return f"{hours:02d}:{minutes:02d}"


def parse_days(value: Any) -> list[int]:
    if isinstance(value, (list, tuple, set)):
        days = []
        for item in value:
            try:
                day = int(item)
            except (TypeError, ValueError):
                continue
            if day in range(1, 8) and day not in days:
                days.append(day)
        return sorted(days)

    text = str(value or "").strip().lower()
    if not text:
        return []
    if text in {"all", "daily", "everyday", "*"}:
        return list(range(1, 8))
    if text in {"weekday", "weekdays"}:
        return [1, 2, 3, 4, 5]
    if text in {"weekend", "weekends"}:
        return [6, 7]

    days: list[int] = []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_raw, end_raw = [part.strip() for part in token.split("-", 1)]
            start_day = DAY_ALIASES.get(start_raw)
            end_day = DAY_ALIASES.get(end_raw)
            if not start_day or not end_day:
                continue
            current = start_day
            while True:
                if current not in days:
                    days.append(current)
                if current == end_day:
                    break
                current = 1 if current == 7 else current + 1
        else:
            day = DAY_ALIASES.get(token)
            if day and day not in days:
                days.append(day)
    return sorted(days)


def normalize_schedule_rules(raw_rules: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rules, list):
        return []

    rules = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            continue
        start_time = parse_time(raw_rule.get("start"))
        end_time = parse_time(raw_rule.get("end"))
        days = parse_days(raw_rule.get("days"))
        mode = normalize_restriction_mode(raw_rule.get("mode"))
        if not start_time or not end_time or not days or mode == RESTRICTION_NONE:
            continue
        rule_id = str(raw_rule.get("id") or f"rule-{index + 1}").strip()[:40]
        rules.append(
            {
                "id": rule_id or f"rule-{index + 1}",
                "enabled": parse_bool(raw_rule.get("enabled"), default=True),
                "days": days,
                "start": start_time,
                "end": end_time,
                "mode": mode,
            }
        )
    return rules


def parse_schedule_rules_text(raw_text: str) -> list[dict[str, Any]]:
    rules = []
    for line_index, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        days = parse_days(parts[0])
        time_range = parts[1]
        if "-" not in time_range:
            continue
        start_raw, end_raw = time_range.split("-", 1)
        start_time = parse_time(start_raw)
        end_time = parse_time(end_raw)
        mode = normalize_restriction_mode(parts[2] if len(parts) > 2 else RESTRICTION_PARENTAL)
        if not days or not start_time or not end_time or mode == RESTRICTION_NONE:
            continue
        rules.append(
            {
                "id": f"rule-{line_index}",
                "enabled": True,
                "days": days,
                "start": start_time,
                "end": end_time,
                "mode": mode,
            }
        )
    return normalize_schedule_rules(rules)


def days_to_text(days: list[int]) -> str:
    normalized = sorted(day for day in days if day in range(1, 8))
    if normalized == list(range(1, 8)):
        return "All"
    if normalized == [1, 2, 3, 4, 5]:
        return "Weekdays"
    if normalized == [6, 7]:
        return "Weekends"
    return ",".join(DAY_NAMES[day - 1] for day in normalized)


def schedule_rules_to_text(rules: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{days_to_text(rule['days'])} {rule['start']}-{rule['end']} {rule['mode']}"
        for rule in normalize_schedule_rules(rules)
        if rule.get("enabled", True)
    )


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
    temporary_path = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def default_config_data() -> dict[str, Any]:
    return {
        "allowedPackages": [],
        "pin": None,
        "restrictionMode": RESTRICTION_NONE,
        "parentalLockEnabled": False,
        "lockdownEnabled": False,
        "scheduleRules": [],
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
        "restrictionMode": RESTRICTION_NONE,
        "lockdownEnabled": False,
        "appliedConfigUpdatedAt": "",
        "configApplyStatus": "",
        "protectionHealth": {},
        "location": None,
        "securityEvents": [],
    }


def config_from_data(data: dict[str, Any]) -> Config:
    has_configuration_marker = "serverConfigured" in data
    restriction_mode = normalize_restriction_mode(
        data.get("restrictionMode"),
        legacy_lockdown=data.get("lockdownEnabled"),
        legacy_parental=data.get("parentalLockEnabled"),
    )
    is_default_config = (
        not normalize_packages(data.get("allowedPackages", []))
        and not data.get("pin")
        and restriction_mode == RESTRICTION_NONE
        and not normalize_schedule_rules(data.get("scheduleRules", []))
        and max(0, parse_int(data.get("locationRequestId"))) == 0
    )
    return Config(
        allowed_packages=normalize_packages(data.get("allowedPackages", [])),
        pin=data.get("pin") or None,
        restriction_mode=restriction_mode,
        schedule_rules=normalize_schedule_rules(data.get("scheduleRules", [])),
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
        "restrictionMode": config.restriction_mode,
        "parentalLockEnabled": config.restriction_mode == RESTRICTION_PARENTAL,
        "lockdownEnabled": config.restriction_mode == RESTRICTION_LOST,
        "scheduleRules": normalize_schedule_rules(config.schedule_rules),
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
    restriction_mode: str,
    schedule_rules: list[dict[str, Any]] | None,
    location_request_id: int,
    server_configured: bool = True,
) -> Config:
    config = Config(
        allowed_packages=normalize_packages(allowed_packages),
        pin=pin,
        restriction_mode=normalize_restriction_mode(restriction_mode),
        schedule_rules=normalize_schedule_rules(schedule_rules or []),
        location_request_id=max(0, int(location_request_id)),
        server_configured=server_configured,
        updated_at=utc_now(),
    )
    with DATA_LOCK:
        store = read_devices_store()
        device = ensure_device(store, device_id)
        device["config"] = config_to_data(config)
        write_devices_store(store)
    return config


def config_to_api(config: Config, device_id: str) -> dict[str, Any]:
    data = config_to_data(config)
    data["deviceId"] = device_id
    data["scheduleRulesText"] = schedule_rules_to_text(config.schedule_rules)
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
        restriction_mode=config.restriction_mode,
        schedule_rules=config.schedule_rules,
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
                restriction_mode=config.restriction_mode,
            )
        )
    return sorted(summaries, key=lambda item: (item.name.casefold(), item.device_id))


def device_summary_to_api(summary: DeviceSummary) -> dict[str, Any]:
    return {
        "deviceId": summary.device_id,
        "name": summary.name,
        "reportedAt": summary.reported_at,
        "allowedPackagesCount": summary.allowed_packages_count,
        "restrictionMode": summary.restriction_mode,
        "parentalLockEnabled": summary.restriction_mode == RESTRICTION_PARENTAL,
        "lockdownEnabled": summary.restriction_mode == RESTRICTION_LOST,
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

    restriction_mode = current_config.restriction_mode
    if "restrictionMode" in payload:
        restriction_mode = normalize_restriction_mode(payload.get("restrictionMode"))
    elif "parentalLockEnabled" in payload or "lockdownEnabled" in payload:
        restriction_mode = normalize_restriction_mode(
            None,
            legacy_lockdown=payload.get("lockdownEnabled"),
            legacy_parental=payload.get("parentalLockEnabled"),
        )

    schedule_rules = current_config.schedule_rules
    if "scheduleRules" in payload:
        schedule_rules = normalize_schedule_rules(payload.get("scheduleRules"))
    elif "scheduleRulesText" in payload:
        schedule_rules = parse_schedule_rules_text(str(payload.get("scheduleRulesText") or ""))

    return write_config(
        device_id=device_id,
        allowed_packages=allowed_packages,
        pin=pin,
        restriction_mode=restriction_mode,
        schedule_rules=schedule_rules,
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


def config_apply_summary(config: Config, device_state: dict[str, Any], language: str) -> str:
    applied_updated_at = str(device_state.get("appliedConfigUpdatedAt") or "")
    apply_status = str(device_state.get("configApplyStatus") or "")
    if applied_updated_at == config.updated_at and apply_status == "applied":
        return html.escape(
            message(language, "config_apply_success", updated_at=config.updated_at)
        )
    if apply_status == "skipped_local_change":
        return html.escape(message(language, "config_apply_skipped"))
    return html.escape(
        message(language, "config_apply_pending", updated_at=config.updated_at)
    )


def protection_health_summary(device_state: dict[str, Any], language: str) -> str:
    health = device_state.get("protectionHealth")
    if not isinstance(health, dict) or not health:
        return html.escape(message(language, "protection_health_missing"))
    total = len(health)
    enabled = sum(1 for value in health.values() if bool(value))
    details = ", ".join(
        f"{key}={'on' if bool(value) else 'off'}"
        for key, value in sorted(health.items())
    )
    return (
        html.escape(
            message(
                language,
                "protection_health_summary",
                enabled=enabled,
                total=total,
            )
        )
        + f"<br><small>{html.escape(details)}</small>"
    )


def restriction_mode_options(config: Config, language: str) -> str:
    labels = {
        RESTRICTION_NONE: message(language, "restriction_none"),
        RESTRICTION_PARENTAL: message(language, "restriction_parental"),
        RESTRICTION_LOST: message(language, "restriction_lost"),
    }
    options = []
    for mode in SUPPORTED_RESTRICTION_MODES:
        checked = "checked" if config.restriction_mode == mode else ""
        options.append(
            f"""
            <label class="radio-row">
              <input type="radio" name="restrictionMode" value="{html.escape(mode)}" {checked}>
              <span>{html.escape(labels[mode])}</span>
            </label>
            """
        )
    return "\n".join(options)


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


def normalize_protection_health(raw_health: Any) -> dict[str, bool]:
    """Normalize Android-side protection status reported by the phone."""
    if not isinstance(raw_health, dict):
        return {}
    allowed_keys = {
        "deviceOwnerEnabled",
        "deviceAdminEnabled",
        "accessibilityEnabled",
        "overlayEnabled",
        "usageAccessEnabled",
        "callPermissionGranted",
        "locationPermissionGranted",
        "flashlightPermissionGranted",
    }
    return {
        key: bool(raw_health.get(key))
        for key in sorted(allowed_keys)
        if key in raw_health
    }


def bounded_security_text(value: Any) -> str:
    return str(value or "").strip()[:MAX_SECURITY_FIELD_LENGTH]


def millis_to_iso(raw_millis: Any) -> str:
    millis = parse_int(raw_millis)
    if millis <= 0:
        return ""
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()


def normalize_security_trail_entry(raw_entry: Any) -> dict[str, Any] | None:
    """Keep only technical routing metadata from the Android Accessibility trail."""
    if not isinstance(raw_entry, dict):
        return None
    package_name = bounded_security_text(raw_entry.get("packageName"))
    if not package_name:
        return None
    at_millis = max(0, parse_int(raw_entry.get("atMillis")))
    return {
        "atMillis": at_millis,
        "at": millis_to_iso(at_millis),
        "eventType": bounded_security_text(raw_entry.get("eventType")),
        "packageName": package_name,
        "className": bounded_security_text(raw_entry.get("className")),
        "decision": bounded_security_text(raw_entry.get("decision")),
        "restrictionMode": bounded_security_text(raw_entry.get("restrictionMode")),
    }


def normalize_security_event_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    trigger_package = bounded_security_text(payload.get("triggerPackage"))
    if not trigger_package:
        return None
    raw_trail = payload.get("trail") if isinstance(payload.get("trail"), list) else []
    trail = [
        entry
        for entry in (
            normalize_security_trail_entry(raw_entry)
            for raw_entry in raw_trail[-MAX_SECURITY_TRAIL_ENTRIES:]
        )
        if entry is not None
    ]
    reported_at_millis = max(0, parse_int(payload.get("reportedAtMillis")))
    return {
        "receivedAt": utc_now(),
        "reportedAtMillis": reported_at_millis,
        "reportedAt": millis_to_iso(reported_at_millis),
        "triggerPackage": trigger_package,
        "triggerClassName": bounded_security_text(payload.get("triggerClassName")),
        "reason": bounded_security_text(payload.get("reason")),
        "trail": trail,
    }


def append_security_event(device: dict[str, Any], event: dict[str, Any]) -> None:
    state = device.get("state") if isinstance(device.get("state"), dict) else {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("deviceId", device.get("deviceId"))
    state.setdefault("deviceName", device.get("name"))
    events = state.get("securityEvents") if isinstance(state.get("securityEvents"), list) else []
    state["securityEvents"] = (events + [event])[-MAX_SECURITY_EVENTS:]
    device["state"] = state


def security_events_html(device_state: dict[str, Any], language: str) -> str:
    events = device_state.get("securityEvents")
    if not isinstance(events, list) or not events:
        return f"<p class='muted'>{html.escape(message(language, 'security_events_empty'))}</p>"

    blocks = []
    for event in reversed(events[-5:]):
        if not isinstance(event, dict):
            continue
        trigger = html.escape(str(event.get("triggerPackage") or ""))
        reason = html.escape(str(event.get("reason") or ""))
        received_at = html.escape(str(event.get("receivedAt") or ""))
        trigger_class = html.escape(str(event.get("triggerClassName") or ""))
        trail = event.get("trail") if isinstance(event.get("trail"), list) else []
        trail_items = []
        for entry in trail:
            if not isinstance(entry, dict):
                continue
            package_name = html.escape(str(entry.get("packageName") or ""))
            class_name = html.escape(str(entry.get("className") or ""))
            event_type = html.escape(str(entry.get("eventType") or ""))
            decision = html.escape(str(entry.get("decision") or ""))
            mode = html.escape(str(entry.get("restrictionMode") or ""))
            at = html.escape(str(entry.get("at") or ""))
            trail_items.append(
                f"""
                <li>
                  <code>{package_name}</code>
                  <small>{class_name}<br>{event_type} · {decision} · {mode} · {at}</small>
                </li>
                """
            )
        trail_html = "\n".join(trail_items)
        blocks.append(
            f"""
            <details class="security-event">
              <summary><strong>{trigger}</strong> · {reason} · {received_at}</summary>
              <p class="muted">
                <strong>{html.escape(message(language, "security_event_trigger"))}:</strong>
                {trigger}<br>
                <strong>{html.escape(message(language, "security_event_reason"))}:</strong>
                {reason}<br>
                <small>{trigger_class}</small>
              </p>
              <strong>{html.escape(message(language, "security_event_trail"))}</strong>
              <ol class="trail-list">{trail_html}</ol>
            </details>
            """
        )
    return "\n".join(blocks) or f"<p class='muted'>{html.escape(message(language, 'security_events_empty'))}</p>"


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
    location_html = location_summary(device_state, language)
    location_request_html = location_request_summary(config, device_state, language)
    config_apply_html = config_apply_summary(config, device_state, language)
    protection_health_html = protection_health_summary(device_state, language)
    security_events = security_events_html(device_state, language)
    restriction_options = restriction_mode_options(config, language)
    schedule_rules_text = html.escape(schedule_rules_to_text(config.schedule_rules))
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
	    .radio-row {{
	      display: flex;
	      align-items: center;
	      gap: 10px;
	      border: 1px solid #e5e7eb;
	      border-radius: 8px;
	      padding: 10px;
	      margin: 8px 0;
	      cursor: pointer;
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
	    .security-event {{
	      border: 1px solid #e5e7eb;
	      border-radius: 8px;
	      padding: 10px;
	      margin: 8px 0;
	    }}
	    .security-event summary {{
	      cursor: pointer;
	      word-break: break-word;
	    }}
	    .trail-list {{
	      display: grid;
	      gap: 8px;
	      padding-left: 22px;
	    }}
	    .trail-list code {{
	      word-break: break-word;
	    }}
	    .trail-list small {{
	      display: block;
	      color: #64748b;
	      word-break: break-word;
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
		      <span>{html.escape(message(language, "config_apply_status"))}: {config_apply_html}</span>
		      <span>{html.escape(message(language, "protection_health"))}: {protection_health_html}</span>
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
	        <h2>{html.escape(message(language, "restriction_section"))}</h2>
	        {restriction_options}
	        <p class="muted">{html.escape(message(language, "restriction_help"))}</p>
	      </section>
	      <section class="panel">
	        <h2>{html.escape(message(language, "schedule_section"))}</h2>
	        <label class="field">
	          {html.escape(message(language, "schedule_help"))}
	          <textarea name="scheduleRulesText" spellcheck="false">{schedule_rules_text}</textarea>
	        </label>
	      </section>
	      <section class="panel">
	        <h2>{html.escape(message(language, "location_request"))}</h2>
	        <p class="muted">{location_request_html}</p>
	        <p class="muted"><strong>{html.escape(message(language, "latest_location"))}:</strong><br>{location_html}</p>
	        <button type="submit" name="action" value="requestLocation">{html.escape(message(language, "request_location"))}</button>
	      </section>
	      <section class="panel">
	        <h2>{html.escape(message(language, "security_events"))}</h2>
	        {security_events}
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
    restriction_mode = normalize_restriction_mode(form.get("restrictionMode"))
    schedule_rules = parse_schedule_rules_text(str(form.get("scheduleRulesText") or ""))
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

    write_config(
        device_id,
        selected_packages + manual_packages,
        pin,
        restriction_mode,
        schedule_rules,
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
    with DATA_LOCK:
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
        restriction_mode = normalize_restriction_mode(
            payload.get("restrictionMode"),
            legacy_lockdown=payload.get("lockdownEnabled"),
            legacy_parental=payload.get("parentalLockEnabled"),
        )
        applied_config_updated_at = str(
            payload.get("appliedConfigUpdatedAt")
            or previous_state.get("appliedConfigUpdatedAt")
            or ""
        )
        config_apply_status = str(
            payload.get("configApplyStatus")
            or previous_state.get("configApplyStatus")
            or ""
        )
        protection_health = normalize_protection_health(
            payload.get("protectionHealth")
            or previous_state.get("protectionHealth")
            or {}
        )
        security_events = (
            previous_state.get("securityEvents")
            if isinstance(previous_state.get("securityEvents"), list)
            else []
        )
        state = {
            "deviceId": device_id,
            "deviceName": device_name,
            "reportedAt": utc_now(),
            "installedApps": normalized_apps,
            "localAllowedPackages": normalize_packages(payload.get("localAllowedPackages") or []),
            "restrictionMode": restriction_mode,
            "parentalLockEnabled": restriction_mode == RESTRICTION_PARENTAL,
            "lockdownEnabled": restriction_mode == RESTRICTION_LOST,
            "appliedConfigUpdatedAt": applied_config_updated_at,
            "configApplyStatus": config_apply_status,
            "protectionHealth": protection_health,
            "location": location,
            "securityEvents": security_events[-MAX_SECURITY_EVENTS:],
        }
        device["name"] = device_name
        device["state"] = state
        write_devices_store(store)
    return Response(content=json.dumps({"ok": True}), media_type="application/json")


@post("/api/security-events", status_code=200)
async def api_security_event(request: Request) -> Response:
    if not is_authorized(request):
        return unauthorized()

    payload = await request.json()
    if not isinstance(payload, dict):
        return Response(
            content="invalid payload",
            status_code=400,
            media_type="text/plain",
        )
    event = normalize_security_event_payload(payload)
    if event is None:
        return Response(
            content="triggerPackage is required",
            status_code=400,
            media_type="text/plain",
        )

    device_id = normalize_device_id(payload.get("deviceId"))
    device_name = normalize_device_name(payload.get("deviceName"), device_id)
    with DATA_LOCK:
        store = read_devices_store()
        device = ensure_device(store, device_id, device_name)
        append_security_event(device, event)
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
        api_security_event,
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
