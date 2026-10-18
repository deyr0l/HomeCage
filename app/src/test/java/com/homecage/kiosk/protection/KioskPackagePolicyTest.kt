package com.homecage.kiosk.protection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class KioskPackagePolicyTest {
    private val allowedApp = KioskPackagePolicy.WindowState(true, true, true, true)
    private val backgroundApp = allowedApp.copy(isForeground = false)
    private val forbiddenApp = KioskPackagePolicy.WindowState(true, true, false, false)
    private val keyboard = KioskPackagePolicy.WindowState(false, true, true, false)
    private val systemPanel = KioskPackagePolicy.WindowState(false, true, true, false)

    @Test
    fun `видимое запрещённое окно нельзя оправдать разрешённым приложением`() {
        val cases = listOf(
            Triple("Разрешённое приложение", listOf(allowedApp), true),
            Triple("Нет данных об окнах", emptyList(), false),
            Triple("Только старое фоновое окно", listOf(backgroundApp), false),
            Triple("Запрещённое приложение", listOf(forbiddenApp), false),
            Triple("Браузер поверх разрешённого приложения", listOf(backgroundApp, forbiddenApp), false),
            Triple("Запрещённое плавающее окно", listOf(allowedApp, forbiddenApp.copy(isForeground = false)), false),
            Triple("Клавиатура внутри разрешённого приложения", listOf(allowedApp, keyboard), true),
            Triple("Клавиатура над запрещённым браузером", listOf(backgroundApp, forbiddenApp, keyboard), false),
            Triple("Клавиатура без приложения", listOf(keyboard), false),
            Triple("Отдельный экран клавиатуры", listOf(backgroundApp, forbiddenApp), false),
            Triple("Фонарик в системной панели", listOf(backgroundApp, systemPanel), true),
            Triple("Меню выключения над разрешённым приложением", listOf(backgroundApp, systemPanel), true),
            Triple("Системная панель над запрещённым приложением", listOf(forbiddenApp, systemPanel), false),
            Triple("Системная панель без приложения", listOf(systemPanel), false),
            Triple("Неизвестное окно с фокусом", listOf(allowedApp, systemPanel.copy(isAllowed = false)), false),
            Triple("Фоновая служебная панель без фокуса", listOf(allowedApp, systemPanel.copy(isForeground = false, isAllowed = false)), true),
            Triple("HomeCage в фоне не оправдывает настройки", listOf(backgroundApp, forbiddenApp), false)
        )
        for ((name, windows, expected) in cases) {
            assertEquals(name, expected, KioskPackagePolicy.hasAllowedForeground(windows))
        }
    }

    @Test
    fun `допуск клавиатуры относится только к окну ввода`() {
        for (isKeyboard in listOf(false, true)) {
            for (isInput in listOf(false, true)) {
                for (isSystem in listOf(false, true)) {
                    assertEquals(
                        "Клавиатура=$isKeyboard, окно ввода=$isInput, системное окно=$isSystem",
                        if (isKeyboard) isInput else isSystem,
                        KioskPackagePolicy.isSupportWindowAllowed(isKeyboard, isInput, isSystem)
                    )
                }
            }
        }
    }

    @Test
    fun `настройки установщики и магазины не попадают в список киоска`() {
        val packages = setOf(
            "com.android.settings",
            "com.android.packageinstaller",
            "com.google.android.packageinstaller",
            "com.miui.packageinstaller",
            "com.android.vending",
            "com.xiaomi.market",
            "com.xiaomi.mipicks"
        )
        val result = KioskPackagePolicy.lockTaskPackages("com.homecage.kiosk", packages)
        for (pkg in packages) assertFalse("Не должен разрешаться: $pkg", pkg in result)
    }
}
