package de.heimdall.heimdall_child.agent

import android.util.Log
import org.json.JSONObject
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Evaluates cached rules from the backend to determine if app groups are allowed.
 *
 * Handles:
 * - Time-window enforcement (device-wide allowed hours)
 * - Daily limit enforcement (overall device limit + per-group limit)
 * - Active TAN overrides
 */
class RuleEvaluator {
    companion object {
        private const val TAG = "HeimdallRules"
        private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    }

    private var currentRules: JSONObject? = null

    /** Update evaluator with fresh rules from backend or cache. */
    fun updateRules(rules: JSONObject) {
        currentRules = rules
        Log.d(TAG, "Rules updated: day_type=${rules.optString("day_type")}, " +
                "windows=${rules.optJSONArray("time_windows")?.length() ?: 0}, " +
                "daily_limit=${rules.optInt("daily_limit_minutes", -1)}")
    }

    /** Clear rules (e.g. on logout or rule fetch error). */
    fun clearRules() {
        currentRules = null
    }

    /**
     * Returns true if the current local time falls within any configured time window,
     * or if no time windows are configured (= no time restriction).
     */
    fun isDeviceAllowedByTimeWindow(): Boolean {
        val rules = currentRules ?: return true
        val windows = rules.optJSONArray("time_windows") ?: return true
        if (windows.length() == 0) return true

        val now = LocalTime.now()
        for (i in 0 until windows.length()) {
            val window = windows.getJSONObject(i)
            val start = LocalTime.parse(window.getString("start"), TIME_FMT)
            val end = LocalTime.parse(window.getString("end"), TIME_FMT)
            if (isTimeInWindow(now, start, end)) return true
        }
        Log.i(TAG, "Device blocked by time window (now=$now)")
        return false
    }

    /**
     * Returns the number of minutes remaining for overall device use today,
     * adjusted by local in-memory usage accumulated since last rule sync.
     * Returns null if no overall daily limit is configured.
     */
    fun getRemainingDeviceMinutes(totalUsedSeconds: Long): Int? {
        val rules = currentRules ?: return null
        if (rules.isNull("remaining_minutes")) return null
        val backendRemaining = rules.getInt("remaining_minutes")
        // Subtract local usage accumulated since last sync from backend
        val localUsedMinutesSinceSync = (totalUsedSeconds / 60).toInt()
        return maxOf(0, backendRemaining - localUsedMinutesSinceSync)
    }

    /**
     * Returns true if the specific app group still has time remaining within
     * its per-group daily limit, or if no limit is configured for the group.
     */
    fun isGroupAllowedByLimit(groupId: String, groupUsedSeconds: Long): Boolean {
        val rules = currentRules ?: return true
        val limits = rules.optJSONArray("group_limits") ?: return true

        for (i in 0 until limits.length()) {
            val limit = limits.getJSONObject(i)
            if (limit.getString("group_id") == groupId) {
                val maxMinutes = limit.getInt("max_minutes")
                val usedMinutes = (groupUsedSeconds / 60).toInt()
                if (usedMinutes >= maxMinutes) {
                    Log.i(TAG, "Group $groupId exceeded limit: ${usedMinutes}/${maxMinutes} min")
                    return false
                }
                return true
            }
        }
        return true  // No limit defined for this group
    }

    /**
     * Complete check for a specific app group:
     * 1. Device time window (is it allowed hours now?)
     * 2. Overall device daily limit (is general budget exhausted?)
     * 3. Per-group daily limit (is this group's budget exhausted?)
     *
     * Returns true if the group is allowed, false if it should be blocked.
     */
    fun isGroupAllowedNow(groupId: String, usageByGroup: Map<String, Long>): Boolean {
        if (!isDeviceAllowedByTimeWindow()) return false

        val totalUsedSeconds = usageByGroup.values.sum()
        val remaining = getRemainingDeviceMinutes(totalUsedSeconds)
        if (remaining != null && remaining <= 0) {
            Log.i(TAG, "Device daily limit exhausted")
            return false
        }

        val groupUsed = usageByGroup[groupId] ?: 0L
        return isGroupAllowedByLimit(groupId, groupUsed)
    }

    /**
     * Returns the set of group IDs that have exceeded their per-group daily limit.
     * Used for bulk evaluation after usage updates.
     */
    fun getGroupsExceedingLimit(usageByGroup: Map<String, Long>): Set<String> {
        val rules = currentRules ?: return emptySet()
        val limits = rules.optJSONArray("group_limits") ?: return emptySet()
        val exceeded = mutableSetOf<String>()
        for (i in 0 until limits.length()) {
            val limit = limits.getJSONObject(i)
            val groupId = limit.getString("group_id")
            val maxMinutes = limit.getInt("max_minutes")
            val usedMinutes = ((usageByGroup[groupId] ?: 0L) / 60).toInt()
            if (usedMinutes >= maxMinutes) exceeded.add(groupId)
        }
        return exceeded
    }

    /**
     * Returns the remaining minutes for a specific group, considering both
     * the per-group limit and the overall device limit (takes the minimum).
     * Returns null if neither limit is configured.
     */
    fun getRemainingMinutesForGroup(groupId: String, usageByGroup: Map<String, Long>): Int? {
        var groupRemaining: Int? = null
        val limits = currentRules?.optJSONArray("group_limits")
        if (limits != null) {
            for (i in 0 until limits.length()) {
                val limit = limits.getJSONObject(i)
                if (limit.getString("group_id") == groupId) {
                    val maxMinutes = limit.getInt("max_minutes")
                    val usedMinutes = ((usageByGroup[groupId] ?: 0L) / 60).toInt()
                    groupRemaining = maxOf(0, maxMinutes - usedMinutes)
                    break
                }
            }
        }
        val deviceRemaining = getRemainingDeviceMinutes(usageByGroup.values.sum())
        return when {
            groupRemaining != null && deviceRemaining != null -> minOf(groupRemaining, deviceRemaining)
            groupRemaining != null -> groupRemaining
            deviceRemaining != null -> deviceRemaining
            else -> null
        }
    }

    /** True if any rules are loaded. */
    val hasRules: Boolean get() = currentRules != null

    private fun isTimeInWindow(now: LocalTime, start: LocalTime, end: LocalTime): Boolean {
        return if (end.isAfter(start)) {
            // Normal window e.g. 14:00–22:00
            !now.isBefore(start) && !now.isAfter(end)
        } else {
            // Overnight window e.g. 22:00–06:00
            !now.isBefore(start) || !now.isAfter(end)
        }
    }
}
