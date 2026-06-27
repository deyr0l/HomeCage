package com.homecage.kiosk.data

import android.content.Context
import android.os.Build
import android.util.Base64
import com.homecage.kiosk.R
import com.homecage.kiosk.locale.AppLocaleManager
import org.json.JSONArray
import org.json.JSONObject
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

class KioskPreferences(private val context: Context) {
    private val preferences =
        context.getSharedPreferences("kid_kiosk_preferences", Context.MODE_PRIVATE)
    private val random = SecureRandom()

    init {
        if (!preferences.contains(KEY_PIN_HASH)) {
            setPin(context.getString(R.string.default_pin), isDefault = true)
        }
    }

    fun getAllowedPackages(): Set<String> =
        preferences.getStringSet(KEY_ALLOWED_PACKAGES, emptySet()).orEmpty()

    fun setAllowedPackages(packages: Set<String>) {
        preferences.edit()
            .putStringSet(KEY_ALLOWED_PACKAGES, packages.toSet())
            .apply()
    }

    fun getManualPackages(): Set<String> =
        preferences.getStringSet(KEY_MANUAL_PACKAGES, emptySet()).orEmpty()

    fun setManualPackages(packages: Set<String>) {
        preferences.edit()
            .putStringSet(KEY_MANUAL_PACKAGES, packages.toSet())
            .apply()
    }

    fun getLaunchableAllowedPackages(): Set<String> =
        getAllowedPackages() - getManualPackages()

    fun getPolicyRevision(): Long =
        preferences.getLong(KEY_POLICY_REVISION, 0L)

    fun updatePolicy(allowedPackages: Set<String>, manualPackages: Set<String>) {
        synchronized(POLICY_LOCK) {
            preferences.edit()
                .putStringSet(KEY_ALLOWED_PACKAGES, allowedPackages.toSet())
                .putStringSet(KEY_MANUAL_PACKAGES, manualPackages.toSet())
                .putLong(KEY_POLICY_REVISION, getPolicyRevision() + 1)
                .apply()
        }
    }

    fun updatePolicyIfRevisionUnchanged(
        expectedRevision: Long,
        allowedPackages: Set<String>,
        manualPackages: Set<String>
    ): Boolean =
        synchronized(POLICY_LOCK) {
            if (getPolicyRevision() != expectedRevision) {
                false
            } else {
                preferences.edit()
                    .putStringSet(KEY_ALLOWED_PACKAGES, allowedPackages.toSet())
                    .putStringSet(KEY_MANUAL_PACKAGES, manualPackages.toSet())
                    .putLong(KEY_POLICY_REVISION, expectedRevision + 1)
                    .apply()
                true
            }
        }

    fun getAppLanguageTag(): String =
        AppLocaleManager.getSelectedLanguageTag(context)

    fun setAppLanguageTag(tag: String) {
        AppLocaleManager.setSelectedLanguageTag(context, tag)
    }

    fun getQuickCallContacts(): List<QuickCallContact> {
        val rawJson = preferences.getString(KEY_QUICK_CALL_CONTACTS, "[]").orEmpty()
        return runCatching {
            val array = JSONArray(rawJson)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val name = item.optString("name").trim()
                    val phone = item.optString("phone").trim()
                    if (name.isNotEmpty() && phone.isNotEmpty()) {
                        add(QuickCallContact(name = name, phone = phone))
                    }
                }
            }
        }.getOrDefault(emptyList())
    }

    fun setQuickCallContacts(contacts: List<QuickCallContact>) {
        val array = JSONArray()
        contacts
            .map { it.copy(name = it.name.trim(), phone = it.phone.trim()) }
            .filter { it.name.isNotEmpty() && it.phone.isNotEmpty() }
            .distinctBy { "${it.name.lowercase()}|${it.phone}" }
            .forEach { contact ->
                array.put(JSONObject().apply {
                    put("name", contact.name)
                    put("phone", contact.phone)
                })
            }

        preferences.edit()
            .putString(KEY_QUICK_CALL_CONTACTS, array.toString())
            .apply()
    }

    fun getScheduleRules(): List<RestrictionScheduleRule> =
        RestrictionScheduleRule.fromJson(
            preferences.getString(KEY_SCHEDULE_RULES, "[]").orEmpty()
        )

    fun setScheduleRules(rules: List<RestrictionScheduleRule>) {
        preferences.edit()
            .putString(KEY_SCHEDULE_RULES, RestrictionScheduleRule.toJson(rules))
            .apply()
    }

    fun getServerUrl(): String =
        preferences.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL).orEmpty()

    fun setServerUrl(serverUrl: String) {
        preferences.edit()
            .putString(KEY_SERVER_URL, serverUrl.trim())
            .apply()
    }

    fun getServerToken(): String =
        preferences.getString(KEY_SERVER_TOKEN, "").orEmpty()

    fun setServerToken(serverToken: String) {
        preferences.edit()
            .putString(KEY_SERVER_TOKEN, serverToken.trim())
            .apply()
    }

    fun getDeviceName(): String {
        val savedName = preferences.getString(KEY_DEVICE_NAME, "").orEmpty().trim()
        if (savedName.isNotEmpty()) return savedName
        return Build.MODEL?.takeIf { it.isNotBlank() } ?: "HomeCage device"
    }

    fun setDeviceName(deviceName: String) {
        preferences.edit()
            .putString(KEY_DEVICE_NAME, deviceName.trim())
            .apply()
    }

    fun getLastSyncAttemptAt(): Long =
        preferences.getLong(KEY_LAST_SYNC_ATTEMPT_AT, 0L)

    fun getLastSyncSuccessAt(): Long =
        preferences.getLong(KEY_LAST_SYNC_SUCCESS_AT, 0L)

    fun getLastSyncMessage(): String =
        preferences.getString(KEY_LAST_SYNC_MESSAGE, context.getString(R.string.sync_never)).orEmpty()

    private fun getRestrictionMode(): RestrictionMode {
        val storedMode = preferences.getString(KEY_RESTRICTION_MODE, null)
        if (storedMode != null) return RestrictionMode.fromWireValue(storedMode)
        return if (preferences.getBoolean(KEY_LOCKDOWN_ENABLED, false)) {
            RestrictionMode.LOST
        } else {
            RestrictionMode.NONE
        }
    }

    fun getEffectiveRestrictionMode(nowMillis: Long = System.currentTimeMillis()): RestrictionMode =
        RestrictionMode.strongest(
            getRestrictionMode(),
            RestrictionScheduleRule.effectiveModeAt(getScheduleRules(), nowMillis)
        )

    fun setRestrictionMode(mode: RestrictionMode) {
        preferences.edit()
            .putString(KEY_RESTRICTION_MODE, mode.wireValue)
            .putBoolean(KEY_LOCKDOWN_ENABLED, mode == RestrictionMode.LOST)
            .apply()
    }

    fun markQuickCallSession(durationMillis: Long = QUICK_CALL_SESSION_DURATION_MS) {
        preferences.edit()
            .putLong(KEY_QUICK_CALL_SESSION_UNTIL, System.currentTimeMillis() + durationMillis)
            .apply()
    }

    fun isQuickCallSessionActive(nowMillis: Long = System.currentTimeMillis()): Boolean =
        preferences.getLong(KEY_QUICK_CALL_SESSION_UNTIL, 0L) > nowMillis

    fun getHandledLocationRequestId(): Long =
        preferences.getLong(KEY_HANDLED_LOCATION_REQUEST_ID, 0L)

    fun setHandledLocationRequestId(requestId: Long) {
        preferences.edit()
            .putLong(KEY_HANDLED_LOCATION_REQUEST_ID, requestId)
            .apply()
    }

    fun markSyncAttempt(atMillis: Long) {
        preferences.edit()
            .putLong(KEY_LAST_SYNC_ATTEMPT_AT, atMillis)
            .apply()
    }

    fun markSyncSuccess(atMillis: Long, message: String) {
        preferences.edit()
            .putLong(KEY_LAST_SYNC_SUCCESS_AT, atMillis)
            .putString(KEY_LAST_SYNC_MESSAGE, message)
            .apply()
    }

    fun markSyncFailure(message: String) {
        preferences.edit()
            .putString(KEY_LAST_SYNC_MESSAGE, message)
            .apply()
    }

    fun getLastAppliedRemoteConfigUpdatedAt(): String =
        preferences.getString(KEY_LAST_APPLIED_REMOTE_CONFIG_UPDATED_AT, "").orEmpty()

    fun getLastRemoteConfigApplyStatus(): String =
        preferences.getString(KEY_LAST_REMOTE_CONFIG_APPLY_STATUS, "").orEmpty()

    fun markRemoteConfigApplyResult(updatedAt: String, status: String) {
        preferences.edit()
            .putString(KEY_LAST_APPLIED_REMOTE_CONFIG_UPDATED_AT, updatedAt)
            .putString(KEY_LAST_REMOTE_CONFIG_APPLY_STATUS, status)
            .apply()
    }

    fun markAdminSessionUnlocked(durationMillis: Long = ADMIN_SESSION_DURATION_MS) {
        preferences.edit()
            .putLong(KEY_ADMIN_SESSION_UNTIL, System.currentTimeMillis() + durationMillis)
            .apply()
    }

    fun clearAdminSession() {
        preferences.edit()
            .remove(KEY_ADMIN_SESSION_UNTIL)
            .apply()
    }

    fun isAdminSessionUnlocked(nowMillis: Long = System.currentTimeMillis()): Boolean =
        preferences.getLong(KEY_ADMIN_SESSION_UNTIL, 0L) > nowMillis

    fun isDefaultPin(): Boolean =
        preferences.getBoolean(KEY_IS_DEFAULT_PIN, false)

    fun verifyPin(pin: String): Boolean {
        val salt = preferences.getString(KEY_PIN_SALT, null) ?: return false
        val expectedHash = preferences.getString(KEY_PIN_HASH, null) ?: return false
        val actualHash = hashPin(pin, salt)
        return constantTimeEquals(expectedHash, actualHash)
    }

    fun setPin(pin: String, isDefault: Boolean = false) {
        require(pin.length in 4..12) { "PIN length must be between 4 and 12 digits" }
        require(pin.all { it.isDigit() }) { "PIN must contain only digits" }

        val saltBytes = ByteArray(16)
        random.nextBytes(saltBytes)
        val salt = Base64.encodeToString(saltBytes, Base64.NO_WRAP)
        val hash = hashPin(pin, salt)

        preferences.edit()
            .putString(KEY_PIN_SALT, salt)
            .putString(KEY_PIN_HASH, hash)
            .putBoolean(KEY_IS_DEFAULT_PIN, isDefault)
            .apply()
    }

    private fun hashPin(pin: String, salt: String): String {
        val spec = PBEKeySpec(
            pin.toCharArray(),
            salt.toByteArray(Charsets.UTF_8),
            PIN_HASH_ITERATIONS,
            PIN_HASH_BITS
        )
        val key = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec)
        return Base64.encodeToString(key.encoded, Base64.NO_WRAP)
    }

    private fun constantTimeEquals(left: String, right: String): Boolean {
        if (left.length != right.length) return false
        var result = 0
        for (index in left.indices) {
            result = result or (left[index].code xor right[index].code)
        }
        return result == 0
    }

    private companion object {
        const val KEY_ALLOWED_PACKAGES = "allowed_packages"
        const val KEY_MANUAL_PACKAGES = "manual_packages"
        const val KEY_POLICY_REVISION = "policy_revision"
        const val KEY_PIN_SALT = "pin_salt"
        const val KEY_PIN_HASH = "pin_hash"
        const val KEY_IS_DEFAULT_PIN = "is_default_pin"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_SERVER_TOKEN = "server_token"
        const val KEY_DEVICE_NAME = "device_name"
        const val KEY_QUICK_CALL_CONTACTS = "quick_call_contacts"
        const val KEY_SCHEDULE_RULES = "schedule_rules"
        const val KEY_LAST_SYNC_ATTEMPT_AT = "last_sync_attempt_at"
        const val KEY_LAST_SYNC_SUCCESS_AT = "last_sync_success_at"
        const val KEY_LAST_SYNC_MESSAGE = "last_sync_message"
        const val KEY_ADMIN_SESSION_UNTIL = "admin_session_until"
        const val KEY_LOCKDOWN_ENABLED = "lockdown_enabled"
        const val KEY_RESTRICTION_MODE = "restriction_mode"
        const val KEY_QUICK_CALL_SESSION_UNTIL = "quick_call_session_until"
        const val KEY_HANDLED_LOCATION_REQUEST_ID = "handled_location_request_id"
        const val KEY_LAST_APPLIED_REMOTE_CONFIG_UPDATED_AT = "last_applied_remote_config_updated_at"
        const val KEY_LAST_REMOTE_CONFIG_APPLY_STATUS = "last_remote_config_apply_status"
        const val DEFAULT_SERVER_URL = ""
        const val ADMIN_SESSION_DURATION_MS = 5 * 60 * 1000L
        const val QUICK_CALL_SESSION_DURATION_MS = 15 * 60 * 1000L
        const val PIN_HASH_ITERATIONS = 80_000
        const val PIN_HASH_BITS = 256
        val POLICY_LOCK = Any()
    }
}
