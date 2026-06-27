package com.homecage.kiosk.data

import org.json.JSONArray
import org.json.JSONObject

data class SecurityTrailEntry(
    val atMillis: Long,
    val eventType: String,
    val packageName: String,
    val className: String,
    val decision: String,
    val restrictionMode: String
) {
    fun toJson(): JSONObject =
        JSONObject().apply {
            put("atMillis", atMillis)
            put("eventType", eventType)
            put("packageName", packageName)
            put("className", className)
            put("decision", decision)
            put("restrictionMode", restrictionMode)
        }

    companion object {
        fun fromJson(item: JSONObject?): SecurityTrailEntry? {
            if (item == null) return null
            val packageName = item.optString("packageName").trim()
            if (packageName.isEmpty()) return null
            return SecurityTrailEntry(
                atMillis = item.optLong("atMillis", 0L),
                eventType = item.optString("eventType").trim(),
                packageName = packageName,
                className = item.optString("className").trim(),
                decision = item.optString("decision").trim(),
                restrictionMode = item.optString("restrictionMode").trim()
            )
        }

        fun fromJson(rawJson: String): List<SecurityTrailEntry> =
            runCatching {
                val array = JSONArray(rawJson)
                buildList {
                    for (index in 0 until array.length()) {
                        fromJson(array.optJSONObject(index))?.let(::add)
                    }
                }
            }.getOrDefault(emptyList())

        fun toJson(entries: List<SecurityTrailEntry>): String =
            JSONArray().apply {
                entries.forEach { put(it.toJson()) }
            }.toString()
    }
}
