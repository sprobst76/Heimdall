package de.heimdall.heimdall_child.agent

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

class OfflineRuleCache(context: Context) {
    companion object {
        private const val TAG = "HeimdallCache"
        private const val PREFS_RULES = "heimdall_rules_cache"
        private const val PREFS_EVENTS = "heimdall_events_queue"
        private const val KEY_RULES = "cached_rules"
        private const val KEY_RULES_UPDATED = "rules_updated_at"
        private const val KEY_EVENTS = "pending_events"
        private const val KEY_APP_GROUP_MAP = "app_group_map"
    }

    private val rulesPrefs: SharedPreferences = context.getSharedPreferences(PREFS_RULES, Context.MODE_PRIVATE)
    private val eventsPrefs: SharedPreferences = context.getSharedPreferences(PREFS_EVENTS, Context.MODE_PRIVATE)

    // -- Rules cache --

    fun cacheRules(rules: JSONObject) {
        rulesPrefs.edit()
            .putString(KEY_RULES, rules.toString())
            .putString(KEY_RULES_UPDATED, Instant.now().toString())
            .apply()
        Log.d(TAG, "Rules cached")
    }

    fun getCachedRules(): JSONObject? {
        val json = rulesPrefs.getString(KEY_RULES, null) ?: return null
        return try { JSONObject(json) } catch (e: Exception) { null }
    }

    // -- App group map (packageName -> groupId) --

    fun cacheAppGroupMap(map: Map<String, String>) {
        val json = JSONObject(map as Map<*, *>).toString()
        rulesPrefs.edit().putString(KEY_APP_GROUP_MAP, json).apply()
    }

    fun getAppGroupMap(): Map<String, String> {
        val json = rulesPrefs.getString(KEY_APP_GROUP_MAP, null) ?: return emptyMap()
        return try {
            val obj = JSONObject(json)
            val map = mutableMapOf<String, String>()
            obj.keys().forEach { key -> map[key] = obj.getString(key) }
            map
        } catch (e: Exception) { emptyMap() }
    }

    // -- Event queue --

    fun queueEvent(event: JSONObject) {
        val events = getPendingEventsRaw()
        events.put(event)
        eventsPrefs.edit().putString(KEY_EVENTS, events.toString()).apply()
        Log.d(TAG, "Event queued (total: ${events.length()})")
    }

    fun getPendingEvents(): List<JSONObject> {
        val arr = getPendingEventsRaw()
        return (0 until arr.length()).map { arr.getJSONObject(it) }
    }

    fun clearPendingEvents() {
        eventsPrefs.edit().putString(KEY_EVENTS, "[]").apply()
    }

    fun removeSyncedEvents(count: Int) {
        val arr = getPendingEventsRaw()
        if (count >= arr.length()) {
            clearPendingEvents()
            return
        }
        val remaining = JSONArray()
        for (i in count until arr.length()) {
            remaining.put(arr.getJSONObject(i))
        }
        eventsPrefs.edit().putString(KEY_EVENTS, remaining.toString()).apply()
    }

    val pendingCount: Int get() = getPendingEventsRaw().length()

    private fun getPendingEventsRaw(): JSONArray {
        val json = eventsPrefs.getString(KEY_EVENTS, "[]") ?: "[]"
        return try { JSONArray(json) } catch (e: Exception) { JSONArray() }
    }
}
