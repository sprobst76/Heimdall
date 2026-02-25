package de.heimdall.heimdall_child.agent

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

/**
 * WorkManager worker that periodically refreshes rules from the backend.
 *
 * Runs every 2 hours (±1h flex) when the device has network connectivity.
 * Keeps the offline rule cache up-to-date independently of the Flutter app
 * being in the foreground or the WebSocket being connected.
 *
 * On success: cache updated, live RuleEvaluator replaced on the main thread.
 * On network failure: Result.retry() → exponential backoff.
 */
class RuleSyncWorker(
    private val appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    companion object {
        private const val TAG = "HeimdallSync"
    }

    override suspend fun doWork(): Result {
        val comm = AgentCommunication(appContext)

        if (!comm.isRegistered) {
            Log.i(TAG, "Skipping rule sync — device not registered")
            return Result.success()
        }

        return try {
            val rules = comm.fetchRules()
            if (rules == null) {
                Log.w(TAG, "Rule sync: backend returned null — will retry")
                return Result.retry()
            }

            // Persist to offline cache
            val cache = OfflineRuleCache(appContext)
            cache.cacheRules(rules)

            // Update live AppMonitorService on the main thread to avoid races
            Handler(Looper.getMainLooper()).post {
                AppMonitorService.instance?.let { monitor ->
                    val evaluator = RuleEvaluator()
                    evaluator.updateRules(rules)
                    monitor.ruleEvaluator = evaluator
                    monitor.reevaluateCurrentApp()
                    Log.i(TAG, "Rules applied to running monitor service")
                }
            }

            Log.i(TAG, "Periodic rule sync successful")
            Result.success()
        } catch (e: Exception) {
            Log.w(TAG, "Rule sync failed: ${e.message}")
            Result.retry()
        }
    }
}
