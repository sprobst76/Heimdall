package de.heimdall.heimdall_child.agent

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.util.Log
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*

class MethodChannelHandler(
    private val context: Context,
    private val channel: MethodChannel
) : MethodChannel.MethodCallHandler {
    companion object {
        const val CHANNEL_NAME = "de.heimdall/agent"
        private const val TAG = "HeimdallBridge"
    }

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var communication: AgentCommunication? = null
    private var cache: OfflineRuleCache? = null
    private val ruleEvaluator = RuleEvaluator()
    private val totpValidator = TotpValidator()

    fun initialize() {
        communication = AgentCommunication(context)
        cache = OfflineRuleCache(context)
        channel.setMethodCallHandler(this)
        // Restore rules from cache on startup so blocking works immediately
        cache?.getCachedRules()?.let { ruleEvaluator.updateRules(it) }
        AppMonitorService.instance?.ruleEvaluator = ruleEvaluator
        wireWebSocketCallbacks()
        wireSyncCallback()
        wireMonitorCallbacks()
        Log.i(TAG, "Method channel handler initialized")
    }

    /**
     * Wire WebSocket callbacks: rule updates, block/unblock commands from backend
     * are applied immediately without waiting for next Flutter fetchRules call.
     */
    private fun wireWebSocketCallbacks() {
        val comm = communication ?: return

        comm.onRuleUpdate = { rules ->
            scope.launch(Dispatchers.Main) {
                cache?.cacheRules(rules)
                ruleEvaluator.updateRules(rules)
                AppMonitorService.instance?.let { monitor ->
                    monitor.ruleEvaluator = ruleEvaluator
                    monitor.reevaluateCurrentApp()
                }
                channel.invokeMethod("onRuleUpdate", mapOf("rules" to rules.toString()))
                Log.i(TAG, "Rule update applied via WebSocket")
            }
        }

        comm.onBlockApp = { groupId ->
            scope.launch(Dispatchers.Main) {
                AppMonitorService.instance?.blockedGroups?.add(groupId)
                // Show overlay immediately if current app is in this group
                val currentPkg = HeimdallAccessibilityService.currentPackage
                val currentGroup = AppMonitorService.instance?.appGroupMap?.get(currentPkg)
                if (currentGroup == groupId) {
                    val intent = Intent(context, BlockingOverlayService::class.java).apply {
                        putExtra("packageName", currentPkg)
                        putExtra("groupId", groupId)
                    }
                    context.startService(intent)
                }
                channel.invokeMethod("onGroupBlocked", mapOf("groupId" to groupId))
                Log.i(TAG, "Group blocked via WebSocket: $groupId")
            }
        }

        comm.onUnblockApp = { groupId ->
            scope.launch(Dispatchers.Main) {
                AppMonitorService.instance?.blockedGroups?.remove(groupId)
                BlockingOverlayService.instance?.hideBlock()
                AppMonitorService.instance?.reevaluateCurrentApp()
                channel.invokeMethod("onGroupUnblocked", mapOf("groupId" to groupId))
                Log.i(TAG, "Group unblocked via WebSocket: $groupId")
            }
        }

        comm.onConnected = {
            scope.launch(Dispatchers.IO) {
                // Fetch fresh rules immediately after reconnect
                val rules = communication?.fetchRules()
                if (rules != null) {
                    cache?.cacheRules(rules)
                    scope.launch(Dispatchers.Main) {
                        ruleEvaluator.updateRules(rules)
                        AppMonitorService.instance?.ruleEvaluator = ruleEvaluator
                        AppMonitorService.instance?.reevaluateCurrentApp()
                    }
                }
                Log.i(TAG, "WebSocket connected — rules refreshed")
            }
        }
    }

    /**
     * Wire AppMonitorService.onSyncNeeded → sends heartbeat + flushes queued events.
     * Also includes safe mode detection in the heartbeat payload.
     * Called every ~60s from the monitoring loop.
     */
    private fun wireSyncCallback() {
        AppMonitorService.instance?.onSyncNeeded = { activePackage ->
            scope.launch(Dispatchers.IO) {
                try {
                    val safe = isSafeMode()
                    communication?.sendHeartbeat(activePackage, safe)
                    if (safe) {
                        scope.launch(Dispatchers.Main) {
                            channel.invokeMethod("onSafeModeDetected", null)
                        }
                        Log.w(TAG, "Safe mode detected — reported to backend and Flutter")
                    }
                    flushPendingEvents()
                } catch (e: Exception) {
                    Log.w(TAG, "Sync failed: ${e.message}")
                }
            }
        }
    }

    /**
     * Wire AppMonitorService tamper and limit-warning callbacks.
     * Should be called after service start (with delay) and on initialize().
     */
    private fun wireMonitorCallbacks() {
        val monitor = AppMonitorService.instance ?: return

        monitor.onTamperDetected = { reason ->
            scope.launch(Dispatchers.IO) {
                try {
                    communication?.sendTamperAlert(reason)
                    Log.w(TAG, "Tamper alert sent: $reason")
                } catch (e: Exception) {
                    Log.w(TAG, "Tamper alert failed: ${e.message}")
                }
            }
            scope.launch(Dispatchers.Main) {
                channel.invokeMethod("onTamperDetected", mapOf("reason" to reason))
            }
        }

        monitor.onLimitWarning = { groupId, remainingMinutes ->
            scope.launch(Dispatchers.Main) {
                channel.invokeMethod("onLimitWarning", mapOf(
                    "groupId" to groupId,
                    "remainingMinutes" to remainingMinutes
                ))
                Log.i(TAG, "Limit warning sent to Flutter: group=$groupId remaining=${remainingMinutes}min")
            }
        }

        monitor.onVpnDetected = { reason ->
            scope.launch(Dispatchers.IO) {
                try {
                    communication?.sendTamperAlert("vpn_detected:$reason")
                    Log.w(TAG, "VPN/proxy tamper alert sent: $reason")
                } catch (e: Exception) {
                    Log.w(TAG, "VPN tamper alert failed: ${e.message}")
                }
            }
            scope.launch(Dispatchers.Main) {
                channel.invokeMethod("onVpnDetected", mapOf("reason" to reason))
            }
        }
    }

    /** Send all queued offline events to the backend. */
    private suspend fun flushPendingEvents() {
        val pending = cache?.getPendingEvents() ?: return
        if (pending.isEmpty()) return
        var synced = 0
        for (event in pending) {
            try {
                communication?.sendUsageEvent(
                    appPackage = event.optString("app_package").ifEmpty { null },
                    appGroupId = event.optString("app_group_id").ifEmpty { null },
                    eventType = event.getString("event_type"),
                    startedAt = event.optString("started_at").ifEmpty { null },
                    endedAt = event.optString("ended_at").ifEmpty { null },
                    durationSeconds = if (event.has("duration_seconds")) event.getInt("duration_seconds") else null
                )
                synced++
            } catch (e: Exception) {
                Log.w(TAG, "Failed to flush event: ${e.message}")
                break  // Stop on first error; retry next sync cycle
            }
        }
        if (synced > 0) {
            cache?.removeSyncedEvents(synced)
            Log.i(TAG, "Flushed $synced pending events")
        }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "startMonitoring" -> {
                val intent = Intent(context, AppMonitorService::class.java)
                context.startForegroundService(intent)
                // Wire evaluator + callbacks after service starts
                scope.launch {
                    kotlinx.coroutines.delay(500)
                    AppMonitorService.instance?.ruleEvaluator = ruleEvaluator
                    wireSyncCallback()
                    wireMonitorCallbacks()
                }
                // Connect WebSocket for real-time rule updates
                if (communication?.isRegistered == true) {
                    communication?.connectWebSocket()
                }
                // Schedule periodic rule sync (2h ±1h, network required)
                WorkManagerScheduler.scheduleRuleSync(context)
                result.success(true)
            }
            "stopMonitoring" -> {
                val intent = Intent(context, AppMonitorService::class.java)
                context.stopService(intent)
                WorkManagerScheduler.cancelRuleSync(context)
                result.success(true)
            }
            "checkPermissions" -> {
                val permissions = mapOf(
                    "accessibility" to isAccessibilityEnabled(),
                    "usageStats" to isUsageStatsGranted(),
                    "deviceAdmin" to isDeviceAdminActive(),
                    "overlay" to Settings.canDrawOverlays(context),
                    "notification" to true,  // Always true for Android 8+
                    "safeMode" to isSafeMode()
                )
                result.success(permissions)
            }
            "requestAccessibility" -> {
                val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                result.success(true)
            }
            "requestUsageStats" -> {
                val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                result.success(true)
            }
            "requestDeviceAdmin" -> {
                val component = ComponentName(context, HeimdallDeviceAdminReceiver::class.java)
                val intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                    putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, component)
                    putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                        "Heimdall benötigt Geräte-Admin-Rechte zum Schutz vor Deinstallation.")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                result.success(true)
            }
            "requestOverlay" -> {
                val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                result.success(true)
            }
            "configure" -> {
                val serverUrl = call.argument<String>("serverUrl") ?: ""
                val deviceToken = call.argument<String>("deviceToken") ?: ""
                val deviceId = call.argument<String>("deviceId") ?: ""
                communication?.configure(serverUrl, deviceToken, deviceId)
                result.success(true)
            }
            "getUsageToday" -> {
                val usage = AppMonitorService.instance?.getUsageTodayByGroup() ?: emptyMap()
                // Convert seconds to minutes
                val minutes = usage.mapValues { (it.value / 60).toInt() }
                result.success(minutes)
            }
            "fetchRules" -> {
                scope.launch {
                    try {
                        val rules = communication?.fetchRules()
                        if (rules != null) {
                            cache?.cacheRules(rules)
                            ruleEvaluator.updateRules(rules)
                            AppMonitorService.instance?.ruleEvaluator = ruleEvaluator
                            result.success(rules.toString())
                        } else {
                            val cached = cache?.getCachedRules()
                            if (cached != null) {
                                ruleEvaluator.updateRules(cached)
                                AppMonitorService.instance?.ruleEvaluator = ruleEvaluator
                            }
                            result.success(cached?.toString())
                        }
                    } catch (e: Exception) {
                        result.error("FETCH_ERROR", e.message, null)
                    }
                }
            }
            "sendHeartbeat" -> {
                scope.launch {
                    try {
                        val resp = communication?.sendHeartbeat(
                            HeimdallAccessibilityService.currentPackage.ifEmpty { null }
                        )
                        result.success(resp?.toString())
                    } catch (e: Exception) {
                        result.error("HEARTBEAT_ERROR", e.message, null)
                    }
                }
            }
            "blockGroup" -> {
                val groupId = call.argument<String>("groupId") ?: ""
                AppMonitorService.instance?.blockedGroups?.add(groupId)
                // Check if current foreground app is in this group → show overlay immediately
                val currentPkg = HeimdallAccessibilityService.currentPackage
                val currentGroup = AppMonitorService.instance?.appGroupMap?.get(currentPkg)
                if (currentGroup == groupId) {
                    val intent = Intent(context, BlockingOverlayService::class.java).apply {
                        putExtra("packageName", currentPkg)
                        putExtra("groupId", groupId)
                    }
                    context.startService(intent)
                }
                result.success(true)
            }
            "unblockGroup" -> {
                val groupId = call.argument<String>("groupId") ?: ""
                AppMonitorService.instance?.blockedGroups?.remove(groupId)
                // Hide overlay if the currently blocked app belongs to this group
                BlockingOverlayService.instance?.hideBlock()
                result.success(true)
            }
            "showBlockOverlay" -> {
                val packageName = call.argument<String>("packageName") ?: ""
                val groupId = call.argument<String>("groupId") ?: ""
                val intent = Intent(context, BlockingOverlayService::class.java).apply {
                    putExtra("packageName", packageName)
                    putExtra("groupId", groupId)
                }
                context.startService(intent)
                result.success(true)
            }
            "hideBlockOverlay" -> {
                BlockingOverlayService.instance?.hideBlock()
                result.success(true)
            }
            "isMonitoringActive" -> {
                result.success(AppMonitorService.instance != null)
            }
            "isAccessibilityActive" -> {
                result.success(HeimdallAccessibilityService.instance != null)
            }
            // Returns remaining minutes for a group (or device-wide if no groupId given)
            "getRemainingMinutes" -> {
                val groupId = call.argument<String>("groupId")
                val usage = AppMonitorService.instance?.getUsageTodayByGroup() ?: emptyMap()
                // Convert map from seconds (Long) — getUsageTodayByGroup returns Long values
                val usageLong = usage.mapValues { it.value }
                val remaining = if (groupId != null) {
                    ruleEvaluator.getRemainingMinutesForGroup(groupId, usageLong)
                } else {
                    ruleEvaluator.getRemainingDeviceMinutes(usageLong.values.sum())
                }
                result.success(remaining)
            }
            // Evaluate all rules against current usage and update blocked groups accordingly
            "applyRules" -> {
                val monitor = AppMonitorService.instance
                if (monitor != null) {
                    val usage = monitor.getUsageTodayByGroup()
                    val exceeded = ruleEvaluator.getGroupsExceedingLimit(usage)
                    val timeAllowed = ruleEvaluator.isDeviceAllowedByTimeWindow()
                    // Groups to block = manually blocked + rule-exceeded
                    // We don't touch manually blocked groups here, just add exceeded ones
                    exceeded.forEach { monitor.blockedGroups.add(it) }
                    result.success(mapOf(
                        "timeAllowed" to timeAllowed,
                        "groupsBlocked" to exceeded.toList()
                    ))
                } else {
                    result.success(mapOf("timeAllowed" to true, "groupsBlocked" to emptyList<String>()))
                }
            }
            "updateAppGroupMap" -> {
                val map = call.argument<Map<String, String>>("map") ?: emptyMap()
                AppMonitorService.instance?.appGroupMap = map
                cache?.cacheAppGroupMap(map)
                result.success(true)
            }
            // Validate a 6-digit TOTP code offline using the cached totp_config.secret
            "validateTotpOffline" -> {
                val code = call.argument<String>("code") ?: ""
                val rules = cache?.getCachedRules()
                val totpConfig = rules?.optJSONObject("totp_config")
                val secret = totpConfig?.optString("secret") ?: ""
                if (secret.isEmpty()) {
                    result.success(mapOf("valid" to false, "reason" to "no_totp_config"))
                } else {
                    val valid = totpValidator.validate(code, secret)
                    val overrideMinutes = totpConfig?.optInt("override_minutes", 30) ?: 30
                    result.success(mapOf(
                        "valid" to valid,
                        "override_minutes" to overrideMinutes,
                        "seconds_remaining" to totpValidator.secondsRemaining()
                    ))
                    Log.i(TAG, "TOTP offline validation: valid=$valid")
                }
            }
            // Connect (or reconnect) WebSocket explicitly from Flutter
            "connectWebSocket" -> {
                if (communication?.isRegistered == true) {
                    communication?.connectWebSocket()
                    result.success(true)
                } else {
                    result.error("NOT_CONFIGURED", "Device token not set", null)
                }
            }
            else -> result.notImplemented()
        }
    }

    private fun isAccessibilityEnabled(): Boolean {
        return HeimdallAccessibilityService.instance != null
    }

    private fun isUsageStatsGranted(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as android.app.AppOpsManager
        val mode = appOps.unsafeCheckOpNoThrow(
            android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
            android.os.Process.myUid(),
            context.packageName
        )
        return mode == android.app.AppOpsManager.MODE_ALLOWED
    }

    private fun isDeviceAdminActive(): Boolean {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val component = ComponentName(context, HeimdallDeviceAdminReceiver::class.java)
        return dpm.isAdminActive(component)
    }

    /**
     * Returns true if the device is booted in Safe Mode.
     * In Safe Mode, third-party services (including Accessibility) are disabled,
     * so Heimdall cannot enforce rules. The parent app should be notified.
     */
    private fun isSafeMode(): Boolean {
        return try {
            context.packageManager.isSafeMode
        } catch (e: Exception) {
            false
        }
    }

    fun notifyAppChanged(packageName: String) {
        scope.launch {
            channel.invokeMethod("onAppChanged", mapOf("packageName" to packageName))
        }
    }

    fun notifyBlockTriggered(packageName: String, groupId: String) {
        scope.launch {
            channel.invokeMethod("onBlockTriggered", mapOf(
                "packageName" to packageName,
                "groupId" to groupId
            ))
        }
    }

    fun destroy() {
        communication?.destroy()
        scope.cancel()
    }
}
