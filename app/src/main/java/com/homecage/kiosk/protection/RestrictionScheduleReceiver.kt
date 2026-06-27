package com.homecage.kiosk.protection

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import com.homecage.kiosk.MainActivity
import com.homecage.kiosk.admin.KioskPolicyManager
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.data.RestrictionScheduleRule

class RestrictionScheduleReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_SCHEDULE_CHANGED) return

        val appContext = context.applicationContext
        val preferences = KioskPreferences(appContext)
        val effectiveMode = preferences.getEffectiveRestrictionMode()
        KioskPolicyManager(appContext).applyDeviceOwnerPolicies(
            allowedPackages = preferences.getAllowedPackages(),
            restrictionMode = effectiveMode
        )
        scheduleNext(appContext)

        if (effectiveMode.blocksAppLaunches) {
            val homeIntent = Intent(appContext, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
                addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            runCatching { appContext.startActivity(homeIntent) }
        }
    }

    companion object {
        private const val ACTION_SCHEDULE_CHANGED = "com.homecage.kiosk.action.RESTRICTION_SCHEDULE_CHANGED"
        private const val REQUEST_CODE = 9201

        fun scheduleNext(context: Context) {
            val appContext = context.applicationContext
            val alarmManager = appContext.getSystemService(AlarmManager::class.java) ?: return
            val pendingIntent = pendingIntent(appContext)
            val nextChangeAt = RestrictionScheduleRule.nextChangeAfter(
                KioskPreferences(appContext).getScheduleRules()
            )

            if (nextChangeAt == null) {
                alarmManager.cancel(pendingIntent)
                return
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    nextChangeAt,
                    pendingIntent
                )
            } else {
                alarmManager.set(
                    AlarmManager.RTC_WAKEUP,
                    nextChangeAt,
                    pendingIntent
                )
            }
        }

        private fun pendingIntent(context: Context): PendingIntent {
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0
            return PendingIntent.getBroadcast(
                context,
                REQUEST_CODE,
                Intent(context, RestrictionScheduleReceiver::class.java).apply {
                    action = ACTION_SCHEDULE_CHANGED
                },
                flags
            )
        }
    }
}
