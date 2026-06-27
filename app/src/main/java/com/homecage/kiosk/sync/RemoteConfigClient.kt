package com.homecage.kiosk.sync

import com.homecage.kiosk.data.LaunchableApp
import com.homecage.kiosk.data.RestrictionMode
import com.homecage.kiosk.data.RestrictionScheduleRule
import com.homecage.kiosk.data.SecurityEventReport
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class RemoteKioskConfig(
    val allowedPackages: Set<String>,
    val pin: String?,
    val restrictionMode: RestrictionMode,
    val scheduleRules: List<RestrictionScheduleRule>,
    val locationRequestId: Long,
    val updatedAt: String
)

class RemoteConfigClient(
    private val rawServerUrl: String,
    private val token: String
) {
    fun reportDeviceState(
        deviceId: String,
        deviceName: String,
        installedApps: List<LaunchableApp>,
        localAllowedPackages: Set<String>,
        restrictionMode: RestrictionMode,
        location: DeviceLocationReport?,
        appliedConfigUpdatedAt: String,
        configApplyStatus: String,
        protectionHealth: ProtectionHealthReport
    ) {
        val payload = JSONObject().apply {
            put("deviceId", deviceId)
            put("deviceName", deviceName)
            put("restrictionMode", restrictionMode.wireValue)
            put("lockdownEnabled", restrictionMode == RestrictionMode.LOST)
            if (appliedConfigUpdatedAt.isNotBlank()) {
                put("appliedConfigUpdatedAt", appliedConfigUpdatedAt)
            }
            if (configApplyStatus.isNotBlank()) {
                put("configApplyStatus", configApplyStatus)
            }
            put("installedApps", JSONArray().apply {
                installedApps.forEach { app ->
                    put(JSONObject().apply {
                        put("label", app.label)
                        put("packageName", app.packageName)
                        put("isSystem", app.isSystem)
                    })
                }
            })
            put("localAllowedPackages", JSONArray().apply {
                localAllowedPackages.sorted().forEach { put(it) }
            })
            put("protectionHealth", JSONObject().apply {
                put("deviceOwnerEnabled", protectionHealth.deviceOwnerEnabled)
                put("deviceAdminEnabled", protectionHealth.deviceAdminEnabled)
                put("accessibilityEnabled", protectionHealth.accessibilityEnabled)
                put("overlayEnabled", protectionHealth.overlayEnabled)
                put("usageAccessEnabled", protectionHealth.usageAccessEnabled)
                put("callPermissionGranted", protectionHealth.callPermissionGranted)
                put("locationPermissionGranted", protectionHealth.locationPermissionGranted)
                put("flashlightPermissionGranted", protectionHealth.flashlightPermissionGranted)
            })
            if (location != null) {
                put("location", JSONObject().apply {
                    put("requestId", location.requestId)
                    put("status", location.status)
                    location.latitude?.let { put("latitude", it) }
                    location.longitude?.let { put("longitude", it) }
                    location.accuracyMeters?.let { put("accuracyMeters", it.toDouble()) }
                    location.provider?.let { put("provider", it) }
                    location.capturedAtMillis?.let { put("capturedAtMillis", it) }
                })
            }
        }
        request(path = "/api/device-state", method = "POST", body = payload.toString())
    }

    fun reportSecurityEvent(
        deviceId: String,
        deviceName: String,
        report: SecurityEventReport
    ) {
        val payload = report.toJson().apply {
            put("deviceId", deviceId)
            put("deviceName", deviceName)
        }
        request(path = "/api/security-events", method = "POST", body = payload.toString())
    }

    fun fetchConfig(deviceId: String, deviceName: String): RemoteKioskConfig {
        val body = request(
            path = "/api/config?deviceId=${urlEncode(deviceId)}&deviceName=${urlEncode(deviceName)}",
            method = "GET"
        )
        val root = JSONObject(body)
        val packages = root.optJSONArray("allowedPackages") ?: JSONArray()
        val allowedPackages = buildSet {
            for (index in 0 until packages.length()) {
                val packageName = packages.optString(index).trim()
                if (packageName.isNotEmpty()) add(packageName)
            }
        }
        val pin = if (root.isNull("pin")) {
            null
        } else {
            root.optString("pin", "").trim().ifEmpty { null }
        }
        if (pin != null && (pin.length !in 4..12 || pin.any { !it.isDigit() })) {
            error("Server returned an invalid PIN")
        }
        val restrictionMode = if (root.has("restrictionMode")) {
            RestrictionMode.fromWireValue(root.optString("restrictionMode"))
        } else if (root.optBoolean("parentalLockEnabled", false)) {
            RestrictionMode.PARENTAL
        } else if (root.optBoolean("lockdownEnabled", false)) {
            RestrictionMode.LOST
        } else {
            RestrictionMode.NONE
        }
        return RemoteKioskConfig(
            allowedPackages = allowedPackages,
            pin = pin,
            restrictionMode = restrictionMode,
            scheduleRules = RestrictionScheduleRule.fromJsonArray(root.optJSONArray("scheduleRules")),
            locationRequestId = root.optLong("locationRequestId", 0L),
            updatedAt = root.optString("updatedAt", "")
        )
    }

    private fun request(path: String, method: String, body: String? = null): String {
        val connection = URL(buildUrl(path)).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = CONNECT_TIMEOUT_MS
        connection.readTimeout = READ_TIMEOUT_MS
        connection.setRequestProperty("Accept", "application/json")
        if (token.isNotBlank()) {
            connection.setRequestProperty("Authorization", "Bearer $token")
        }
        if (body != null) {
            val bytes = body.toByteArray(Charsets.UTF_8)
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Content-Length", bytes.size.toString())
            connection.outputStream.use { it.write(bytes) }
        }

        val responseCode = connection.responseCode
        val responseBody = readStream(
            if (responseCode in 200..299) connection.inputStream else connection.errorStream
        )
        connection.disconnect()

        if (responseCode !in 200..299) {
            error("Server responded HTTP $responseCode: $responseBody")
        }
        return responseBody
    }

    private fun buildUrl(path: String): String {
        val base = rawServerUrl.trim()
        require(base.isNotEmpty()) { "Server URL is empty" }
        val withScheme = if (base.startsWith("http://") || base.startsWith("https://")) {
            base
        } else {
            "https://$base"
        }
        return withScheme.trimEnd('/') + path
    }

    private fun readStream(stream: InputStream?): String {
        if (stream == null) return ""
        return BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { it.readText() }
    }

    private fun urlEncode(value: String): String =
        URLEncoder.encode(value, Charsets.UTF_8.name())

    private companion object {
        const val CONNECT_TIMEOUT_MS = 8_000
        const val READ_TIMEOUT_MS = 12_000
    }
}
