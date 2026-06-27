package com.homecage.kiosk.data

import org.json.JSONArray
import org.json.JSONObject

data class SecurityEventReport(
    val reportedAtMillis: Long,
    val triggerPackage: String,
    val triggerClassName: String,
    val reason: String,
    val trail: List<SecurityTrailEntry>
) {
    fun toJson(): JSONObject =
        JSONObject().apply {
            put("reportedAtMillis", reportedAtMillis)
            put("triggerPackage", triggerPackage)
            put("triggerClassName", triggerClassName)
            put("reason", reason)
            put("trail", JSONArray().apply {
                trail.forEach { put(it.toJson()) }
            })
        }

    companion object {
        fun fromJson(item: JSONObject?): SecurityEventReport? {
            if (item == null) return null
            val triggerPackage = item.optString("triggerPackage").trim()
            if (triggerPackage.isEmpty()) return null
            val trailArray = item.optJSONArray("trail") ?: JSONArray()
            val trail = buildList {
                for (index in 0 until trailArray.length()) {
                    SecurityTrailEntry.fromJson(trailArray.optJSONObject(index))?.let(::add)
                }
            }
            return SecurityEventReport(
                reportedAtMillis = item.optLong("reportedAtMillis", 0L),
                triggerPackage = triggerPackage,
                triggerClassName = item.optString("triggerClassName").trim(),
                reason = item.optString("reason").trim(),
                trail = trail
            )
        }

        fun fromJson(rawJson: String): List<SecurityEventReport> =
            runCatching {
                val array = JSONArray(rawJson)
                buildList {
                    for (index in 0 until array.length()) {
                        fromJson(array.optJSONObject(index))?.let(::add)
                    }
                }
            }.getOrDefault(emptyList())

        fun toJson(reports: List<SecurityEventReport>): String =
            JSONArray().apply {
                reports.forEach { put(it.toJson()) }
            }.toString()
    }
}
