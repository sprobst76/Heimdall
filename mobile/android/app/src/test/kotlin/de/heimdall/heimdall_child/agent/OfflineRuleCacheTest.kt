package de.heimdall.heimdall_child.agent

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class OfflineRuleCacheTest {

    private lateinit var cache: OfflineRuleCache

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        cache = OfflineRuleCache(context)
        cache.clearPendingEvents()
    }

    @Test
    fun test_getCachedRules_empty() {
        assertNull(cache.getCachedRules())
    }

    @Test
    fun test_cacheRules_and_getCachedRules() {
        val rules = JSONObject().apply {
            put("daily_limit_minutes", 120)
            put("day_type", "weekday")
        }
        cache.cacheRules(rules)

        val cached = cache.getCachedRules()
        assertNotNull(cached)
        assertEquals(120, cached!!.getInt("daily_limit_minutes"))
        assertEquals("weekday", cached.getString("day_type"))
    }

    @Test
    fun test_cacheAppGroupMap_and_get() {
        val map = mapOf("com.chrome" to "browser-group", "com.minecraft" to "games-group")
        cache.cacheAppGroupMap(map)

        val result = cache.getAppGroupMap()
        assertEquals(2, result.size)
        assertEquals("browser-group", result["com.chrome"])
        assertEquals("games-group", result["com.minecraft"])
    }

    @Test
    fun test_getAppGroupMap_empty() {
        val result = cache.getAppGroupMap()
        assertTrue(result.isEmpty())
    }

    @Test
    fun test_queueEvent_and_getPendingEvents() {
        val event = JSONObject().apply {
            put("type", "usage_event")
            put("app", "chrome")
        }
        cache.queueEvent(event)

        val events = cache.getPendingEvents()
        assertEquals(1, events.size)
        assertEquals("chrome", events[0].getString("app"))
    }

    @Test
    fun test_removeSyncedEvents() {
        for (i in 1..5) {
            cache.queueEvent(JSONObject().apply { put("i", i) })
        }
        assertEquals(5, cache.pendingCount)

        cache.removeSyncedEvents(3)

        val remaining = cache.getPendingEvents()
        assertEquals(2, remaining.size)
        assertEquals(4, remaining[0].getInt("i"))
        assertEquals(5, remaining[1].getInt("i"))
    }

    @Test
    fun test_clearPendingEvents() {
        cache.queueEvent(JSONObject().apply { put("x", 1) })
        cache.queueEvent(JSONObject().apply { put("x", 2) })
        assertEquals(2, cache.pendingCount)

        cache.clearPendingEvents()
        assertEquals(0, cache.pendingCount)
    }

    @Test
    fun test_pendingCount() {
        assertEquals(0, cache.pendingCount)
        cache.queueEvent(JSONObject().apply { put("a", 1) })
        assertEquals(1, cache.pendingCount)
        cache.queueEvent(JSONObject().apply { put("b", 2) })
        assertEquals(2, cache.pendingCount)
    }
}
