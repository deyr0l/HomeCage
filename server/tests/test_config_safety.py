import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from litestar.testing import TestClient

from server.app import main as server


class ConfigSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="homecage-tests-")
        self.addCleanup(self.directory.cleanup)
        data_dir = Path(self.directory.name)
        self.storage = patch.multiple(
            server,
            DATA_DIR=data_dir,
            CONFIG_PATH=data_dir / "config.json",
            DEVICE_STATE_PATH=data_dir / "device_state.json",
            DEVICES_PATH=data_dir / "devices.json",
            ADMIN_TOKEN="test-token-not-a-real-secret",
        )
        self.storage.start()
        self.addCleanup(self.storage.stop)
        self.client = self.enterContext(TestClient(app=server.app))
        self.headers = {"Authorization": "Bearer test-token-not-a-real-secret"}
        self.rules = [{
            "id": "bedtime", "enabled": True, "days": [1, 2, 3, 4, 5],
            "start": "22:00", "end": "07:00", "mode": "parental",
        }]
        self.device_id = "qa-phone"
        server.write_config(self.device_id, ["com.android.deskclock"], "4826", "parental", self.rules, 3)

    def config(self):
        return server.config_to_api(server.read_config(self.device_id), self.device_id)

    def request(self, method, path, **kwargs):
        return self.client.request(method, path, headers=self.headers, **kwargs)

    def test_поврежденный_файл_не_подменяется_и_не_перезаписывается(self):
        damaged = b'{"devices": broken'
        server.DEVICES_PATH.write_bytes(damaged)
        requests = [
            ("GET", f"/api/config?deviceId={self.device_id}", {}),
            ("GET", "/", {}),
            ("POST", "/api/device-state", {"json": {"deviceId": self.device_id}}),
            ("POST", f"/api/config?deviceId={self.device_id}", {"json": {"requestLocation": True}}),
            ("POST", "/admin/config", {"data": {"deviceId": self.device_id, "action": "requestLocation"}}),
            ("POST", "/api/security-events", {"json": {"deviceId": self.device_id, "triggerPackage": "qa"}}),
        ]
        for method, path, kwargs in requests:
            with self.subTest(маршрут=path):
                response = self.request(method, path, **kwargs)
                self.assertEqual(503, response.status_code)
                self.assertIs(response.json()["configValid"], False)
                self.assertEqual(damaged, server.DEVICES_PATH.read_bytes())

    def test_ошибка_доступа_к_файлу_не_означает_новый_сервер(self):
        before = server.DEVICES_PATH.read_bytes()
        with patch.object(Path, "read_text", side_effect=PermissionError("test access denied")):
            response = self.request("GET", f"/api/config?deviceId={self.device_id}")
        self.assertEqual(503, response.status_code)
        self.assertEqual(before, server.DEVICES_PATH.read_bytes())

    def test_ошибка_записи_сохраняет_последний_исправный_файл(self):
        before = server.DEVICES_PATH.read_bytes()
        for operation in ("write_text", "replace"):
            with self.subTest(операция=operation):
                with patch.object(Path, operation, side_effect=OSError("test disk failure")):
                    response = self.request("POST", f"/api/config?deviceId={self.device_id}", json={"allowedPackages": []})
                self.assertEqual(503, response.status_code)
                self.assertEqual(before, server.DEVICES_PATH.read_bytes())

    def test_неверная_структура_хранилища_отклоняется(self):
        valid = json.loads(server.DEVICES_PATH.read_text())
        cases = [[], {}, {"schemaVersion": 1, "devices": []}, {"schemaVersion": 2, "devices": {}}]
        for field, value in (
            ("allowedPackages", None), ("restrictionMode", "invalid"),
            ("scheduleRules", [{}]), ("updatedAt", ""), ("pin", False),
            ("locationRequestId", -1), ("serverConfigured", "true"),
        ):
            invalid = json.loads(json.dumps(valid))
            invalid["devices"][self.device_id]["config"][field] = value
            cases.append(invalid)
        incomplete = json.loads(json.dumps(valid))
        del incomplete["devices"][self.device_id]["config"]["scheduleRules"]
        cases.append(incomplete)
        for index, value in enumerate(cases):
            with self.subTest(вариант=index):
                encoded = json.dumps(value).encode()
                server.DEVICES_PATH.write_bytes(encoded)
                response = self.request("GET", f"/api/config?deviceId={self.device_id}")
                self.assertEqual(503, response.status_code)
                self.assertEqual(encoded, server.DEVICES_PATH.read_bytes())

    def test_старые_файлы_мигрируют_без_потери_настроек(self):
        server.DEVICES_PATH.unlink()
        server.CONFIG_PATH.write_text(json.dumps({
            "allowedPackages": ["com.android.deskclock"], "pin": "4826",
            "lockdownEnabled": True, "updatedAt": "2026-06-27T10:00:00+00:00",
        }))
        response = self.request("GET", "/api/config?deviceId=legacy")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["configValid"])
        self.assertEqual("lost", response.json()["restrictionMode"])
        self.assertEqual(["com.android.deskclock"], response.json()["allowedPackages"])

    def test_поврежденное_основное_хранилище_не_откатывается_к_старому_файлу(self):
        server.CONFIG_PATH.write_text(json.dumps(server.default_config_data()))
        server.DEVICES_PATH.write_text("broken")
        response = self.request("GET", f"/api/config?deviceId={self.device_id}")
        self.assertEqual(503, response.status_code)

    def test_первый_запуск_принимает_локальный_список_приложений(self):
        response = self.request("POST", "/api/device-state", json={
            "deviceId": "new-phone", "localAllowedPackages": ["com.android.deskclock"],
        })
        self.assertEqual(200, response.status_code)
        response = self.request("GET", "/api/config?deviceId=new-phone")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["configValid"])
        self.assertEqual(1, response.json()["configSchemaVersion"])
        self.assertEqual("new-phone", response.json()["deviceId"])

    def test_потерянный_серверный_конфиг_не_восстанавливается_пустыми_ограничениями(self):
        applied_at = self.config()["updatedAt"]
        server.DEVICES_PATH.unlink()
        response = self.request("POST", "/api/device-state", json={
            "deviceId": self.device_id, "localAllowedPackages": ["com.android.deskclock"],
            "appliedConfigUpdatedAt": applied_at, "restrictionMode": "parental",
        })
        self.assertEqual(200, response.status_code)
        response = self.request("GET", f"/api/config?deviceId={self.device_id}")
        self.assertEqual(503, response.status_code)
        self.assertFalse(response.json()["configValid"])
        self.request("GET", f"/?deviceId={self.device_id}")
        self.assertFalse(self.config()["serverConfigured"])

    def test_неизвестному_телефону_не_отдается_пустой_конфиг(self):
        response = self.request("GET", "/api/config?deviceId=unknown-phone")
        self.assertEqual(503, response.status_code)
        self.assertFalse(response.json()["configValid"])

    def test_явно_сохраненный_пустой_список_валиден(self):
        response = self.request("POST", f"/api/config?deviceId={self.device_id}", json={"allowedPackages": []})
        self.assertEqual(200, response.status_code)
        response = self.request("GET", f"/api/config?deviceId={self.device_id}")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["configValid"])
        self.assertEqual([], response.json()["allowedPackages"])

    def test_запрос_локации_из_старой_формы_игнорирует_все_редактируемые_поля(self):
        before = self.config()
        response = self.request("POST", "/admin/config", data={
            "deviceId": self.device_id, "action": "requestLocation",
            "configUpdatedAt": "old-version", "package": "com.unwanted.app",
            "manualPackages": "com.other.app", "restrictionMode": "none",
            "scheduleRulesText": "", "pin": "invalid", "clearPin": "1",
        }, follow_redirects=False)
        self.assertEqual(302, response.status_code)
        after = self.config()
        for key in ("allowedPackages", "restrictionMode", "scheduleRules", "pin", "serverConfigured"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before["locationRequestId"] + 1, after["locationRequestId"])

    def test_запрос_локации_по_api_сохраняет_настройки(self):
        before = self.config()
        response = self.request("POST", f"/api/config?deviceId={self.device_id}", json={"requestLocation": True})
        self.assertEqual(200, response.status_code)
        after = self.config()
        for key in ("allowedPackages", "restrictionMode", "scheduleRules", "pin"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(4, after["locationRequestId"])

    def test_запрос_локации_не_подтверждает_пустой_конфиг_нового_телефона(self):
        self.request("POST", "/api/device-state", json={"deviceId": "empty-phone"})
        response = self.request("POST", "/api/config?deviceId=empty-phone", json={"requestLocation": True})
        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["configValid"])
        self.assertEqual(503, self.request("GET", "/api/config?deviceId=empty-phone").status_code)

    def test_старая_форма_не_перезаписывает_новые_настройки(self):
        before = self.config()
        for revision in ("old-version", ""):
            with self.subTest(версия=revision):
                response = self.request("POST", "/admin/config?lang=ru", data={
                    "deviceId": self.device_id, "action": "save",
                    "configUpdatedAt": revision, "restrictionMode": "none",
                }, follow_redirects=False)
                self.assertEqual(409, response.status_code)
                self.assertIn("Обновите страницу", response.text)
                self.assertEqual(before, self.config())

    def test_актуальная_форма_может_намеренно_очистить_настройки(self):
        response = self.request("POST", "/admin/config", data={
            "deviceId": self.device_id, "action": "save",
            "configUpdatedAt": self.config()["updatedAt"], "restrictionMode": "none",
            "scheduleRulesText": "",
        }, follow_redirects=False)
        self.assertEqual(302, response.status_code)
        self.assertEqual([], self.config()["allowedPackages"])
        self.assertEqual([], self.config()["scheduleRules"])
        self.assertEqual("none", self.config()["restrictionMode"])

    def test_параллельные_запросы_локации_не_теряют_счетчик(self):
        def request_location(_):
            return self.request("POST", f"/api/config?deviceId={self.device_id}", json={"requestLocation": True}).status_code
        with ThreadPoolExecutor(max_workers=4) as executor:
            self.assertEqual([200] * 8, list(executor.map(request_location, range(8))))
        self.assertEqual(11, self.config()["locationRequestId"])
        self.assertEqual("parental", self.config()["restrictionMode"])

    def test_некорректный_запрос_не_сохраняет_валидный_пустой_конфиг(self):
        before = self.config()
        for payload in (
            {"restrictionMode": "typo"}, {"allowedPackages": [None]}, {"allowedPackages": None},
            {"scheduleRules": [{}]}, {"scheduleRules": None}, {"pin": 4826},
            {"scheduleRulesText": None}, {"allowedPackagesText": None},
            {"scheduleRulesText": "typo"},
            {"scheduleRulesText": "Weekdays 22:00-07:00 parental\nWeekend 25:00-08:00 parental"},
            {"scheduleRules": [{"days": [True], "start": "22:00", "end": "07:00", "mode": "parental"}]},
        ):
            with self.subTest(поле=next(iter(payload))):
                response = self.request("POST", f"/api/config?deviceId={self.device_id}", json=payload)
                self.assertEqual(400, response.status_code)
                self.assertEqual(before, self.config())

    def test_опечатка_в_расписании_веб_формы_не_стирает_старые_правила(self):
        before = self.config()
        response = self.request("POST", "/admin/config", data={
            "deviceId": self.device_id, "action": "save",
            "configUpdatedAt": before["updatedAt"], "restrictionMode": "parental",
            "scheduleRulesText": "Weekdays 25:00-07:00 parental",
        }, follow_redirects=False)
        self.assertEqual(400, response.status_code)
        self.assertEqual(before, self.config())


if __name__ == "__main__":
    unittest.main()
