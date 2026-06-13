package com.homecage.kiosk.sync

data class ConfigSyncResult(
    val success: Boolean,
    val message: String,
    val appliedPackages: Int = 0
)
