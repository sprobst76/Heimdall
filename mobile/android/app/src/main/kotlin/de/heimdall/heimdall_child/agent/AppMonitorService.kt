package de.heimdall.heimdall_child.agent

import android.app.*
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import de.heimdall.heimdall_child.R
import kotlinx.coroutines.*
import java.util.concurrent.TimeUnit

// Re-evaluation interval for time-window transitions (e.g. 14:00 → allowed)
private const val RULE_EVAL_INTERVAL_MS = 60_000L

class AppMonitorService : Service() {
    companion object {
        private const val TAG = "HeimdallMonitor"
        private const val CHANNEL_ID = "heimdall_monitor"
        private const val NOTIFICATION_ID = 1001
        private const val POLL_INTERVAL_MS = 2000L

        var instance: AppMonitorService? = null
            private set
    }

    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var monitorJob: Job? = null
    private var currentForegroundPackage: String = ""

    // Track usage time per app group: groupId -> accumulated seconds today
    val usageByGroup = mutableMapOf<String, Long>()
    // Track current session start
    private var sessionStart: Long = 0L
    private var sessionPackage: String = ""

    // Rule evaluator for time-window and daily-limit enforcement
    var ruleEvaluator: RuleEvaluator? = null

    // Callbacks
    var onAppChanged: ((oldPkg: String, newPkg: String) -> Unit)? = null
    var appGroupMap: Map<String, String> = emptyMap()  // packageName -> groupId
    var blockedGroups: MutableSet<String> = mutableSetOf()  // manually blocked groups
    var onBlockTriggered: ((packageName: String, groupId: String) -> Unit)? = null
    /** Called every ~60s by the monitoring loop. Used by MethodChannelHandler to send heartbeats. */
    var onSyncNeeded: (suspend (activePackage: String?) -> Unit)? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        // Register for instant A11y notifications (much faster than polling)
        HeimdallAccessibilityService.onAppChanged = { pkg ->
            handleForegroundChange(pkg)
        }
        startMonitoring()
        Log.i(TAG, "Monitor service created")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY // Restart if killed
    }

    override fun onDestroy() {
        monitorJob?.cancel()
        scope.cancel()
        HeimdallAccessibilityService.onAppChanged = null
        instance = null
        super.onDestroy()
        Log.i(TAG, "Monitor service destroyed")
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            resources.getString(R.string.monitor_channel_name),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = resources.getString(R.string.monitor_channel_description)
            setShowBadge(false)
        }
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val intent = packageManager.getLaunchIntentForPackage(packageName)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Heimdall aktiv")
            .setContentText("Bildschirmzeit wird überwacht")
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .build()
    }

    /**
     * Called both from A11y callback (instant) and from polling (fallback).
     * Handles session tracking and blocking logic.
     */
    fun handleForegroundChange(pkg: String) {
        if (pkg == currentForegroundPackage) return
        // Ignore our own package — overlay triggers A11y events
        if (pkg == packageName) return

        val oldPkg = currentForegroundPackage
        // Close old session
        if (sessionPackage.isNotEmpty()) {
            recordSessionEnd()
        }
        // Start new session
        currentForegroundPackage = pkg
        sessionPackage = pkg
        sessionStart = System.currentTimeMillis()

        Log.d(TAG, "Foreground: $oldPkg -> $pkg")
        onAppChanged?.invoke(oldPkg, pkg)

        // Check if blocked (manual block OR rule-based block)
        val groupId = appGroupMap[pkg]
        val shouldBlock = when {
            // 1. Manually blocked group (e.g. via parent action)
            groupId != null && blockedGroups.contains(groupId) -> true
            // 2. Rule-based: time window or daily limit exceeded
            groupId != null && ruleEvaluator?.isGroupAllowedNow(groupId, usageByGroup) == false -> true
            // 3. No group mapping but device time window violated → block all unknown apps
            groupId == null && ruleEvaluator?.isDeviceAllowedByTimeWindow() == false -> true
            else -> false
        }
        if (shouldBlock) {
            val blockGroup = groupId ?: "device"
            Log.i(TAG, "Blocking app: $pkg (group: $blockGroup)")
            onBlockTriggered?.invoke(pkg, blockGroup)
            showBlockingOverlay(pkg, blockGroup)
        } else {
            hideBlockingOverlay()
        }
    }

    private fun startMonitoring() {
        monitorJob = scope.launch {
            var lastRuleEvalAt = 0L
            while (isActive) {
                // Polling as fallback — primary detection is via A11y callback
                val pkg = detectForegroundApp()
                if (pkg != null) {
                    handleForegroundChange(pkg)
                }

                // Periodic rule re-evaluation + heartbeat sync
                val now = System.currentTimeMillis()
                if (now - lastRuleEvalAt >= RULE_EVAL_INTERVAL_MS) {
                    lastRuleEvalAt = now
                    reevaluateCurrentApp()
                    // Notify MethodChannelHandler to send heartbeat + flush events
                    val activePkg = currentForegroundPackage.ifEmpty { null }
                    onSyncNeeded?.invoke(activePkg)
                }

                delay(POLL_INTERVAL_MS)
            }
        }
    }

    /**
     * Re-check the currently active app against rules without a foreground change.
     * Handles cases like: blocked hours start while the same app is in the foreground,
     * or a daily limit is hit during a long session.
     */
    internal fun reevaluateCurrentApp() {
        val pkg = currentForegroundPackage
        if (pkg.isEmpty()) return
        val groupId = appGroupMap[pkg]
        val alreadyBlocked = BlockingOverlayService.instance?.isShowing == true
        val shouldBlock = when {
            groupId != null && blockedGroups.contains(groupId) -> true
            groupId != null && ruleEvaluator?.isGroupAllowedNow(groupId, usageByGroup) == false -> true
            groupId == null && ruleEvaluator?.isDeviceAllowedByTimeWindow() == false -> true
            else -> false
        }
        if (shouldBlock && !alreadyBlocked) {
            val blockGroup = groupId ?: "device"
            Log.i(TAG, "Rule re-eval blocked: $pkg (group: $blockGroup)")
            onBlockTriggered?.invoke(pkg, blockGroup)
            showBlockingOverlay(pkg, blockGroup)
        } else if (!shouldBlock && alreadyBlocked) {
            // Time window opened or limit reset — unblock
            Log.i(TAG, "Rule re-eval unblocked: $pkg")
            hideBlockingOverlay()
        }
    }

    private fun recordSessionEnd() {
        if (sessionPackage.isEmpty()) return
        val duration = (System.currentTimeMillis() - sessionStart) / 1000
        val groupId = appGroupMap[sessionPackage]
        if (groupId != null && duration > 0) {
            usageByGroup[groupId] = (usageByGroup[groupId] ?: 0) + duration
        }
    }

    private fun detectForegroundApp(): String? {
        // Primary: use AccessibilityService
        val a11yPkg = HeimdallAccessibilityService.currentPackage
        if (a11yPkg.isNotEmpty()) return a11yPkg

        // Fallback: UsageStatsManager
        return try {
            val usm = getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
                ?: return null
            val end = System.currentTimeMillis()
            val start = end - TimeUnit.SECONDS.toMillis(5)
            val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_BEST, start, end)
            stats?.maxByOrNull { it.lastTimeUsed }?.packageName
        } catch (e: Exception) {
            Log.w(TAG, "UsageStats fallback failed", e)
            null
        }
    }

    fun getUsageTodayByGroup(): Map<String, Long> = usageByGroup.toMap()

    fun resetDailyUsage() {
        usageByGroup.clear()
    }

    private fun showBlockingOverlay(packageName: String, groupId: String) {
        val intent = Intent(this, BlockingOverlayService::class.java).apply {
            putExtra("packageName", packageName)
            putExtra("groupId", groupId)
        }
        startService(intent)
    }

    private fun hideBlockingOverlay() {
        BlockingOverlayService.instance?.hideBlock()
    }
}
