package com.homecage.kiosk.sync

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.os.Build

object ConfigSyncScheduler {
    private const val JOB_ID = 7301
    private const val SYNC_INTERVAL_MS = 15 * 60 * 1000L
    private const val SYNC_FLEX_MS = 5 * 60 * 1000L

    fun schedule(context: Context) {
        val appContext = context.applicationContext
        val scheduler = appContext.getSystemService(JobScheduler::class.java) ?: return
        val component = ComponentName(appContext, ConfigSyncJobService::class.java)
        val builder = JobInfo.Builder(JOB_ID, component)
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPersisted(true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            builder.setPeriodic(SYNC_INTERVAL_MS, SYNC_FLEX_MS)
        } else {
            @Suppress("DEPRECATION")
            builder.setPeriodic(SYNC_INTERVAL_MS)
        }
        runCatching {
            scheduler.schedule(builder.build())
        }
    }
}
