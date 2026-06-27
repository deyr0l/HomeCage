package com.homecage.kiosk.sync

import android.Manifest
import android.app.AppOpsManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.provider.Settings
import com.homecage.kiosk.R
import com.homecage.kiosk.admin.KioskPolicyManager
import com.homecage.kiosk.data.AppRepository
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.locale.AppLocaleManager
import com.homecage.kiosk.protection.KioskAccessibilityService
import com.homecage.kiosk.protection.RestrictionScheduleReceiver

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

    fun sync(force: Boolean = false): ConfigSyncResult =
        synchronized(SYNC_LOCK) {
            syncLocked(force)
        }

    private fun syncLocked(force: Boolean = false): ConfigSyncResult {
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

            SecurityTrailReporter(appContext).flushPending(client, deviceId, deviceName)

            client.reportDeviceState(
                deviceId = deviceId,
                deviceName = deviceName,
                installedApps = installedApps,
                localAllowedPackages = localAllowedPackagesBeforeSync,
                restrictionMode = preferences.getEffectiveRestrictionMode(),
                location = null,
                appliedConfigUpdatedAt = preferences.getLastAppliedRemoteConfigUpdatedAt(),
                configApplyStatus = preferences.getLastRemoteConfigApplyStatus(),
                protectionHealth = protectionHealth()
            )

            val remoteConfig = client.fetchConfig(deviceId, deviceName)

            val launchableNames = installedApps.map { it.packageName }.toSet()
            val manualPackages = remoteConfig.allowedPackages.filter { it !in launchableNames }.toSet()

            val canApplyAllowedPackages =
                (force || !preferences.isAdminSessionUnlocked()) &&
                    preferences.updatePolicyIfRevisionUnchanged(
                        expectedRevision = revisionBeforeSync,
                        allowedPackages = remoteConfig.allowedPackages,
                        manualPackages = manualPackages
                    )
            val applyStatus = if (canApplyAllowedPackages) {
                CONFIG_APPLY_STATUS_APPLIED
            } else {
                CONFIG_APPLY_STATUS_SKIPPED_LOCAL_CHANGE
            }

            preferences.setRestrictionMode(remoteConfig.restrictionMode)
            preferences.setScheduleRules(remoteConfig.scheduleRules)
            preferences.markRemoteConfigApplyResult(remoteConfig.updatedAt, applyStatus)
            remoteConfig.pin?.let { preferences.setPin(it) }
            RestrictionScheduleReceiver.scheduleNext(appContext)
            KioskPolicyManager(appContext).applyDeviceOwnerPolicies(
                allowedPackages = preferences.getAllowedPackages(),
                restrictionMode = preferences.getEffectiveRestrictionMode()
            )

            val locationReport = locationReportFor(remoteConfig.locationRequestId)
            client.reportDeviceState(
                deviceId = deviceId,
                deviceName = deviceName,
                installedApps = installedApps,
                localAllowedPackages = preferences.getAllowedPackages(),
                restrictionMode = preferences.getEffectiveRestrictionMode(),
                location = locationReport,
                appliedConfigUpdatedAt = remoteConfig.updatedAt,
                configApplyStatus = applyStatus,
                protectionHealth = protectionHealth()
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

    private fun protectionHealth(): ProtectionHealthReport {
        val policyManager = KioskPolicyManager(appContext)
        return ProtectionHealthReport(
            deviceOwnerEnabled = policyManager.isDeviceOwner(),
            deviceAdminEnabled = policyManager.isDeviceAdminActive(),
            accessibilityEnabled = isAccessibilityProtectionEnabled(),
            overlayEnabled = Settings.canDrawOverlays(appContext),
            usageAccessEnabled = hasUsageAccess(),
            callPermissionGranted = hasPermission(Manifest.permission.CALL_PHONE),
            locationPermissionGranted =
                hasPermission(Manifest.permission.ACCESS_FINE_LOCATION) ||
                    hasPermission(Manifest.permission.ACCESS_COARSE_LOCATION),
            flashlightPermissionGranted = hasPermission(Manifest.permission.CAMERA)
        )
    }

    private fun hasPermission(permission: String): Boolean =
        appContext.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED

    private fun isAccessibilityProtectionEnabled(): Boolean {
        val enabledServices = Settings.Secure.getString(
            appContext.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ).orEmpty()
        val expected = ComponentName(appContext, KioskAccessibilityService::class.java)
        return enabledServices.split(':').any { rawComponent ->
            val component = ComponentName.unflattenFromString(rawComponent)
            component?.packageName == expected.packageName &&
                component.className == expected.className
        }
    }

    private fun hasUsageAccess(): Boolean {
        val appOpsManager = appContext.getSystemService(AppOpsManager::class.java) ?: return false
        @Suppress("DEPRECATION")
        val mode = appOpsManager.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            appContext.applicationInfo.uid,
            appContext.packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    companion object {
        const val MIN_SYNC_INTERVAL_MS = 10 * 60 * 1000L
        const val CONFIG_APPLY_STATUS_APPLIED = "applied"
        const val CONFIG_APPLY_STATUS_SKIPPED_LOCAL_CHANGE = "skipped_local_change"
        val SYNC_LOCK = Any()
    }
}
