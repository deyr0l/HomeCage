package com.homecage.kiosk.sync

import android.app.job.JobParameters
import android.app.job.JobService

class ConfigSyncJobService : JobService() {
    @Volatile
    private var worker: Thread? = null

    override fun onStartJob(params: JobParameters): Boolean {
        worker = Thread {
            ConfigSyncer(applicationContext).sync()
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
