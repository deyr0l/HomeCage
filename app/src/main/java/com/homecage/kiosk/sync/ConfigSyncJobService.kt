package com.homecage.kiosk.sync

import android.app.job.JobParameters
import android.app.job.JobService

class ConfigSyncJobService : JobService() {
    @Volatile
    private var worker: Thread? = null

    override fun onStartJob(params: JobParameters): Boolean {
        worker = Thread {
            val syncer = ConfigSyncer(applicationContext)
            if (syncer.shouldSyncNow()) {
                syncer.sync()
            }
            ConfigSyncScheduler.schedule(applicationContext)
            jobFinished(params, false)
        }.also { it.start() }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        worker?.interrupt()
        worker = null
        return true
    }
}
