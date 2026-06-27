package com.homecage.kiosk.protection

import android.accessibilityservice.AccessibilityService
import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityWindowInfo
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.homecage.kiosk.MainActivity
import com.homecage.kiosk.R
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.data.RestrictionMode
import com.homecage.kiosk.data.SecurityTrailEntry
import com.homecage.kiosk.locale.AppLocaleManager
import com.homecage.kiosk.sync.SecurityTrailReporter
import kotlin.math.roundToInt

class KioskAccessibilityService : AccessibilityService() {
    private val handler = Handler(Looper.getMainLooper())
    private var overlayView: View? = null
    private var lastBlockedPackage: String? = null
    private var lastHomeReturnAt = 0L
    private var watchdogAttempts = 0

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppLocaleManager.wrap(newBase))
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        if (packageName.isBlank()) return
        val className = event.className?.toString().orEmpty()

        val preferences = KioskPreferences(this)
        if (
            preferences.isAdminSessionUnlocked() &&
            KioskPackagePolicy.isAdminSetupPackage(packageName)
        ) {
            rememberTrailEvent(event, packageName, className, preferences, DECISION_ALLOWED_ADMIN_SETUP)
            clearBlock()
            return
        }

        if (packageName == this.packageName) {
            rememberTrailEvent(event, packageName, className, preferences, DECISION_ALLOWED_SELF)
            clearBlock()
            return
        }

        if (KioskPackagePolicy.isBlockedSystemSurface(packageName, className)) {
            val trail = rememberTrailEvent(
                event,
                packageName,
                className,
                preferences,
                DECISION_BLOCKED_SYSTEM_SURFACE
            )
            blockPackage(packageName, className, REASON_BLOCKED_SYSTEM_SURFACE, trail)
            return
        }

        if (packageName in KioskPackagePolicy.blockedSystemPackages) {
            val trail = rememberTrailEvent(
                event,
                packageName,
                className,
                preferences,
                DECISION_BLOCKED_SYSTEM_PACKAGE
            )
            blockPackage(packageName, className, REASON_BLOCKED_SYSTEM_PACKAGE, trail)
            return
        }

        if (isTransientPackage(packageName, preferences)) {
            if (verifyForegroundAllowed(preferences)) {
                rememberTrailEvent(
                    event,
                    packageName,
                    className,
                    preferences,
                    DECISION_ALLOWED_TRANSIENT_WITH_ANCHOR
                )
                if (lastBlockedPackage != null) clearBlock()
                return
            }
            val trail = rememberTrailEvent(
                event,
                packageName,
                className,
                preferences,
                DECISION_BLOCKED_TRANSIENT_WITHOUT_ANCHOR
            )
            blockPackage(packageName, className, REASON_TRANSIENT_WITHOUT_ALLOWED_ANCHOR, trail)
            return
        }

        if (isAllowedPackage(packageName, preferences)) {
            rememberTrailEvent(event, packageName, className, preferences, DECISION_ALLOWED_EXPLICIT)
            if (lastBlockedPackage != null && verifyForegroundAllowed(preferences)) {
                clearBlock()
            }
            return
        }

        val trail = rememberTrailEvent(
            event,
            packageName,
            className,
            preferences,
            DECISION_BLOCKED_NOT_ALLOWED
        )
        blockPackage(packageName, className, REASON_PACKAGE_NOT_EXPLICITLY_ALLOWED, trail)
    }

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        clearBlock()
        super.onDestroy()
    }

    private fun isAllowedPackage(packageName: String, preferences: KioskPreferences): Boolean {
        if (packageName == this.packageName) return true
        return isAllowedForegroundPackage(
            packageName = packageName,
            className = null,
            preferences = preferences
        )
    }

    private fun verifyForegroundAllowed(preferences: KioskPreferences): Boolean {
        val appWindows = try {
            windows?.filter { it.type == AccessibilityWindowInfo.TYPE_APPLICATION }
        } catch (_: Exception) {
            return false
        }

        var hasAllowedAnchor = false
        if (!appWindows.isNullOrEmpty()) {
            for (window in appWindows) {
                val root = try { window.root } catch (_: Exception) { null } ?: continue
                val pkg = root.packageName?.toString()
                val className = root.className?.toString()
                @Suppress("DEPRECATION") root.recycle()

                if (pkg.isNullOrBlank()) continue
                if (window.isFocused || window.isActive) {
                    if (KioskPackagePolicy.isBlockedSystemSurface(pkg, className)) return false
                    if (pkg in KioskPackagePolicy.blockedSystemPackages) return false
                }
                if (
                    isAllowedForegroundPackage(
                        packageName = pkg,
                        className = className,
                        preferences = preferences
                    ) &&
                    !isTransientPackage(pkg, preferences)
                ) {
                    hasAllowedAnchor = true
                }
            }
        }
        if (hasAllowedAnchor) return true

        val usagePackage = usageStatsForegroundPackage() ?: return false
        return isAllowedForegroundPackage(
            packageName = usagePackage,
            className = null,
            preferences = preferences
        ) && !isTransientPackage(usagePackage, preferences)
    }

    private fun isAllowedForegroundPackage(
        packageName: String,
        className: String?,
        preferences: KioskPreferences
    ): Boolean {
        if (packageName == this.packageName) return true
        if (KioskPackagePolicy.isBlockedSystemSurface(packageName, className)) return false
        val restrictionMode = preferences.getEffectiveRestrictionMode()
        if (restrictionMode == RestrictionMode.LOST) {
            return packageName in KioskPackagePolicy.allowedSystemPackages
        }
        if (packageName in KioskPackagePolicy.blockedSystemPackages) return false
        if (packageName in KioskPackagePolicy.allowedSystemPackages) return true
        if (packageName in KioskPackagePolicy.phonePackages) {
            return preferences.isQuickCallSessionActive() ||
                (
                    restrictionMode == RestrictionMode.NONE &&
                        packageName in preferences.getLaunchableAllowedPackages()
                    )
        }
        if (restrictionMode == RestrictionMode.PARENTAL) return false
        if (packageName in preferences.getLaunchableAllowedPackages()) return true
        return false
    }

    private fun isTransientPackage(packageName: String, preferences: KioskPreferences): Boolean =
        packageName in preferences.getManualPackages() ||
            KioskPackagePolicy.isTransientSupportPackage(packageName) ||
            isDefaultInputMethodPackage(packageName)

    private fun isDefaultInputMethodPackage(packageName: String): Boolean {
        val rawInputMethod = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.DEFAULT_INPUT_METHOD
        ).orEmpty()
        val component = ComponentName.unflattenFromString(rawInputMethod)
        return component?.packageName == packageName
    }

    @Suppress("DEPRECATION")
    private fun usageStatsForegroundPackage(): String? {
        if (!hasUsageAccess()) return null
        val usageStatsManager = getSystemService(UsageStatsManager::class.java) ?: return null
        val endTime = System.currentTimeMillis()
        val events = runCatching {
            usageStatsManager.queryEvents(endTime - USAGE_LOOKBACK_MS, endTime)
        }.getOrNull() ?: return null

        val event = UsageEvents.Event()
        var latestPackage: String? = null
        var latestTime = 0L
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            val isForegroundEvent =
                event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND ||
                    (
                        Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
                            event.eventType == UsageEvents.Event.ACTIVITY_RESUMED
                        )
            if (isForegroundEvent && event.timeStamp >= latestTime) {
                latestPackage = event.packageName
                latestTime = event.timeStamp
            }
        }
        return latestPackage
    }

    private fun hasUsageAccess(): Boolean {
        val appOpsManager = getSystemService(AppOpsManager::class.java) ?: return false
        @Suppress("DEPRECATION")
        val mode = appOpsManager.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            applicationInfo.uid,
            packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun overlayWindowType(): Int =
        if (Settings.canDrawOverlays(this)) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY
        }

    private fun rememberTrailEvent(
        event: AccessibilityEvent,
        packageName: String,
        className: String,
        preferences: KioskPreferences,
        decision: String
    ): List<SecurityTrailEntry> =
        preferences.rememberSecurityTrailEntry(
            SecurityTrailEntry(
                atMillis = System.currentTimeMillis(),
                eventType = eventTypeName(event.eventType),
                packageName = packageName.take(MAX_SECURITY_FIELD_LENGTH),
                className = className.take(MAX_SECURITY_FIELD_LENGTH),
                decision = decision,
                restrictionMode = preferences.getEffectiveRestrictionMode().wireValue
            )
        )

    private fun eventTypeName(eventType: Int): String =
        runCatching { AccessibilityEvent.eventTypeToString(eventType) }
            .getOrNull()
            ?.takeIf { it.isNotBlank() }
            ?: eventType.toString()

    private fun blockPackage(
        packageName: String,
        className: String,
        reason: String,
        trail: List<SecurityTrailEntry>
    ) {
        val now = SystemClock.elapsedRealtime()
        val shouldRefreshOverlay = packageName != lastBlockedPackage || overlayView == null
        if (shouldRefreshOverlay) {
            lastBlockedPackage = packageName
            SecurityTrailReporter(this).reportAsync(
                triggerPackage = packageName,
                triggerClassName = className.take(MAX_SECURITY_FIELD_LENGTH),
                reason = reason,
                trail = trail
            )
            showOverlay(packageName)
        }

        if (shouldRefreshOverlay || now - lastHomeReturnAt >= HOME_RETURN_THROTTLE_MS) {
            lastHomeReturnAt = now
            returnHome()
        }

        handler.removeCallbacks(watchdogRunnable)
        watchdogAttempts = 0
        handler.postDelayed(watchdogRunnable, WATCHDOG_INTERVAL_MS)
    }

    private val watchdogRunnable = object : Runnable {
        override fun run() {
            if (lastBlockedPackage == null) return
            if (++watchdogAttempts > MAX_WATCHDOG_ATTEMPTS) return
            if (verifyForegroundAllowed(KioskPreferences(this@KioskAccessibilityService))) {
                clearBlock()
                return
            }
            returnHome()
            handler.postDelayed(this, WATCHDOG_INTERVAL_MS)
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
                    overlayWindowType(),
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                    android.graphics.PixelFormat.TRANSLUCENT
                )
                getSystemService(WindowManager::class.java)?.addView(root, params)
                overlayView = root
            }
        }
    }

    private fun clearBlock() {
        handler.removeCallbacks(watchdogRunnable)
        watchdogAttempts = 0
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
        const val WATCHDOG_INTERVAL_MS = 500L
        const val MAX_WATCHDOG_ATTEMPTS = 5
        const val USAGE_LOOKBACK_MS = 30_000L
        const val MAX_SECURITY_FIELD_LENGTH = 180
        const val DECISION_ALLOWED_ADMIN_SETUP = "allowed_admin_setup"
        const val DECISION_ALLOWED_SELF = "allowed_self"
        const val DECISION_ALLOWED_EXPLICIT = "allowed_explicit"
        const val DECISION_ALLOWED_TRANSIENT_WITH_ANCHOR = "allowed_transient_with_anchor"
        const val DECISION_BLOCKED_SYSTEM_SURFACE = "blocked_system_surface"
        const val DECISION_BLOCKED_SYSTEM_PACKAGE = "blocked_system_package"
        const val DECISION_BLOCKED_TRANSIENT_WITHOUT_ANCHOR = "blocked_transient_without_anchor"
        const val DECISION_BLOCKED_NOT_ALLOWED = "blocked_not_explicitly_allowed"
        const val REASON_BLOCKED_SYSTEM_SURFACE = "blocked_system_surface"
        const val REASON_BLOCKED_SYSTEM_PACKAGE = "blocked_system_package"
        const val REASON_TRANSIENT_WITHOUT_ALLOWED_ANCHOR = "transient_without_allowed_anchor"
        const val REASON_PACKAGE_NOT_EXPLICITLY_ALLOWED = "package_not_explicitly_allowed"
    }
}
