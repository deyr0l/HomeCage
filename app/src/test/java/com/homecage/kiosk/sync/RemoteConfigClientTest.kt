package com.homecage.kiosk.sync

import com.homecage.kiosk.data.RestrictionMode
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class RemoteConfigClientTest {
    private fun config() = JSONObject(
        """{
          "configValid":true,"configSchemaVersion":1,"serverConfigured":true,
          "deviceId":"qa-phone","updatedAt":"2026-10-18T10:00:00+00:00",
          "allowedPackages":["com.android.deskclock"],"pin":null,
          "restrictionMode":"parental","locationRequestId":3,
          "scheduleRules":[{
            "id":"bedtime","enabled":true,"days":[1,2,3,4,5],
            "start":"22:00","end":"07:00","mode":"parental"
          }]
        }"""
    )

    private fun parse(value: JSONObject, previousRevision: String = "") =
        RemoteConfigClient.parseConfig(value.toString(), "qa-phone", previousRevision)

    @Test
    fun `полный подтверждённый конфиг принимается без потери полей`() {
        val result = parse(config())
        assertEquals(setOf("com.android.deskclock"), result.allowedPackages)
        assertEquals(RestrictionMode.PARENTAL, result.restrictionMode)
        assertEquals(3L, result.locationRequestId)
        assertEquals(1, result.scheduleRules.size)
        assertEquals(22 * 60, result.scheduleRules.single().startMinutes)
        assertNull(result.pin)
    }

    @Test
    fun `намеренно сохранённые пустые приложения и расписание допустимы`() {
        val value = config().put("allowedPackages", JSONArray()).put("scheduleRules", JSONArray())
            .put("restrictionMode", "none")
        val result = parse(value)
        assertTrue(result.allowedPackages.isEmpty())
        assertTrue(result.scheduleRules.isEmpty())
        assertEquals(RestrictionMode.NONE, result.restrictionMode)
    }

    @Test
    fun `отсутствующее поле не превращается в пустую настройку`() {
        for (key in listOf(
            "configValid", "configSchemaVersion", "serverConfigured", "deviceId", "updatedAt",
            "allowedPackages", "pin", "restrictionMode", "locationRequestId", "scheduleRules"
        )) {
            val value = config().apply { remove(key) }
            assertThrows("Отсутствует поле $key", Exception::class.java) { parse(value) }
        }
    }

    @Test
    fun `неподтверждённый ошибочный и чужой конфиг отклоняются целиком`() {
        val cases = listOf(
            "Пустой объект" to JSONObject(),
            "Ошибка сервера с HTTP 200" to JSONObject("""{"error":"unavailable"}"""),
            "Сервер не подтвердил конфиг" to config().put("configValid", false),
            "Конфиг не настроен" to config().put("serverConfigured", false),
            "Текст вместо флага" to config().put("configValid", "true"),
            "Неизвестная версия" to config().put("configSchemaVersion", 2),
            "Дробная версия" to config().put("configSchemaVersion", 1.5),
            "Другой телефон" to config().put("deviceId", "other-phone"),
            "Нет даты" to config().put("updatedAt", ""),
            "Неверная дата" to config().put("updatedAt", "yesterday"),
            "Дата без часового пояса" to config().put("updatedAt", "2026-10-18T10:00:00"),
            "Пустое значение списка" to config().put("allowedPackages", JSONObject.NULL),
            "Строка вместо списка" to config().put("allowedPackages", "com.android.deskclock"),
            "Число вместо пакета" to config().put("allowedPackages", JSONArray().put(42)),
            "Пустой пакет" to config().put("allowedPackages", JSONArray().put(" ")),
            "Опечатка в режиме" to config().put("restrictionMode", "parentl"),
            "Отрицательный номер запроса" to config().put("locationRequestId", -1),
            "Строка вместо номера запроса" to config().put("locationRequestId", "3"),
            "Некорректный PIN" to config().put("pin", "abcd"),
            "Число вместо PIN" to config().put("pin", 4826),
            "Короткий PIN" to config().put("pin", "12"),
            "Пустое значение расписания" to config().put("scheduleRules", JSONObject.NULL),
            "Повреждённое правило" to config().put("scheduleRules", JSONArray().put(JSONObject()))
        )
        for ((name, value) in cases) {
            assertThrows(name, Exception::class.java) { parse(value) }
        }
    }

    @Test
    fun `одно повреждённое правило не стирает остальное расписание`() {
        val cases = listOf(
            "enabled" to "false", "start" to "25:00", "end" to "07:99",
            "mode" to "none", "days" to JSONArray(), "days" to JSONArray().put(0),
            "days" to JSONArray().put("1"), "id" to ""
        )
        for ((key, invalid) in cases) {
            val value = config()
            val secondRule = JSONObject(value.getJSONArray("scheduleRules").getJSONObject(0).toString())
                .put(key, invalid)
            value.getJSONArray("scheduleRules").put(secondRule)
            assertThrows("Повреждено поле $key", Exception::class.java) { parse(value) }
        }
    }

    @Test
    fun `старый ответ не откатывает уже применённые ограничения`() {
        assertThrows(Exception::class.java) { parse(config(), "2026-10-18T11:00:00+00:00") }
        assertEquals(RestrictionMode.PARENTAL, parse(config(), "2026-10-18T10:00:00+00:00").restrictionMode)
        assertEquals(RestrictionMode.PARENTAL, parse(config(), "2026-10-18T09:00:00+00:00").restrictionMode)
    }

    @Test
    fun `пустой или повреждённый ответ не считается конфигом`() {
        for (body in listOf("", "null", "[]", "{broken", "<html>Bad Gateway</html>")) {
            assertThrows(Exception::class.java) { RemoteConfigClient.parseConfig(body, "qa-phone") }
        }
    }
}
