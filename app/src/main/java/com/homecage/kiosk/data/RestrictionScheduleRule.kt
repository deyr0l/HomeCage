package com.homecage.kiosk.data

import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import java.util.Locale
import kotlin.math.max

data class RestrictionScheduleRule(
    val id: String,
    val enabled: Boolean,
    val days: Set<Int>,
    val startMinutes: Int,
    val endMinutes: Int,
    val mode: RestrictionMode
) {
    fun isActiveAt(nowMillis: Long = System.currentTimeMillis()): Boolean {
        if (!enabled || days.isEmpty() || mode == RestrictionMode.NONE) return false

        val calendar = Calendar.getInstance().apply { timeInMillis = nowMillis }
        val today = calendar.isoDayOfWeek()
        val nowMinutes = calendar.get(Calendar.HOUR_OF_DAY) * MINUTES_PER_HOUR +
            calendar.get(Calendar.MINUTE)

        if (startMinutes == endMinutes) {
            return today in days
        }
        if (startMinutes < endMinutes) {
            return today in days && nowMinutes in startMinutes until endMinutes
        }

        val yesterday = if (today == 1) 7 else today - 1
        return (today in days && nowMinutes >= startMinutes) ||
            (yesterday in days && nowMinutes < endMinutes)
    }

    fun toJson(): JSONObject =
        JSONObject().apply {
            put("id", id)
            put("enabled", enabled)
            put("days", JSONArray().apply { days.sorted().forEach { put(it) } })
            put("start", minutesToTime(startMinutes))
            put("end", minutesToTime(endMinutes))
            put("mode", mode.wireValue)
        }

    companion object {
        private const val MINUTES_PER_HOUR = 60
        private const val MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR

        fun effectiveModeAt(
            rules: List<RestrictionScheduleRule>,
            nowMillis: Long = System.currentTimeMillis()
        ): RestrictionMode =
            rules.fold(RestrictionMode.NONE) { current, rule ->
                if (rule.isActiveAt(nowMillis)) {
                    RestrictionMode.strongest(current, rule.mode)
                } else {
                    current
                }
            }

        fun nextChangeAfter(
            rules: List<RestrictionScheduleRule>,
            nowMillis: Long = System.currentTimeMillis()
        ): Long? {
            val enabledRules = rules.filter { it.enabled && it.days.isNotEmpty() && it.mode != RestrictionMode.NONE }
            if (enabledRules.isEmpty()) return null

            val candidates = mutableListOf<Long>()
            val base = Calendar.getInstance().apply {
                timeInMillis = nowMillis
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }

            enabledRules.forEach { rule ->
                for (dayOffset in 0..8) {
                    val dayStart = base.dayStartWithOffset(dayOffset)
                    val isoDay = dayStart.isoDayOfWeek()
                    if (isoDay !in rule.days) continue

                    val startMillis = dayStart.timeInMillis + rule.startMinutes * 60_000L
                    val endOffsetDays = if (rule.startMinutes >= rule.endMinutes) 1 else 0
                    val endMillis = dayStart.timeInMillis +
                        endOffsetDays * 24L * 60L * 60L * 1000L +
                        rule.endMinutes * 60_000L

                    if (startMillis > nowMillis) candidates.add(startMillis)
                    if (endMillis > nowMillis) candidates.add(endMillis)
                }
            }
            return candidates.minOrNull()
        }

        fun fromJson(rawJson: String): List<RestrictionScheduleRule> =
            runCatching {
                val array = JSONArray(rawJson)
                buildList {
                    for (index in 0 until array.length()) {
                        val rule = fromJsonObject(array.optJSONObject(index), index) ?: continue
                        add(rule)
                    }
                }
            }.getOrDefault(emptyList())

        fun toJson(rules: List<RestrictionScheduleRule>): String =
            JSONArray().apply {
                rules.forEach { put(it.toJson()) }
            }.toString()

        fun fromJsonArray(array: JSONArray?): List<RestrictionScheduleRule> =
            buildList {
                if (array == null) return@buildList
                for (index in 0 until array.length()) {
                    val rule = fromJsonObject(array.optJSONObject(index), index) ?: continue
                    add(rule)
                }
            }

        private fun fromJsonObject(
            item: JSONObject?,
            index: Int
        ): RestrictionScheduleRule? {
            if (item == null) return null
            val startMinutes = parseTime(item.optString("start"))
            val endMinutes = parseTime(item.optString("end"))
            val days = parseDays(item.optJSONArray("days"))
            val mode = RestrictionMode.fromWireValue(item.optString("mode"))
            if (startMinutes == null || endMinutes == null || days.isEmpty() || mode == RestrictionMode.NONE) {
                return null
            }
            return RestrictionScheduleRule(
                id = item.optString("id", "rule-${index + 1}").ifBlank { "rule-${index + 1}" },
                enabled = item.optBoolean("enabled", true),
                days = days,
                startMinutes = startMinutes,
                endMinutes = endMinutes,
                mode = mode
            )
        }

        private fun parseDays(array: JSONArray?): Set<Int> =
            buildSet {
                if (array == null) return@buildSet
                for (index in 0 until array.length()) {
                    val day = array.optInt(index, -1)
                    if (day in 1..7) add(day)
                }
            }

        private fun parseTime(value: String): Int? {
            val parts = value.trim().split(":")
            if (parts.size != 2) return null
            val hours = parts[0].toIntOrNull() ?: return null
            val minutes = parts[1].toIntOrNull() ?: return null
            if (hours !in 0..23 || minutes !in 0..59) return null
            return hours * MINUTES_PER_HOUR + minutes
        }

        private fun minutesToTime(value: Int): String {
            val safeValue = max(0, value).coerceAtMost(MINUTES_PER_DAY - 1)
            return String.format(Locale.US, "%02d:%02d", safeValue / MINUTES_PER_HOUR, safeValue % MINUTES_PER_HOUR)
        }

        private fun Calendar.isoDayOfWeek(): Int =
            when (get(Calendar.DAY_OF_WEEK)) {
                Calendar.MONDAY -> 1
                Calendar.TUESDAY -> 2
                Calendar.WEDNESDAY -> 3
                Calendar.THURSDAY -> 4
                Calendar.FRIDAY -> 5
                Calendar.SATURDAY -> 6
                else -> 7
            }

        private fun Calendar.dayStartWithOffset(offsetDays: Int): Calendar =
            (clone() as Calendar).apply {
                add(Calendar.DAY_OF_YEAR, offsetDays)
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
    }
}
