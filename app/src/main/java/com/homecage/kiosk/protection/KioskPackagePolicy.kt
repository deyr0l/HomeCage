package com.homecage.kiosk.protection

object KioskPackagePolicy {
    val allowedSystemPackages: Set<String> = setOf(
        "android",
        "com.android.systemui",
        "com.miui.systemui",
        "com.android.permissioncontroller",
        "com.google.android.permissioncontroller",
        "com.lbe.security.miui",
        "com.google.android.gms"
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

    val blockedSystemPackages: Set<String> = setOf(
        "com.android.settings",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.miui.packageinstaller",
        "com.miui.securitycenter",
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
}
