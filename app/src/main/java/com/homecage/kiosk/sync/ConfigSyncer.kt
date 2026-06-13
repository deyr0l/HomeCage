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

    fun shouldSyncNow(nowMillis: Long = System.currentTimeMillis()): Boolean {
        val serverUrl = preferences.getServerUrl()
        if (serverUrl.isBlank()) return false
        return nowMillis - preferences.getLastSyncAttemptAt() >= MIN_SYNC_INTERVAL_MS
    }

    fun sync(): ConfigSyncResult {
        val now = System.currentTimeMillis()
        preferences.markSyncAttempt(now)

        return runCatching {
            val appRepository = AppRepository(appContext)
            val installedApps = appRepository.getLaunchableApps()
            val client = RemoteConfigClient(
                rawServerUrl = preferences.getServerUrl(),
                token = preferences.getServerToken()
            )

            client.reportDeviceState(
                deviceId = deviceId(),
                installedApps = installedApps,
                localAllowedPackages = preferences.getAllowedPackages()
            )
            val remoteConfig = client.fetchConfig()
            preferences.setAllowedPackages(remoteConfig.allowedPackages)
            remoteConfig.pin?.let { preferences.setPin(it) }
            KioskPolicyManager(appContext).applyDeviceOwnerPolicies(remoteConfig.allowedPackages)

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

    companion object {
        const val MIN_SYNC_INTERVAL_MS = 15 * 60 * 1000L
    }
}
