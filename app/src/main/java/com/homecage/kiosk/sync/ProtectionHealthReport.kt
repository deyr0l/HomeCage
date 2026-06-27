package com.homecage.kiosk.sync

data class ProtectionHealthReport(
    val deviceOwnerEnabled: Boolean,
    val deviceAdminEnabled: Boolean,
    val accessibilityEnabled: Boolean,
    val overlayEnabled: Boolean,
    val usageAccessEnabled: Boolean,
    val callPermissionGranted: Boolean,
    val locationPermissionGranted: Boolean,
    val flashlightPermissionGranted: Boolean
)
