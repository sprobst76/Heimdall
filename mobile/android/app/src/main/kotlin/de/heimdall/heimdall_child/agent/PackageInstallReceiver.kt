package de.heimdall.heimdall_child.agent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * Detects new app installations and notifies the monitoring service.
 *
 * ACTION_PACKAGE_ADDED is exempt from Android 8+ implicit broadcast restrictions,
 * so manifest registration works. Package replacements (updates) are ignored —
 * only genuinely new installations trigger the callback.
 *
 * On detection: the new package is immediately added to AppMonitorService's
 * blockedPackages set so it is blocked the moment the child tries to open it,
 * and parents are notified via backend + Flutter.
 */
class PackageInstallReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "HeimdallPkgWatch"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_PACKAGE_ADDED) return

        // Ignore updates to existing apps — only care about fresh installs
        if (intent.getBooleanExtra(Intent.EXTRA_REPLACING, false)) return

        val packageName = intent.data?.schemeSpecificPart ?: return
        // Never block ourselves
        if (packageName == context.packageName) return

        Log.w(TAG, "New package installed: $packageName")

        val monitor = AppMonitorService.instance
        if (monitor != null) {
            // Block the newly installed app until a parent approves
            monitor.blockedPackages.add(packageName)
            monitor.onPackageInstalled?.invoke(packageName)
        } else {
            // Monitor not running — persist to prefs so it's blocked on next start
            val prefs = context.getSharedPreferences("heimdall_state", Context.MODE_PRIVATE)
            val existing = prefs.getStringSet("blocked_new_packages", mutableSetOf()) ?: mutableSetOf()
            prefs.edit().putStringSet("blocked_new_packages", existing + packageName).apply()
            Log.i(TAG, "Monitor not running — $packageName queued for blocking")
        }
    }
}
