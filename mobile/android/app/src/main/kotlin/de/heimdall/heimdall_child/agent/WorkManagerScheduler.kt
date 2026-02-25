package de.heimdall.heimdall_child.agent

import android.content.Context
import android.util.Log
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkRequest
import java.util.concurrent.TimeUnit

/**
 * Schedules and cancels the periodic rule-sync WorkManager job.
 *
 * Schedule: every 2 hours, with a 1-hour flex window so the OS can
 * batch it with other work (better battery life).
 * Constraint: device must have network connectivity.
 * Policy: KEEP — if already scheduled, the existing job is preserved
 * (avoids resetting the timer on every app start).
 */
object WorkManagerScheduler {

    private const val TAG = "HeimdallScheduler"
    private const val WORK_NAME = "heimdall_rule_sync"

    fun scheduleRuleSync(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<RuleSyncWorker>(
            repeatInterval = 2L,
            repeatIntervalTimeUnit = TimeUnit.HOURS,
            flexTimeInterval = 1L,
            flexTimeIntervalUnit = TimeUnit.HOURS,
        )
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                WorkRequest.MIN_BACKOFF_MILLIS,
                TimeUnit.MILLISECONDS,
            )
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
        Log.i(TAG, "Periodic rule sync scheduled (every 2h ±1h, network required)")
    }

    fun cancelRuleSync(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        Log.i(TAG, "Periodic rule sync cancelled")
    }
}
