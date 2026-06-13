package com.homecage.kiosk

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.text.Editable
import android.text.InputType
import android.text.TextUtils
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import com.homecage.kiosk.admin.KioskPolicyManager
import com.homecage.kiosk.data.AppRepository
import com.homecage.kiosk.data.KioskPreferences
import com.homecage.kiosk.data.LaunchableApp
import com.homecage.kiosk.data.QuickCallContact
import com.homecage.kiosk.locale.AppLocaleManager
import com.homecage.kiosk.protection.KioskAccessibilityService
import com.homecage.kiosk.sync.ConfigSyncScheduler
import com.homecage.kiosk.sync.ConfigSyncer
import com.homecage.kiosk.ui.HomeCageColors
import java.text.DateFormat
import java.util.Date
import kotlin.math.roundToInt

class MainActivity : Activity() {
    private lateinit var preferences: KioskPreferences
    private lateinit var appRepository: AppRepository
    private lateinit var policyManager: KioskPolicyManager
    private var launchableApps: List<LaunchableApp> = emptyList()
    private var currentScreen = Screen.LAUNCHER
    private var syncInFlight = false
    private var pinWorkInFlight = false

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppLocaleManager.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = KioskPreferences(this)
        appRepository = AppRepository(this)
        policyManager = KioskPolicyManager(this)
        refreshApps()
        policyManager.applyDeviceOwnerPolicies(preferences.getAllowedPackages())
        ConfigSyncScheduler.schedule(this)
        showLauncherScreen()
        maybeSyncRemoteConfig()
    }

    override fun onResume() {
        super.onResume()
        enterImmersiveMode()
        if (::policyManager.isInitialized) {
            refreshApps()
            policyManager.applyDeviceOwnerPolicies(preferences.getAllowedPackages())
            policyManager.startLockTaskIfReady(this)
            maybeSyncRemoteConfig()
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enterImmersiveMode()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (currentScreen == Screen.ADMIN) {
            showLauncherScreen()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_CALL_PHONE) return

        val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
        if (granted) {
            Toast.makeText(this, R.string.toast_call_permission_enabled, Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, R.string.toast_call_permission_missing, Toast.LENGTH_LONG).show()
        }
    }

    private fun showLauncherScreen() {
        currentScreen = Screen.LAUNCHER
        preferences.clearAdminSession()
        refreshApps()

        val allowedPackages = preferences.getAllowedPackages()
        val allowedApps = launchableApps.filter { it.packageName in allowedPackages }
        val quickCallContacts = preferences.getQuickCallContacts()
        val root = homeRoot()

        root.addView(kioskHeader(onAdminClick = { showAdminPinDialog() }))

        val scrollView = ScrollView(this).apply {
            setBackgroundColor(HomeCageColors.Background)
            clipToPadding = false
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(2), dp(18), dp(28))
        }
        scrollView.addView(content)
        root.addView(scrollView, weightParams())

        content.addView(statusStrip(allowedApps.size, quickCallContacts.size))

        content.addView(homeSectionTitle(getString(R.string.home_section_quick_call)))
        if (quickCallContacts.isEmpty()) {
            content.addView(emptyStateCard(getString(R.string.home_no_quick_contacts)))
        } else {
            quickCallContacts.forEach { contact ->
                content.addView(quickCallCard(contact))
            }
        }

        content.addView(homeSectionTitle(getString(R.string.home_section_allowed_apps)))
        if (allowedApps.isEmpty()) {
            content.addView(emptyStateCard(getString(R.string.home_no_allowed_apps)))
        } else {
            allowedApps.forEach { app ->
                content.addView(allowedAppCard(app))
            }
        }

        setContentView(root)
        enterImmersiveMode()
        policyManager.applyDeviceOwnerPolicies(allowedPackages)
        policyManager.startLockTaskIfReady(this)
    }

    private fun showAdminPinDialog() {
        val input = pinInput(getString(R.string.pin_label))
        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.admin_pin_title)
            .setView(paddedDialogView(input))
            .setNegativeButton(R.string.action_cancel, null)
            .setPositiveButton(R.string.action_open, null)
            .create()

        dialog.setCanceledOnTouchOutside(false)
        dialog.setOnShowListener {
            val openButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            openButton.isEnabled = false
            input.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                    openButton.isEnabled = (s?.length ?: 0) in 4..12
                }
                override fun afterTextChanged(s: Editable?) = Unit
            })
            openButton.setOnClickListener {
                val pin = input.text.toString()
                openButton.isEnabled = false
                input.isEnabled = false
                verifyAdminPinInBackground(pin) { isValid, errorMessage ->
                    if (!dialog.isShowing) return@verifyAdminPinInBackground
                    input.isEnabled = true
                    openButton.isEnabled = input.text.length in 4..12
                    when {
                        errorMessage != null ->
                            Toast.makeText(this, errorMessage, Toast.LENGTH_LONG).show()
                        isValid -> {
                            dialog.dismiss()
                            showAdminScreen()
                        }
                        else -> input.error = getString(R.string.error_wrong_pin)
                    }
                }
            }
            enterImmersiveMode()
            policyManager.startLockTaskIfReady(this)
        }
        dialog.setOnDismissListener {
            enterImmersiveMode()
            policyManager.startLockTaskIfReady(this)
        }
        dialog.show()
    }

    private fun showAdminScreen() {
        currentScreen = Screen.ADMIN
        preferences.markAdminSessionUnlocked()
        refreshApps()

        val selectedPackages = preferences.getAllowedPackages().toMutableSet()
        val root = verticalRoot()
        root.addView(
            adminHeader(
                onBack = { showLauncherScreen() },
                onSave = {
                    preferences.setAllowedPackages(selectedPackages)
                    policyManager.applyDeviceOwnerPolicies(selectedPackages)
                    Toast.makeText(this, R.string.toast_allowed_list_saved, Toast.LENGTH_SHORT).show()
                    showLauncherScreen()
                }
            )
        )

        val scrollView = ScrollView(this)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(8), dp(16), dp(28))
        }
        scrollView.addView(content)
        root.addView(scrollView, weightParams())

        content.addView(policyStatusSection())
        content.addView(languageSection())
        content.addView(fallbackProtectionSection())
        content.addView(pinSection())
        content.addView(serverSection())
        content.addView(quickCallsSection())
        content.addView(sectionTitle(getString(R.string.section_allowed_apps)))

        if (launchableApps.isEmpty()) {
            content.addView(infoText(getString(R.string.empty_no_launchable_apps)))
        } else {
            launchableApps.forEach { app ->
                content.addView(appCheckRow(app, selectedPackages))
            }
        }

        content.addView(adminActionButton(getString(R.string.button_pause_kiosk_admin)) {
            policyManager.pauseKioskForAdmin(this)
            Toast.makeText(this, R.string.toast_kiosk_paused, Toast.LENGTH_LONG).show()
        })
        content.addView(adminActionButton(getString(R.string.button_disable_protection_remove)) {
            confirmRemoval()
        })

        setContentView(root)
        enterImmersiveMode()
    }

    private fun confirmRemoval() {
        AlertDialog.Builder(this)
            .setTitle(R.string.dialog_disable_protection_title)
            .setMessage(
                getString(R.string.dialog_disable_protection_message)
            )
            .setNegativeButton(R.string.action_cancel, null)
            .setPositiveButton(R.string.action_disable) { _, _ ->
                if (policyManager.clearDeviceOwnerForRemoval(this)) {
                    Toast.makeText(this, R.string.toast_protection_disabled, Toast.LENGTH_LONG).show()
                    openOwnAppSettings()
                }
            }
            .show()
    }

    private fun openOwnAppSettings(showErrorToast: Boolean = false) {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { startActivity(intent) }
            .onFailure {
                if (showErrorToast) {
                    Toast.makeText(this, R.string.toast_open_settings_failed, Toast.LENGTH_LONG).show()
                }
            }
    }

    private fun openAccessibilityServiceSettings() {
        val serviceComponent = ComponentName(this, KioskAccessibilityService::class.java)
        val detailIntent = Intent(ACTION_ACCESSIBILITY_DETAILS_SETTINGS).apply {
            putExtra(Intent.EXTRA_COMPONENT_NAME, serviceComponent)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        if (tryStartSettingsActivity(detailIntent)) return

        val listIntent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        if (!tryStartSettingsActivity(listIntent)) {
            Toast.makeText(this, R.string.toast_open_settings_failed, Toast.LENGTH_LONG).show()
        }
    }

    private fun tryStartSettingsActivity(intent: Intent): Boolean =
        runCatching {
            startActivity(intent)
        }.isSuccess

    private fun maybeSyncRemoteConfig() {
        if (syncInFlight) return
        if (!ConfigSyncer(this).shouldSyncNow()) return
        syncRemoteConfig(showToast = false, refreshAfter = currentScreen == Screen.LAUNCHER)
    }

    private fun syncRemoteConfig(showToast: Boolean, refreshAfter: Boolean) {
        if (syncInFlight) return
        syncInFlight = true

        Thread {
            val result = ConfigSyncer(applicationContext).sync()
            runOnUiThread {
                syncInFlight = false
                policyManager.applyDeviceOwnerPolicies(preferences.getAllowedPackages())
                if (showToast) {
                    Toast.makeText(this, result.message, Toast.LENGTH_LONG).show()
                }
                if (refreshAfter) {
                    if (currentScreen == Screen.ADMIN) showAdminScreen() else showLauncherScreen()
                }
            }
        }.start()
    }

    private fun launchApp(app: LaunchableApp) {
        val intent = packageManager.getLaunchIntentForPackage(app.packageName)
        if (intent == null) {
            Toast.makeText(this, getString(R.string.toast_open_failed, app.label), Toast.LENGTH_SHORT).show()
            return
        }

        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        runCatching {
            startActivity(intent)
        }.onFailure {
            Toast.makeText(this, R.string.toast_launch_blocked, Toast.LENGTH_SHORT).show()
        }
    }

    private fun confirmQuickCall(contact: QuickCallContact) {
        AlertDialog.Builder(this)
            .setTitle(R.string.dialog_quick_call_title)
            .setMessage(getString(R.string.dialog_quick_call_message, contact.name))
            .setNegativeButton(R.string.action_no, null)
            .setPositiveButton(R.string.action_yes) { _, _ ->
                startQuickCall(contact)
            }
            .show()
    }

    private fun startQuickCall(contact: QuickCallContact) {
        if (!hasCallPermission()) {
            Toast.makeText(
                this,
                getString(R.string.toast_quick_calls_need_permission),
                Toast.LENGTH_LONG
            ).show()
            return
        }
        placeQuickCall(contact)
    }

    private fun placeQuickCall(contact: QuickCallContact) {
        val intent = Intent(Intent.ACTION_CALL).apply {
            data = Uri.parse("tel:${Uri.encode(contact.phone)}")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching {
            startActivity(intent)
        }.onFailure {
            Toast.makeText(this, R.string.toast_call_failed, Toast.LENGTH_LONG).show()
        }
    }

    private fun hasCallPermission(): Boolean =
        checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED

    private fun refreshApps() {
        launchableApps = appRepository.getLaunchableApps()
    }

    private fun policyStatusSection(): View {
        val status = if (policyManager.isDeviceOwner()) {
            getString(R.string.policy_device_owner_active)
        } else {
            getString(
                R.string.policy_device_owner_inactive,
                policyManager.setupCommand(),
                policyManager.setHomeCommand()
            )
        }

        val text = infoText(status).apply {
            setTextIsSelectable(true)
        }
        return section(getString(R.string.section_protection_status), text)
    }

    private fun fallbackProtectionSection(): View {
        val deviceAdminStatus = if (policyManager.isDeviceAdminActive()) getString(R.string.status_enabled) else getString(R.string.status_disabled)
        val accessibilityStatus = if (isAccessibilityProtectionEnabled()) getString(R.string.status_enabled) else getString(R.string.status_disabled)
        val callStatus = if (hasCallPermission()) getString(R.string.status_calls_allowed) else getString(R.string.status_calls_not_allowed)

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(infoText(
                getString(
                    R.string.fallback_status,
                    deviceAdminStatus,
                    accessibilityStatus,
                    callStatus
                )
            ))
            addView(adminActionButton(getString(R.string.button_enable_device_admin)) {
                preferences.markAdminSessionUnlocked()
                runCatching { startActivity(policyManager.deviceAdminActivationIntent()) }
            }, matchWrapParams(top = 8))
            addView(adminActionButton(getString(R.string.button_open_accessibility_service)) {
                preferences.markAdminSessionUnlocked()
                openAccessibilityServiceSettings()
            }, matchWrapParams(top = 8))
            addView(infoText(getString(R.string.restricted_settings_help)), matchWrapParams(top = 10))
            addView(adminActionButton(getString(R.string.button_open_restricted_settings)) {
                preferences.markAdminSessionUnlocked()
                openOwnAppSettings(showErrorToast = true)
            }, matchWrapParams(top = 8))
            addView(adminActionButton(getString(R.string.button_allow_calls)) {
                preferences.markAdminSessionUnlocked()
                requestPermissions(arrayOf(Manifest.permission.CALL_PHONE), REQUEST_CALL_PHONE)
            }, matchWrapParams(top = 8))
        }
        return section(getString(R.string.section_fallback_protection), container)
    }

    private fun isAccessibilityProtectionEnabled(): Boolean {
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ).orEmpty()
        val expected = ComponentName(this, KioskAccessibilityService::class.java)
        return enabledServices.split(':').any { rawComponent ->
            val component = ComponentName.unflattenFromString(rawComponent)
            component?.packageName == expected.packageName &&
                component.className == expected.className
        }
    }

    private fun pinSection(): View {
        val currentPin = pinInput(getString(R.string.current_pin_hint))
        val newPin = pinInput(getString(R.string.new_pin_hint))
        lateinit var button: Button
        button = adminActionButton(getString(R.string.button_change_pin)) {
            val current = currentPin.text.toString()
            val new = newPin.text.toString()
            when {
                current.length !in 4..12 || current.any { !it.isDigit() } ->
                    currentPin.error = getString(R.string.error_enter_current_pin)
                new.length !in 4..12 || new.any { !it.isDigit() } ->
                    newPin.error = getString(R.string.error_enter_4_12_digits)
                else -> changePinInBackground(
                    current = current,
                    new = new,
                    currentPinInput = currentPin,
                    newPinInput = newPin,
                    button = button
                )
            }
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(currentPin, matchWrapParams(top = 8))
            addView(newPin, matchWrapParams(top = 8))
            if (preferences.isDefaultPin()) {
                addView(infoText(getString(R.string.default_pin_warning)))
            }
            addView(button, matchWrapParams(top = 12))
        }
        return section(getString(R.string.section_admin_pin), container)
    }

    private fun verifyAdminPinInBackground(
        pin: String,
        onComplete: (isValid: Boolean, errorMessage: String?) -> Unit
    ) {
        if (pinWorkInFlight) return
        pinWorkInFlight = true

        Thread {
            val result = runCatching { preferences.verifyPin(pin) }
            runOnUiThread {
                pinWorkInFlight = false
                if (isFinishing || isDestroyed) return@runOnUiThread
                onComplete(
                    result.getOrDefault(false),
                    result.exceptionOrNull()?.message?.let {
                        getString(R.string.error_pin_check_failed, it)
                    }
                )
            }
        }.start()
    }

    private fun changePinInBackground(
        current: String,
        new: String,
        currentPinInput: EditText,
        newPinInput: EditText,
        button: Button
    ) {
        if (pinWorkInFlight) return
        pinWorkInFlight = true
        button.isEnabled = false
        currentPinInput.isEnabled = false
        newPinInput.isEnabled = false
        val defaultErrorMessage = getString(R.string.error_pin_change_default)

        Thread {
            val result = runCatching {
                if (!preferences.verifyPin(current)) {
                    PinChangeResult(currentPinIsWrong = true)
                } else {
                    preferences.setPin(new)
                    PinChangeResult(success = true)
                }
            }.getOrElse { error ->
                PinChangeResult(errorMessage = error.message ?: defaultErrorMessage)
            }

            runOnUiThread {
                pinWorkInFlight = false
                if (isFinishing || isDestroyed) return@runOnUiThread
                button.isEnabled = true
                currentPinInput.isEnabled = true
                newPinInput.isEnabled = true

                when {
                    result.success -> {
                        currentPinInput.text.clear()
                        newPinInput.text.clear()
                        Toast.makeText(this, R.string.toast_pin_changed, Toast.LENGTH_SHORT).show()
                    }
                    result.currentPinIsWrong -> currentPinInput.error = getString(R.string.error_wrong_pin)
                    else -> Toast.makeText(
                        this,
                        getString(R.string.error_pin_change_failed, result.errorMessage),
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }.start()
    }

    private fun serverSection(): View {
        val serverUrl = textInput(getString(R.string.server_url_hint)).apply {
            setText(preferences.getServerUrl())
        }
        val serverToken = textInput(getString(R.string.server_token_hint)).apply {
            setText(preferences.getServerToken())
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val status = infoText(
            getString(
                R.string.sync_status_format,
                formatTime(preferences.getLastSyncSuccessAt()),
                preferences.getLastSyncMessage()
            )
        )
        val saveButton = adminActionButton(getString(R.string.button_save_server)) {
            preferences.setServerUrl(serverUrl.text.toString())
            preferences.setServerToken(serverToken.text.toString())
            ConfigSyncScheduler.schedule(this)
            Toast.makeText(this, R.string.toast_server_saved, Toast.LENGTH_SHORT).show()
        }
        val syncButton = adminActionButton(getString(R.string.button_sync_now)) {
            preferences.setServerUrl(serverUrl.text.toString())
            preferences.setServerToken(serverToken.text.toString())
            ConfigSyncScheduler.schedule(this)
            syncRemoteConfig(showToast = true, refreshAfter = true)
        }

        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(saveButton, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(syncButton, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(8)
            })
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(infoText(getString(R.string.remote_server_info)))
            addView(serverUrl, matchWrapParams(top = 8))
            addView(serverToken, matchWrapParams(top = 8))
            addView(status, matchWrapParams(top = 10))
            addView(buttons, matchWrapParams(top = 12))
        }
        return section(getString(R.string.section_remote_management), container)
    }

    private fun quickCallsSection(): View {
        val editor = multiLineInput(getString(R.string.quick_call_editor_hint)).apply {
            setText(formatQuickCallContacts(preferences.getQuickCallContacts()))
        }
        val saveButton = adminActionButton(getString(R.string.button_save_quick_calls)) {
            val contacts = parseQuickCallContacts(editor.text.toString())
            preferences.setQuickCallContacts(contacts)
            Toast.makeText(this, R.string.toast_quick_calls_saved, Toast.LENGTH_SHORT).show()
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(infoText(getString(R.string.quick_calls_format_help)))
            addView(editor, matchWrapParams(top = 8))
            addView(saveButton, matchWrapParams(top = 10))
        }
        return section(getString(R.string.section_quick_calls), container)
    }

    private fun languageSection(): View {
        val languages = AppLocaleManager.supportedLanguages
        var selectedLanguageTag = preferences.getAppLanguageTag()
        val labels = languages.map { language ->
            if (language.tag == AppLocaleManager.SYSTEM_LANGUAGE_TAG) {
                getString(R.string.language_system)
            } else {
                language.label
            }
        }
        val spinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_item,
                labels
            ).also { adapter ->
                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            }
            setSelection(languages.indexOfFirst { it.tag == selectedLanguageTag }.coerceAtLeast(0))
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(
                    parent: AdapterView<*>?,
                    view: View?,
                    position: Int,
                    id: Long
                ) {
                    selectedLanguageTag = languages.getOrNull(position)?.tag
                        ?: AppLocaleManager.SYSTEM_LANGUAGE_TAG
                }

                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            }
        }
        val saveButton = adminActionButton(getString(R.string.button_save_language)) {
            preferences.setAppLanguageTag(selectedLanguageTag)
            Toast.makeText(this, R.string.toast_language_saved, Toast.LENGTH_SHORT).show()
            recreate()
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(infoText(getString(R.string.language_info)))
            addView(spinner, matchWrapParams(top = 8))
            addView(saveButton, matchWrapParams(top = 10))
        }
        return section(getString(R.string.section_language), container)
    }

    private fun formatQuickCallContacts(contacts: List<QuickCallContact>): String =
        contacts.joinToString(separator = "\n") { "${it.name} | ${it.phone}" }

    private fun parseQuickCallContacts(raw: String): List<QuickCallContact> =
        raw.lines().mapNotNull { line ->
            val trimmed = line.trim()
            if (trimmed.isEmpty()) return@mapNotNull null
            val separatorIndex = listOf(
                trimmed.indexOf('|'),
                trimmed.indexOf(';'),
                trimmed.indexOf(',')
            ).filter { it >= 0 }.minOrNull() ?: return@mapNotNull null

            val name = trimmed.substring(0, separatorIndex).trim()
            val phone = trimmed.substring(separatorIndex + 1).trim()
            if (name.isEmpty() || phone.isEmpty()) null else QuickCallContact(name, phone)
        }

    private fun kioskHeader(onAdminClick: () -> Unit): View {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(12))
            setBackgroundColor(HomeCageColors.Background)
        }
        val titleColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        val title = TextView(this).apply {
            text = getString(R.string.app_name)
            textSize = 32f
            setTextColor(HomeCageColors.TextPrimary)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 1
        }
        val subtitle = TextView(this).apply {
            text = getString(R.string.home_safe_mode_armed)
            textSize = 13f
            setTextColor(HomeCageColors.AccentGreen)
            maxLines = 1
            setPadding(0, dp(2), 0, 0)
        }
        titleColumn.addView(title)
        titleColumn.addView(subtitle)

        layout.addView(titleColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        layout.addView(adminPillButton(onAdminClick))
        return layout
    }

    private fun adminPillButton(onClick: () -> Unit): View =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            minimumHeight = dp(48)
            isClickable = true
            isFocusable = true
            contentDescription = getString(R.string.home_admin_content_description)
            setPadding(dp(12), 0, dp(14), 0)
            background = roundedBackground(HomeCageColors.CardRaised, HomeCageColors.Border, radiusDp = 20)
            setOnClickListener { onClick() }

            addView(statusDot(sizeDp = 8), LinearLayout.LayoutParams(dp(8), dp(8)).apply {
                marginEnd = dp(8)
            })
            addView(TextView(this@MainActivity).apply {
                text = getString(R.string.action_admin)
                textSize = 14f
                setTextColor(HomeCageColors.TextPrimary)
                typeface = Typeface.DEFAULT_BOLD
                maxLines = 1
            })
        }

    private fun statusStrip(allowedAppsCount: Int, quickContactCount: Int): View {
        val status = "${allowedAppsLabel(allowedAppsCount)} $STATUS_SEPARATOR ${quickContactsLabel(quickContactCount)}"
        return homeCardContainer(minHeightDp = 56, radiusDp = 22).apply {
            contentDescription = status
            addView(LinearLayout(this@MainActivity).apply {
                gravity = Gravity.CENTER
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                addView(statusDot(sizeDp = 10), LinearLayout.LayoutParams(dp(10), dp(10)))
            }, LinearLayout.LayoutParams(dp(28), dp(28)).apply {
                marginEnd = dp(8)
            })
            addView(TextView(this@MainActivity).apply {
                text = status
                textSize = 14f
                setTextColor(HomeCageColors.TextSecondary)
                maxLines = 1
                ellipsize = TextUtils.TruncateAt.END
            }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        }
    }

    private fun homeSectionTitle(text: String): View =
        TextView(this).apply {
            this.text = text
            textSize = 13f
            setTextColor(HomeCageColors.AccentGreen)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 1
            setPadding(dp(2), dp(18), dp(2), dp(8))
        }

    private fun quickCallCard(contact: QuickCallContact): View {
        val row = homeCardContainer(minHeightDp = 88, radiusDp = 24).apply {
            isClickable = true
            isFocusable = true
            contentDescription = getString(R.string.home_quick_call_content_description, contact.name)
            setOnClickListener { confirmQuickCall(contact) }
        }
        val avatar = TextView(this).apply {
            text = contact.name.trim().take(1).uppercase()
            textSize = 22f
            gravity = Gravity.CENTER
            setTextColor(HomeCageColors.Background)
            typeface = Typeface.DEFAULT_BOLD
            background = roundedBackground(HomeCageColors.AccentGreen, HomeCageColors.AccentGreen, radiusDp = 18)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        val textColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        val name = TextView(this).apply {
            text = contact.name
            textSize = 19f
            setTextColor(HomeCageColors.TextPrimary)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
        }
        val phone = TextView(this).apply {
            text = contact.phone
            textSize = 13f
            setTextColor(HomeCageColors.TextSecondary)
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
        }
        val label = TextView(this).apply {
            text = getString(R.string.home_emergency_contact)
            textSize = 12f
            setTextColor(HomeCageColors.TextSecondary)
            maxLines = 1
        }
        textColumn.addView(name)
        textColumn.addView(phone)
        textColumn.addView(label)

        row.addView(avatar, LinearLayout.LayoutParams(dp(56), dp(56)).apply {
            marginEnd = dp(14)
        })
        row.addView(textColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(chevronView())
        return row
    }

    private fun allowedAppCard(app: LaunchableApp): View {
        val row = homeCardContainer(minHeightDp = 82, radiusDp = 22).apply {
            isClickable = true
            isFocusable = true
            contentDescription = getString(R.string.home_allowed_app_content_description, app.label)
            setOnClickListener { launchApp(app) }
        }
        val textColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        val name = TextView(this).apply {
            text = app.label
            textSize = 17f
            setTextColor(HomeCageColors.TextPrimary)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
        }
        val label = TextView(this).apply {
            text = getString(R.string.home_allowed_app_label)
            textSize = 12f
            setTextColor(HomeCageColors.TextSecondary)
            maxLines = 1
        }
        textColumn.addView(name)
        textColumn.addView(label)

        row.addView(appIconBadge(app), LinearLayout.LayoutParams(dp(56), dp(56)).apply {
            marginEnd = dp(14)
        })
        row.addView(textColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(chevronView())
        return row
    }

    private fun emptyStateCard(text: String): View =
        homeCardContainer(minHeightDp = 72, radiusDp = 22).apply {
            addView(TextView(this@MainActivity).apply {
                this.text = text
                textSize = 15f
                gravity = Gravity.CENTER_VERTICAL
                setTextColor(HomeCageColors.TextSecondary)
            }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        }

    private fun homeCardContainer(minHeightDp: Int, radiusDp: Int): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(minHeightDp)
            background = roundedBackground(HomeCageColors.Card, HomeCageColors.Border, radiusDp = radiusDp)
            setPadding(dp(18), dp(14), dp(18), dp(14))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, dp(5), 0, dp(7))
            }
        }

    private fun appIconBadge(app: LaunchableApp): View =
        LinearLayout(this).apply {
            gravity = Gravity.CENTER
            background = roundedBackground(HomeCageColors.CardRaised, HomeCageColors.Border, radiusDp = 16)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            addView(ImageView(this@MainActivity).apply {
                setImageDrawable(app.icon)
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.CENTER_INSIDE
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }, LinearLayout.LayoutParams(dp(40), dp(40)))
        }

    private fun chevronView(): TextView =
        TextView(this).apply {
            text = "\u203a"
            textSize = 30f
            gravity = Gravity.CENTER
            setTextColor(HomeCageColors.AccentGreen)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            layoutParams = LinearLayout.LayoutParams(dp(28), dp(48)).apply {
                marginStart = dp(8)
            }
        }

    private fun statusDot(sizeDp: Int): View =
        View(this).apply {
            background = roundedBackground(HomeCageColors.AccentGreen, HomeCageColors.AccentGreen, radiusDp = sizeDp / 2)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }

    private fun allowedAppsLabel(count: Int): String =
        getString(
            if (count == 1) R.string.home_apps_allowed_one else R.string.home_apps_allowed_many,
            count
        )

    private fun quickContactsLabel(count: Int): String =
        getString(
            if (count == 1) R.string.home_quick_contacts_one else R.string.home_quick_contacts_many,
            count
        )

    private fun appCheckRow(app: LaunchableApp, selectedPackages: MutableSet<String>): View {
        val row = rowContainer()
        val checkBox = CheckBox(this).apply {
            isChecked = app.packageName in selectedPackages
            setOnCheckedChangeListener { _, isChecked ->
                if (isChecked) {
                    selectedPackages.add(app.packageName)
                } else {
                    selectedPackages.remove(app.packageName)
                }
            }
        }
        val textColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        val label = TextView(this).apply {
            text = app.label
            textSize = 16f
            setTextColor(COLOR_TEXT)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 2
        }
        val packageName = TextView(this).apply {
            text = if (app.isSystem) {
                "${app.packageName}  ${getString(R.string.system_badge)}"
            } else {
                app.packageName
            }
            textSize = 12f
            setTextColor(COLOR_MUTED)
            maxLines = 2
        }
        textColumn.addView(label)
        textColumn.addView(packageName)

        row.addView(checkBox)
        row.addView(appIcon(app))
        row.addView(textColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        row.setOnClickListener {
            checkBox.isChecked = !checkBox.isChecked
        }
        return row
    }

    private fun adminHeader(onBack: () -> Unit, onSave: () -> Unit): View {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(14), dp(12), dp(10))
            setBackgroundColor(COLOR_SURFACE)
        }
        val back = Button(this).apply {
            text = getString(R.string.action_back)
            setAllCaps(false)
            setOnClickListener { onBack() }
        }
        val title = TextView(this).apply {
            text = getString(R.string.action_admin)
            textSize = 22f
            gravity = Gravity.CENTER
            setTextColor(COLOR_TEXT)
            typeface = Typeface.DEFAULT_BOLD
        }
        val save = Button(this).apply {
            text = getString(R.string.action_save)
            setAllCaps(false)
            setOnClickListener { onSave() }
        }
        layout.addView(back)
        layout.addView(title, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        layout.addView(save)
        return layout
    }

    private fun section(title: String, body: View): View {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = roundedBackground(COLOR_SURFACE, COLOR_BORDER)
            setPadding(dp(14), dp(12), dp(14), dp(14))
        }
        val titleView = TextView(this).apply {
            text = title
            textSize = 16f
            setTextColor(COLOR_TEXT)
            typeface = Typeface.DEFAULT_BOLD
        }
        container.addView(titleView)
        container.addView(body, matchWrapParams(top = 8))
        return withMargins(container, top = 8, bottom = 10)
    }

    private fun sectionTitle(text: String): View =
        TextView(this).apply {
            this.text = text
            textSize = 18f
            setTextColor(COLOR_TEXT)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(2), dp(18), dp(2), dp(8))
        }

    private fun infoText(text: String): TextView =
        TextView(this).apply {
            this.text = text
            textSize = 14f
            setTextColor(COLOR_MUTED)
            setLineSpacing(dp(2).toFloat(), 1.0f)
        }

    private fun adminActionButton(text: String, onClick: () -> Unit): Button =
        Button(this).apply {
            this.text = text
            setAllCaps(false)
            setOnClickListener { onClick() }
        }

    private fun pinInput(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
            maxLines = 1
        }

    private fun textInput(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            maxLines = 1
        }

    private fun multiLineInput(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 3
            maxLines = 8
            gravity = Gravity.TOP
        }

    private fun appIcon(app: LaunchableApp): ImageView =
        ImageView(this).apply {
            setImageDrawable(app.icon)
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            layoutParams = LinearLayout.LayoutParams(dp(44), dp(44)).apply {
                marginEnd = dp(12)
            }
        }

    private fun rowContainer(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = roundedBackground(COLOR_SURFACE, COLOR_BORDER)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, dp(5), 0, dp(5))
            }
        }

    private fun verticalRoot(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(COLOR_BACKGROUND)
        }

    private fun homeRoot(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(HomeCageColors.Background)
        }

    private fun paddedDialogView(view: View): View =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), 0)
            addView(view)
        }

    private fun weightParams(): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            0,
            1f
        )

    private fun matchWrapParams(top: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply {
            if (top > 0) topMargin = dp(top)
        }

    private fun withMargins(view: View, top: Int = 0, bottom: Int = 0): View {
        view.layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply {
            topMargin = dp(top)
            bottomMargin = dp(bottom)
        }
        return view
    }

    private fun roundedBackground(
        color: Int,
        strokeColor: Int,
        radiusDp: Int = 8,
        strokeDp: Int = 1
    ): GradientDrawable =
        GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(radiusDp).toFloat()
            setStroke(dp(strokeDp), strokeColor)
        }

    private fun enterImmersiveMode() {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                View.SYSTEM_UI_FLAG_FULLSCREEN or
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).roundToInt()

    private fun formatTime(timeMillis: Long): String =
        if (timeMillis <= 0L) {
            getString(R.string.time_none)
        } else {
            DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(timeMillis))
        }

    private data class PinChangeResult(
        val success: Boolean = false,
        val currentPinIsWrong: Boolean = false,
        val errorMessage: String = ""
    )

    private enum class Screen {
        LAUNCHER,
        ADMIN
    }

    private companion object {
        const val ACTION_ACCESSIBILITY_DETAILS_SETTINGS = "android.settings.ACCESSIBILITY_DETAILS_SETTINGS"
        const val REQUEST_CALL_PHONE = 4101
        const val STATUS_SEPARATOR = "\u00b7"
        val COLOR_BACKGROUND: Int = Color.rgb(248, 250, 252)
        val COLOR_SURFACE: Int = Color.WHITE
        val COLOR_TEXT: Int = Color.rgb(15, 23, 42)
        val COLOR_MUTED: Int = Color.rgb(71, 85, 105)
        val COLOR_BORDER: Int = Color.rgb(226, 232, 240)
    }
}
