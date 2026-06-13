package com.homecage.kiosk.data

import android.content.Context
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

    fun getLastSyncAttemptAt(): Long =
        preferences.getLong(KEY_LAST_SYNC_ATTEMPT_AT, 0L)

    fun getLastSyncSuccessAt(): Long =
        preferences.getLong(KEY_LAST_SYNC_SUCCESS_AT, 0L)

    fun getLastSyncMessage(): String =
        preferences.getString(KEY_LAST_SYNC_MESSAGE, context.getString(R.string.sync_never)).orEmpty()

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
        const val KEY_PIN_SALT = "pin_salt"
        const val KEY_PIN_HASH = "pin_hash"
        const val KEY_IS_DEFAULT_PIN = "is_default_pin"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_SERVER_TOKEN = "server_token"
        const val KEY_QUICK_CALL_CONTACTS = "quick_call_contacts"
        const val KEY_LAST_SYNC_ATTEMPT_AT = "last_sync_attempt_at"
        const val KEY_LAST_SYNC_SUCCESS_AT = "last_sync_success_at"
        const val KEY_LAST_SYNC_MESSAGE = "last_sync_message"
        const val KEY_ADMIN_SESSION_UNTIL = "admin_session_until"
        const val DEFAULT_SERVER_URL = ""
        const val ADMIN_SESSION_DURATION_MS = 5 * 60 * 1000L
        const val PIN_HASH_ITERATIONS = 80_000
        const val PIN_HASH_BITS = 256
    }
}
