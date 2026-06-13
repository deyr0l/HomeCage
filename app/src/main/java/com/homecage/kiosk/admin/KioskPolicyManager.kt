package com.homecage.kiosk.admin

import android.app.Activity
import android.app.ActivityManager
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.widget.Toast
import com.homecage.kiosk.R
import com.homecage.kiosk.protection.KioskPackagePolicy

class KioskPolicyManager(private val context: Context) {
    private val devicePolicyManager =
        context.getSystemService(DevicePolicyManager::class.java)
            ?: error("DevicePolicyManager is not available")
    private val activityManager =
        context.getSystemService(ActivityManager::class.java)
            ?: error("ActivityManager is not available")
    private val adminComponent =
        ComponentName(context, KioskDeviceAdminReceiver::class.java)

    fun isDeviceOwner(): Boolean =
        devicePolicyManager.isDeviceOwnerApp(context.packageName)

    fun isDeviceAdminActive(): Boolean =
        devicePolicyManager.isAdminActive(adminComponent)

    fun deviceAdminActivationIntent(): Intent =
        Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
            putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, adminComponent)
            putExtra(
                DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                context.getString(R.string.device_admin_explanation)
            )
        }

    fun setupCommand(): String =
        "adb shell dpm set-device-owner ${adminComponent.flattenToShortString()}"

    fun setHomeCommand(): String =
        "adb shell cmd package set-home-activity ${ComponentName(context, com.homecage.kiosk.MainActivity::class.java).flattenToShortString()}"

    fun applyDeviceOwnerPolicies(allowedPackages: Set<String>, lockdownEnabled: Boolean = false) {
        if (!isDeviceOwner()) return

        setHomeCageAsPersistentHome()

        val lockTaskPackages = if (lockdownEnabled) {
            (setOf(context.packageName) + KioskPackagePolicy.allowedSystemPackages).toTypedArray()
        } else {
            (
                allowedPackages +
                    context.packageName +
                    KioskPackagePolicy.phonePackages +
                    KioskPackagePolicy.allowedSystemPackages
                ).toTypedArray()
        }
        runCatching {
            devicePolicyManager.setLockTaskPackages(adminComponent, lockTaskPackages)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            runCatching {
                devicePolicyManager.setLockTaskFeatures(
                    adminComponent,
                    DevicePolicyManager.LOCK_TASK_FEATURE_NONE
                )
            }
        }
        runCatching {
            devicePolicyManager.setStatusBarDisabled(adminComponent, true)
        }
        runCatching {
            devicePolicyManager.setKeyguardDisabled(adminComponent, true)
        }
    }

    fun startLockTaskIfReady(activity: Activity) {
        if (!isDeviceOwner()) return
        if (!devicePolicyManager.isLockTaskPermitted(context.packageName)) return
        if (activityManager.lockTaskModeState != ActivityManager.LOCK_TASK_MODE_NONE) return

        runCatching {
            activity.startLockTask()
        }.onFailure {
            Toast.makeText(activity, R.string.toast_kiosk_enable_failed, Toast.LENGTH_SHORT).show()
        }
    }

    fun pauseKioskForAdmin(activity: Activity) {
        if (isDeviceOwner()) {
            runCatching { devicePolicyManager.setStatusBarDisabled(adminComponent, false) }
            runCatching { devicePolicyManager.setKeyguardDisabled(adminComponent, false) }
        }
        runCatching { activity.stopLockTask() }
    }

    fun clearDeviceOwnerForRemoval(activity: Activity): Boolean {
        pauseKioskForAdmin(activity)
        if (!isDeviceOwner()) {
            if (isDeviceAdminActive()) {
                runCatching { devicePolicyManager.removeActiveAdmin(adminComponent) }
            }
            return !isDeviceAdminActive()
        }

        runCatching { devicePolicyManager.setLockTaskPackages(adminComponent, emptyArray<String>()) }
        clearPersistentHome()
        if (isDeviceAdminActive()) {
            runCatching { devicePolicyManager.removeActiveAdmin(adminComponent) }
        }
        return runCatching {
            @Suppress("DEPRECATION")
            devicePolicyManager.clearDeviceOwnerApp(context.packageName)
        }.onFailure {
            Toast.makeText(activity, R.string.toast_clear_device_owner_failed, Toast.LENGTH_LONG).show()
        }.isSuccess
    }

    private fun setHomeCageAsPersistentHome() {
        val homeFilter = IntentFilter(Intent.ACTION_MAIN).apply {
            addCategory(Intent.CATEGORY_HOME)
            addCategory(Intent.CATEGORY_DEFAULT)
        }
        val homeComponent = ComponentName(context, com.homecage.kiosk.MainActivity::class.java)

        runCatching {
            devicePolicyManager.addPersistentPreferredActivity(
                adminComponent,
                homeFilter,
                homeComponent
            )
        }
    }

    private fun clearPersistentHome() {
        runCatching {
            devicePolicyManager.clearPackagePersistentPreferredActivities(
                adminComponent,
                context.packageName
            )
        }
    }
}
