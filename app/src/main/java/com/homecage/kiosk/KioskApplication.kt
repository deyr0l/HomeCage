package com.homecage.kiosk

import android.app.Application
import android.content.Context
import com.homecage.kiosk.locale.AppLocaleManager
import com.homecage.kiosk.protection.RestrictionScheduleReceiver

class KioskApplication : Application() {
    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(AppLocaleManager.wrap(base))
    }

    override fun onCreate() {
        super.onCreate()
        RestrictionScheduleReceiver.scheduleNext(this)
    }
}
