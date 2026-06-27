package com.homecage.kiosk.sync

import android.content.Context
import android.provider.Settings
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.data.SecurityEventReport
import com.homecage.kiosk.data.SecurityTrailEntry

class SecurityTrailReporter(context: Context) {
    private val appContext = context.applicationContext
    private val preferences = KioskPreferences(appContext)

    fun reportAsync(
        triggerPackage: String,
        triggerClassName: String,
        reason: String,
        trail: List<SecurityTrailEntry>
    ) {
        val report = SecurityEventReport(
            reportedAtMillis = System.currentTimeMillis(),
            triggerPackage = triggerPackage,
            triggerClassName = triggerClassName,
            reason = reason,
            trail = trail.takeLast(MAX_TRAIL_ENTRIES_PER_REPORT)
        )
        val serverUrl = preferences.getServerUrl()
        if (serverUrl.isBlank()) {
            preferences.enqueueSecurityEvent(report)
            return
        }

        Thread {
            val client = RemoteConfigClient(
                rawServerUrl = serverUrl,
                token = preferences.getServerToken()
            )
            val deviceId = deviceId()
            val deviceName = preferences.getDeviceName()
            runCatching {
                flushPending(client, deviceId, deviceName)
                client.reportSecurityEvent(deviceId, deviceName, report)
            }.onFailure {
                preferences.enqueueSecurityEvent(report)
            }
        }.start()
    }

    fun flushPending(client: RemoteConfigClient, deviceId: String, deviceName: String) {
        val pendingReports = preferences.getPendingSecurityEvents()
        if (pendingReports.isEmpty()) return

        val remainingReports = mutableListOf<SecurityEventReport>()
        for (index in pendingReports.indices) {
            val report = pendingReports[index]
            val result = runCatching {
                client.reportSecurityEvent(deviceId, deviceName, report)
            }
            if (result.isFailure) {
                remainingReports.addAll(pendingReports.drop(index))
                break
            }
        }
        preferences.replacePendingSecurityEvents(remainingReports)
    }

    private fun deviceId(): String =
        Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
            ?: "unknown"

    private companion object {
        const val MAX_TRAIL_ENTRIES_PER_REPORT = 10
    }
}
