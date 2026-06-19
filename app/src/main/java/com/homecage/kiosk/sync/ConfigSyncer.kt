package com.homecage.kiosk.sync

import android.content.Context
import android.provider.Settings
import com.homecage.kiosk.R
import com.homecage.kiosk.admin.KioskPolicyManager
import com.homecage.kiosk.data.AppRepository
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.locale.AppLocaleManager

class ConfigSyncer(private val context: Context) {
    private val appContext = context.applicationContext
    private val localizedContext = AppLocaleManager.wrap(appContext)
    private val preferences = KioskPreferences(appContext)

    fun shouldSyncNow(nowMillis: Long = System.currentTimeMillis(), force: Boolean = false): Boolean {
        val serverUrl = preferences.getServerUrl()
        if (serverUrl.isBlank()) return false
        if (force) return true
        return nowMillis - preferences.getLastSyncAttemptAt() >= MIN_SYNC_INTERVAL_MS
    }

    fun sync(force: Boolean = false): ConfigSyncResult {
        val now = System.currentTimeMillis()
        preferences.markSyncAttempt(now)

        if (!force && preferences.isAdminSessionUnlocked()) {
            return ConfigSyncResult(success = true, message = "")
        }

        val revisionBeforeSync = preferences.getPolicyRevision()

        return runCatching {
            val appRepository = AppRepository(appContext)
            val installedApps = appRepository.getLaunchableApps()
            val client = RemoteConfigClient(
                rawServerUrl = preferences.getServerUrl(),
                token = preferences.getServerToken()
            )
            val deviceId = deviceId()
            val deviceName = preferences.getDeviceName()
            val localAllowedPackagesBeforeSync = preferences.getAllowedPackages()

            client.reportDeviceState(
                deviceId = deviceId,
                deviceName = deviceName,
                installedApps = installedApps,
                localAllowedPackages = localAllowedPackagesBeforeSync,
                lockdownEnabled = preferences.isLockdownEnabled(),
                location = null
            )

            val remoteConfig = client.fetchConfig(deviceId, deviceName)

            if (!force && (preferences.isAdminSessionUnlocked() ||
                    preferences.getPolicyRevision() != revisionBeforeSync)) {
                return@runCatching ConfigSyncResult(success = true, message = "")
            }

            val launchableNames = installedApps.map { it.packageName }.toSet()
            val manualPackages = remoteConfig.allowedPackages.filter { it !in launchableNames }.toSet()
            preferences.updatePolicy(remoteConfig.allowedPackages, manualPackages)
            preferences.setLockdownEnabled(remoteConfig.lockdownEnabled)
            remoteConfig.pin?.let { preferences.setPin(it) }
            KioskPolicyManager(appContext).applyDeviceOwnerPolicies(
                allowedPackages = remoteConfig.allowedPackages,
                lockdownEnabled = remoteConfig.lockdownEnabled
            )

            val locationReport = locationReportFor(remoteConfig.locationRequestId)
            client.reportDeviceState(
                deviceId = deviceId,
                deviceName = deviceName,
                installedApps = installedApps,
                localAllowedPackages = preferences.getAllowedPackages(),
                lockdownEnabled = preferences.isLockdownEnabled(),
                location = locationReport
            )
            if (locationReport != null) {
                preferences.setHandledLocationRequestId(locationReport.requestId)
            }

            val message = localizedContext.getString(
                R.string.sync_success_message,
                remoteConfig.allowedPackages.size
            )
            preferences.markSyncSuccess(System.currentTimeMillis(), message)
            ConfigSyncResult(
                success = true,
                message = message,
                appliedPackages = remoteConfig.allowedPackages.size
            )
        }.getOrElse { error ->
            val message = error.message ?: localizedContext.getString(R.string.sync_error_default)
            preferences.markSyncFailure(message)
            ConfigSyncResult(success = false, message = message)
        }
    }

    private fun deviceId(): String =
        Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
            ?: "unknown"

    private fun locationReportFor(locationRequestId: Long): DeviceLocationReport? {
        if (locationRequestId <= 0L) return null
        if (locationRequestId <= preferences.getHandledLocationRequestId()) return null
        return DeviceLocationProvider(appContext).reportForRequest(locationRequestId)
    }

    companion object {
        const val MIN_SYNC_INTERVAL_MS = 10 * 60 * 1000L
    }
}
