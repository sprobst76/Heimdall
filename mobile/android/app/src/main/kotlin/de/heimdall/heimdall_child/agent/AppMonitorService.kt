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

    // Callbacks
    var onAppChanged: ((oldPkg: String, newPkg: String) -> Unit)? = null
    var appGroupMap: Map<String, String> = emptyMap()  // packageName -> groupId
    var blockedGroups: MutableSet<String> = mutableSetOf()
    var onBlockTriggered: ((packageName: String, groupId: String) -> Unit)? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
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

    private fun startMonitoring() {
        monitorJob = scope.launch {
            while (isActive) {
                val pkg = detectForegroundApp()
                if (pkg != null && pkg != currentForegroundPackage) {
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

                    // Check if blocked
                    val groupId = appGroupMap[pkg]
                    if (groupId != null && blockedGroups.contains(groupId)) {
                        Log.i(TAG, "Blocked app detected: $pkg (group: $groupId)")
                        onBlockTriggered?.invoke(pkg, groupId)
                    }
                }
                delay(POLL_INTERVAL_MS)
            }
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
}
