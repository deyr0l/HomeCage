package com.homecage.kiosk.protection

object KioskPackagePolicy {
    val allowedSystemPackages: Set<String> = setOf(
        "android",
        "com.android.systemui",
        "com.miui.systemui"
    )

    val adminSetupPackages: Set<String> = setOf(
        "com.android.settings",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.android.permissioncontroller",
        "com.google.android.permissioncontroller",
        "com.google.android.gms",
        "com.lbe.security.miui",
        "com.miui.packageinstaller",
        "com.miui.securitycenter"
    )

    val phonePackages: Set<String> = setOf(
        "com.android.dialer",
        "com.google.android.dialer",
        "com.android.incallui",
        "com.android.phone",
        "com.android.server.telecom",
        "com.android.contacts",
        "com.google.android.contacts",
        "com.miui.contacts",
        "com.samsung.android.contacts",
        "com.oppo.contacts",
        "com.coloros.contacts",
        "com.miui.voip",
        "com.miui.phone"
    )

    val keyboardPackages: Set<String> = setOf(
        "com.android.inputmethod.latin",
        "com.google.android.inputmethod.latin",
        "com.microsoft.swiftkey",
        "com.touchtype.swiftkey",
        "com.samsung.android.honeyboard",
        "com.baidu.input_mi",
        "com.sohu.inputmethod.sogou.xiaomi"
    )

    val transientSupportPackages: Set<String> = setOf(
        "com.google.android.ext.services",
        "miui.system.plugin"
    ) + keyboardPackages

    val blockedSystemPackages: Set<String> = setOf(
        "com.android.settings",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.miui.packageinstaller",
        "com.miui.securitycenter",
        "com.lbe.security.miui",
        "com.mi.android.globalpersonalassistant",
        "com.miui.cleanmaster",
        "com.miui.freeform",
        "com.miui.gamebooster",
        "com.miui.guardprovider",
        "com.miui.hybrid",
        "com.miui.hybrid.accessory",
        "com.miui.personalassistant",
        "com.miui.powerkeeper",
        "com.miui.securitycore",
        "com.miui.securityadd",
        "com.miui.touchassistant",
        "com.miui.video",
        "com.miui.videoplayer",
        "com.android.vending",
        "com.xiaomi.market",
        "com.xiaomi.mipicks",
        "com.xiaomi.scanner",
        "com.miui.home",
        "com.mi.android.globallauncher",
        "com.android.launcher3",
        "com.google.android.apps.nexuslauncher",
        "com.google.android.apps.nexuslauncher.search",
        "com.sec.android.app.launcher",
        "com.oppo.launcher",
        "com.coloros.launcher",
        "com.huawei.android.launcher"
    )

    fun lockTaskPackages(
        homeCagePackage: String,
        launchablePackages: Set<String>
    ): Set<String> =
        (launchablePackages - blockedSystemPackages) +
            homeCagePackage +
            phonePackages +
            allowedSystemPackages

    private val blockedClassNameFragments: Set<String> = setOf(
        "AccessibilitySettings",
        "ApplicationDetails",
        "AppInfo",
        "DefaultHome",
        "DeviceAdmin",
        "Freeform",
        "Floating",
        "GameBooster",
        "InstalledAppDetails",
        "ManageApplications",
        "PackageInstaller",
        "PermCenter",
        "PermissionsEditor",
        "PowerSettings",
        "ResolverActivity",
        "SecondSpace",
        "SecurityCenter",
        "Uninstaller"
    )

    private val riskySystemHosts: Set<String> =
        allowedSystemPackages + adminSetupPackages + blockedSystemPackages + setOf(
            "miui.system.plugin",
            "com.google.android.gms",
            "com.google.android.ext.services"
        )

    fun isBlockedSystemSurface(packageName: String, className: String?): Boolean {
        if (packageName !in riskySystemHosts) return false
        val normalizedClassName = className.orEmpty()
        if (normalizedClassName.isBlank()) return false
        return blockedClassNameFragments.any { fragment ->
            normalizedClassName.contains(fragment, ignoreCase = true)
        }
    }

    fun isAdminSetupPackage(packageName: String): Boolean =
        packageName in adminSetupPackages || packageName in allowedSystemPackages

    fun isKeyboardPackage(packageName: String): Boolean =
        packageName in keyboardPackages

    fun isTransientSupportPackage(packageName: String): Boolean =
        packageName in transientSupportPackages
}
