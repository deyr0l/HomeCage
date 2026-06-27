package com.homecage.kiosk.sync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.homecage.kiosk.protection.RestrictionScheduleReceiver

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            ConfigSyncScheduler.schedule(context)
            RestrictionScheduleReceiver.scheduleNext(context)
        }
    }
}
