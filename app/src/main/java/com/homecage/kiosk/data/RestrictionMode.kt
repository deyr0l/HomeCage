package com.homecage.kiosk.data

enum class RestrictionMode(val wireValue: String) {
    NONE("none"),
    PARENTAL("parental"),
    LOST("lost");

    val priority: Int
        get() = when (this) {
            NONE -> 0
            PARENTAL -> 1
            LOST -> 2
        }

    val blocksAppLaunches: Boolean
        get() = this != NONE

    companion object {
        fun strongest(left: RestrictionMode, right: RestrictionMode): RestrictionMode =
            if (left.priority >= right.priority) left else right

        fun fromWireValue(value: String?): RestrictionMode =
            when (value?.trim()?.lowercase()) {
                "parental", "parental_lock", "parental-lock", "parentalrestriction" -> PARENTAL
                "lost", "lost_phone", "lost-phone", "lockdown" -> LOST
                else -> NONE
            }
    }
}
