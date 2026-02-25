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
import java.time.LocalDate
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

    // Tracks which groups have already received a 5-min limit warning today
    private val warnedLimitGroups = mutableSetOf<String>()

    // SharedPrefs for tamper detection and daily reset state
    private val statePrefs by lazy {
        getSharedPreferences("heimdall_state", Context.MODE_PRIVATE)
    }

    // Callbacks
    var onAppChanged: ((oldPkg: String, newPkg: String) -> Unit)? = null
    var appGroupMap: Map<String, String> = emptyMap()  // packageName -> groupId
    var blockedGroups: MutableSet<String> = mutableSetOf()  // manually blocked groups
    /** Packages blocked pending parent approval (new installs). */
    val blockedPackages: MutableSet<String> = mutableSetOf()
    var onBlockTriggered: ((packageName: String, groupId: String) -> Unit)? = null
    /** Fired when PackageInstallReceiver detects a new app installation. */
    var onPackageInstalled: ((packageName: String) -> Unit)? = null
    /** Called every ~60s by the monitoring loop. Used by MethodChannelHandler to send heartbeats. */
    var onSyncNeeded: (suspend (activePackage: String?) -> Unit)? = null
    /** Fired when the service detects it was previously force-killed (tamper attempt). */
    var onTamperDetected: ((reason: String) -> Unit)? = null
    /** Fired when a group is approaching its daily limit (≤5 min remaining). */
    var onLimitWarning: ((groupId: String, remainingMinutes: Int) -> Unit)? = null
    /** Fired when an active VPN or proxy is detected (once per session, resets at midnight). */
    var onVpnDetected: ((reason: String) -> Unit)? = null

    // Tracks the VPN/proxy state to fire the callback only on transitions (off → on)
    private var lastVpnReason: String? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        checkTamper()
        restoreQueuedBlockedPackages()
        // Register for instant A11y notifications (much faster than polling)
        HeimdallAccessibilityService.onAppChanged = { pkg ->
            handleForegroundChange(pkg)
        }
        startMonitoring()
        Log.i(TAG, "Monitor service created")
    }

    /**
     * Tamper detection: if the previous session ended without calling onDestroy()
     * (i.e. the service was force-killed), fire the tamper callback.
     * We set graceful_shutdown=false on create and true on destroy.
     */
    private fun checkTamper() {
        val wasGraceful = statePrefs.getBoolean("graceful_shutdown", true)
        statePrefs.edit().putBoolean("graceful_shutdown", false).apply()
        if (!wasGraceful) {
            Log.w(TAG, "Tamper detected: service was force-killed previously")
            // Delay to allow MethodChannelHandler to wire the callback first
            scope.launch {
                delay(3000)
                onTamperDetected?.invoke("service_killed")
            }
        }
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
        // Mark as graceful shutdown so next start doesn't trigger tamper alert
        statePrefs.edit().putBoolean("graceful_shutdown", true).apply()
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

        // Check if blocked (package-level, group-level, or rule-based)
        val groupId = appGroupMap[pkg]
        val shouldBlock = when {
            // 1. Package blocked pending parent approval (new install)
            blockedPackages.contains(pkg) -> true
            // 2. Manually blocked group (e.g. via parent action)
            groupId != null && blockedGroups.contains(groupId) -> true
            // 3. Rule-based: time window or daily limit exceeded
            groupId != null && ruleEvaluator?.isGroupAllowedNow(groupId, usageByGroup) == false -> true
            // 4. No group mapping but device time window violated → block all unknown apps
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
                    checkDailyReset()
                    reevaluateCurrentApp()
                    checkApproachingLimits()
                    checkVpnProxy()
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
            blockedPackages.contains(pkg) -> true
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

    /** Remove a package from pending-approval blocking (parent approved the install). */
    fun approvePackage(packageName: String) {
        blockedPackages.remove(packageName)
        // Also remove from persisted queue
        val prefs = getSharedPreferences("heimdall_state", Context.MODE_PRIVATE)
        val current = prefs.getStringSet("blocked_new_packages", mutableSetOf()) ?: mutableSetOf()
        prefs.edit().putStringSet("blocked_new_packages", current - packageName).apply()
        reevaluateCurrentApp()
        Log.i(TAG, "Package approved by parent: $packageName")
    }

    /**
     * On service start, restore packages that were blocked by PackageInstallReceiver
     * while the monitor service was not yet running.
     */
    private fun restoreQueuedBlockedPackages() {
        val queued = statePrefs.getStringSet("blocked_new_packages", emptySet()) ?: emptySet()
        if (queued.isNotEmpty()) {
            blockedPackages.addAll(queued)
            Log.i(TAG, "Restored ${queued.size} queued blocked package(s): $queued")
        }
    }

    fun getUsageTodayByGroup(): Map<String, Long> = usageByGroup.toMap()

    fun resetDailyUsage() {
        usageByGroup.clear()
        warnedLimitGroups.clear()
        lastVpnReason = null
        Log.i(TAG, "Daily usage counters reset")
    }

    /**
     * Check if the calendar date has changed since last reset and reset usage if so.
     * Called every 60s from the polling loop — catches the midnight transition.
     */
    private fun checkDailyReset() {
        val today = LocalDate.now().toString()
        val lastResetDate = statePrefs.getString("last_reset_date", "") ?: ""
        if (today != lastResetDate) {
            resetDailyUsage()
            statePrefs.edit().putString("last_reset_date", today).apply()
            Log.i(TAG, "Daily reset triggered for $today")
        }
    }

    /**
     * Check all known app groups for approaching daily limits.
     * Fires onLimitWarning when a group has ≤5 minutes remaining (once per day per group).
     */
    /**
     * Check for active VPN or proxy. Fires onVpnDetected only when the state
     * changes from "none" to "detected" — not on every polling tick.
     * lastVpnReason is reset at midnight (via resetDailyUsage).
     */
    private fun checkVpnProxy() {
        val reason = VpnDetector.detect(this)
        if (reason != null && lastVpnReason == null) {
            lastVpnReason = reason
            Log.w(TAG, "VPN/proxy detected: $reason")
            onVpnDetected?.invoke(reason)
        } else if (reason == null && lastVpnReason != null) {
            // VPN was removed — reset so we alert again if it comes back
            lastVpnReason = null
            Log.i(TAG, "VPN/proxy no longer active")
        }
    }

    private fun checkApproachingLimits() {
        val evaluator = ruleEvaluator ?: return
        val groups = appGroupMap.values.toSet()
        for (groupId in groups) {
            if (groupId in warnedLimitGroups) continue
            val remaining = evaluator.getRemainingMinutesForGroup(groupId, usageByGroup) ?: continue
            if (remaining in 1..5) {
                warnedLimitGroups.add(groupId)
                Log.i(TAG, "Approaching limit: group=$groupId remaining=${remaining}min")
                onLimitWarning?.invoke(groupId, remaining)
            }
        }
    }

    private fun showBlockingOverlay(packageName: String, groupId: String) {
        // Navigate away from the blocked app before showing overlay
        // so the app is pushed to background, not just hidden behind overlay
        HeimdallAccessibilityService.instance?.pressHome()
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
