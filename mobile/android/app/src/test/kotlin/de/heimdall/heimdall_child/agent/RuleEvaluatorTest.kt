package de.heimdall.heimdall_child.agent

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Unit tests for RuleEvaluator.
 * Tests time-window enforcement and daily-limit enforcement logic.
 *
 * Note: Tests that depend on LocalTime.now() use time windows that are
 * guaranteed to include or exclude the current time by being very wide
 * or by constructing dynamic windows.
 */
class RuleEvaluatorTest {

    private lateinit var evaluator: RuleEvaluator

    @Before
    fun setUp() {
        evaluator = RuleEvaluator()
    }

    // -- Time window helpers --

    private fun makeRules(
        timeWindows: List<Pair<String, String>> = emptyList(),
        groupLimits: List<Triple<String, Int, Int>> = emptyList(),  // (groupId, maxMinutes, usedMinutes)
        dailyLimitMinutes: Int? = null,
        remainingMinutes: Int? = null
    ): JSONObject {
        val rules = JSONObject()
        rules.put("day_type", "weekday")

        val windowsArray = JSONArray()
        for ((start, end) in timeWindows) {
            windowsArray.put(JSONObject().put("start", start).put("end", end))
        }
        rules.put("time_windows", windowsArray)

        val limitsArray = JSONArray()
        for ((groupId, maxMinutes, _) in groupLimits) {
            limitsArray.put(JSONObject().put("group_id", groupId).put("max_minutes", maxMinutes))
        }
        rules.put("group_limits", limitsArray)

        if (dailyLimitMinutes != null) rules.put("daily_limit_minutes", dailyLimitMinutes)
        if (remainingMinutes != null) rules.put("remaining_minutes", remainingMinutes)

        return rules
    }

    private fun usageMap(vararg entries: Pair<String, Long>): Map<String, Long> =
        entries.toMap()

    // -- Tests: no rules --

    @Test
    fun `no rules - device always allowed`() {
        assertTrue(evaluator.isDeviceAllowedByTimeWindow())
    }

    @Test
    fun `no rules - group always allowed`() {
        assertTrue(evaluator.isGroupAllowedNow("gaming", emptyMap()))
    }

    @Test
    fun `no rules - remaining minutes is null`() {
        assertNull(evaluator.getRemainingDeviceMinutes(0L))
    }

    // -- Tests: time windows --

    @Test
    fun `empty time_windows array - device always allowed`() {
        evaluator.updateRules(makeRules(timeWindows = emptyList()))
        assertTrue(evaluator.isDeviceAllowedByTimeWindow())
    }

    @Test
    fun `time window covering full day - device allowed`() {
        evaluator.updateRules(makeRules(timeWindows = listOf("00:00" to "23:59")))
        assertTrue(evaluator.isDeviceAllowedByTimeWindow())
    }

    @Test
    fun `time window in the past (before any real time) - device blocked`() {
        // 00:00–00:01 will almost certainly exclude current time unless test runs at midnight
        // Use a more robust approach: a tiny window in the past
        val now = LocalTime.now()
        val start = now.minusHours(3).format(DateTimeFormatter.ofPattern("HH:mm"))
        val end = now.minusHours(2).format(DateTimeFormatter.ofPattern("HH:mm"))
        evaluator.updateRules(makeRules(timeWindows = listOf(start to end)))
        // Current time is 3h after end, so outside the window
        assertFalse("Should be blocked outside time window", evaluator.isDeviceAllowedByTimeWindow())
    }

    @Test
    fun `time window currently active - device allowed`() {
        val now = LocalTime.now()
        val start = now.minusHours(1).format(DateTimeFormatter.ofPattern("HH:mm"))
        val end = now.plusHours(1).format(DateTimeFormatter.ofPattern("HH:mm"))
        evaluator.updateRules(makeRules(timeWindows = listOf(start to end)))
        assertTrue("Should be allowed within time window", evaluator.isDeviceAllowedByTimeWindow())
    }

    // -- Tests: daily limits --

    @Test
    fun `daily limit not exceeded - device allowed`() {
        evaluator.updateRules(makeRules(remainingMinutes = 60))
        val remaining = evaluator.getRemainingDeviceMinutes(0L)
        assertEquals(60, remaining)
        // 0 seconds used locally → remaining is full
        assertTrue(evaluator.isGroupAllowedNow("gaming", emptyMap()))
    }

    @Test
    fun `daily limit exhausted from backend - device blocked`() {
        evaluator.updateRules(makeRules(remainingMinutes = 0))
        val remaining = evaluator.getRemainingDeviceMinutes(0L)
        assertEquals(0, remaining)
        assertFalse(evaluator.isGroupAllowedNow("gaming", emptyMap()))
    }

    @Test
    fun `daily limit partially consumed by local usage`() {
        evaluator.updateRules(makeRules(remainingMinutes = 30))
        // 20 minutes used locally since last sync
        val remaining = evaluator.getRemainingDeviceMinutes(20 * 60L)
        assertEquals(10, remaining)
    }

    @Test
    fun `local usage exceeds backend remaining - clamps to 0`() {
        evaluator.updateRules(makeRules(remainingMinutes = 10))
        val remaining = evaluator.getRemainingDeviceMinutes(30 * 60L)
        assertEquals(0, remaining)
    }

    // -- Tests: group limits --

    @Test
    fun `group limit not exceeded - group allowed`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0))
        ))
        assertTrue(evaluator.isGroupAllowedByLimit("gaming", 30 * 60L))
    }

    @Test
    fun `group limit exactly reached - group blocked`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0))
        ))
        assertFalse(evaluator.isGroupAllowedByLimit("gaming", 60 * 60L))
    }

    @Test
    fun `group limit exceeded - group blocked`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0))
        ))
        assertFalse(evaluator.isGroupAllowedByLimit("gaming", 90 * 60L))
    }

    @Test
    fun `group with no limit - always allowed`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("social", 30, 0))
        ))
        // 'gaming' has no limit entry → always allowed
        assertTrue(evaluator.isGroupAllowedByLimit("gaming", 999 * 60L))
    }

    // -- Tests: getGroupsExceedingLimit --

    @Test
    fun `no groups exceed limit`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0))
        ))
        val exceeded = evaluator.getGroupsExceedingLimit(usageMap("gaming" to 30 * 60L))
        assertTrue(exceeded.isEmpty())
    }

    @Test
    fun `one group exceeds limit`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(
                Triple("gaming", 60, 0),
                Triple("social", 30, 0)
            )
        ))
        val exceeded = evaluator.getGroupsExceedingLimit(
            usageMap("gaming" to 90 * 60L, "social" to 10 * 60L)
        )
        assertEquals(setOf("gaming"), exceeded)
    }

    @Test
    fun `multiple groups exceed limit`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(
                Triple("gaming", 60, 0),
                Triple("social", 30, 0)
            )
        ))
        val exceeded = evaluator.getGroupsExceedingLimit(
            usageMap("gaming" to 90 * 60L, "social" to 45 * 60L)
        )
        assertEquals(setOf("gaming", "social"), exceeded)
    }

    // -- Tests: getRemainingMinutesForGroup --

    @Test
    fun `remaining for group with group limit only`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0))
        ))
        val remaining = evaluator.getRemainingMinutesForGroup("gaming", usageMap("gaming" to 20 * 60L))
        assertEquals(40, remaining)
    }

    @Test
    fun `remaining for group takes min of group and device limit`() {
        evaluator.updateRules(makeRules(
            groupLimits = listOf(Triple("gaming", 60, 0)),
            remainingMinutes = 15
        ))
        // Group has 40 min left, device has 15 min left → min = 15
        val remaining = evaluator.getRemainingMinutesForGroup("gaming", usageMap("gaming" to 20 * 60L))
        assertEquals(15, remaining)
    }

    @Test
    fun `remaining for group with no limits - null`() {
        evaluator.updateRules(makeRules())
        assertNull(evaluator.getRemainingMinutesForGroup("gaming", emptyMap()))
    }

    // -- Tests: clearRules --

    @Test
    fun `clear rules - hasRules becomes false`() {
        evaluator.updateRules(makeRules(timeWindows = listOf("00:00" to "23:59")))
        assertTrue(evaluator.hasRules)
        evaluator.clearRules()
        assertFalse(evaluator.hasRules)
    }

    @Test
    fun `after clear - everything allowed again`() {
        evaluator.updateRules(makeRules(remainingMinutes = 0))
        assertFalse(evaluator.isGroupAllowedNow("gaming", emptyMap()))
        evaluator.clearRules()
        assertTrue(evaluator.isGroupAllowedNow("gaming", emptyMap()))
    }
}
