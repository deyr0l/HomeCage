package com.homecage.kiosk.sync

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context

object ConfigSyncScheduler {
    private const val JOB_ID = 7301
    private const val SYNC_INTERVAL_MS = 10 * 60 * 1000L
    private const val SYNC_DEADLINE_MS = 15 * 60 * 1000L

    fun schedule(context: Context) {
        val appContext = context.applicationContext
        val scheduler = appContext.getSystemService(JobScheduler::class.java) ?: return
        val component = ComponentName(appContext, ConfigSyncJobService::class.java)
        val builder = JobInfo.Builder(JOB_ID, component)
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPersisted(true)

        builder
            .setMinimumLatency(SYNC_INTERVAL_MS)
            .setOverrideDeadline(SYNC_DEADLINE_MS)

        runCatching {
            scheduler.schedule(builder.build())
        }
    }
}
