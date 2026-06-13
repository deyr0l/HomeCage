package com.homecage.kiosk.protection

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.homecage.kiosk.MainActivity
import com.homecage.kiosk.R
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.locale.AppLocaleManager
import kotlin.math.roundToInt

class KioskAccessibilityService : AccessibilityService() {
    private val handler = Handler(Looper.getMainLooper())
    private var overlayView: View? = null
    private var lastBlockedPackage: String? = null
    private var lastHomeReturnAt = 0L

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppLocaleManager.wrap(newBase))
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        if (packageName.isBlank()) return

        val preferences = KioskPreferences(this)
        if (preferences.isAdminSessionUnlocked()) {
            hideOverlay()
            return
        }

        if (isAllowedPackage(packageName, preferences)) {
            hideOverlay()
            return
        }

        blockPackage(packageName)
    }

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        hideOverlay()
        super.onDestroy()
    }

    private fun isAllowedPackage(packageName: String, preferences: KioskPreferences): Boolean {
        if (packageName == this.packageName) return true
        if (preferences.isLockdownEnabled()) {
            return packageName in KioskPackagePolicy.allowedSystemPackages
        }
        if (packageName in KioskPackagePolicy.blockedSystemPackages) return false
        if (packageName in KioskPackagePolicy.allowedSystemPackages) return true
        if (packageName in KioskPackagePolicy.phonePackages) return true
        if (packageName in preferences.getAllowedPackages()) return true
        return false
    }

    private fun blockPackage(packageName: String) {
        val now = SystemClock.elapsedRealtime()
        val shouldRefreshOverlay = packageName != lastBlockedPackage || overlayView == null
        if (shouldRefreshOverlay) {
            lastBlockedPackage = packageName
            showOverlay(packageName)
        }

        if (shouldRefreshOverlay || now - lastHomeReturnAt >= HOME_RETURN_THROTTLE_MS) {
            lastHomeReturnAt = now
            returnHome()
        }
    }

    private fun showOverlay(blockedPackage: String) {
        handler.post {
            runCatching {
                removeOverlayNow()
                val root = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    gravity = Gravity.CENTER
                    setPadding(dp(28), dp(28), dp(28), dp(28))
                    background = GradientDrawable().apply {
                        setColor(Color.rgb(248, 250, 252))
                    }
                }
                val title = TextView(this).apply {
                    text = getString(R.string.accessibility_block_title)
                    textSize = 28f
                    typeface = Typeface.DEFAULT_BOLD
                    gravity = Gravity.CENTER
                    setTextColor(Color.rgb(15, 23, 42))
                }
                val details = TextView(this).apply {
                    text = getString(R.string.accessibility_block_message, blockedPackage)
                    textSize = 16f
                    gravity = Gravity.CENTER
                    setTextColor(Color.rgb(71, 85, 105))
                    setPadding(0, dp(14), 0, dp(18))
                }
                val button = Button(this).apply {
                    text = getString(R.string.accessibility_return)
                    setAllCaps(false)
                    setOnClickListener { returnHome() }
                }

                root.addView(title)
                root.addView(details)
                root.addView(button)

                val params = WindowManager.LayoutParams(
                    WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                    android.graphics.PixelFormat.TRANSLUCENT
                )
                getSystemService(WindowManager::class.java)?.addView(root, params)
                overlayView = root
            }
        }
    }

    private fun hideOverlay() {
        handler.post {
            removeOverlayNow()
            lastBlockedPackage = null
            lastHomeReturnAt = 0L
        }
    }

    private fun removeOverlayNow() {
        overlayView?.let { view ->
            runCatching {
                getSystemService(WindowManager::class.java)?.removeView(view)
            }
        }
        overlayView = null
    }

    private fun returnHome() {
        val intent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        runCatching { startActivity(intent) }
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).roundToInt()

    private companion object {
        const val HOME_RETURN_THROTTLE_MS = 1_000L
    }
}
