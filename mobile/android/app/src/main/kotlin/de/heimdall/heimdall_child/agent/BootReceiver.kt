package de.heimdall.heimdall_child.agent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i("HeimdallBoot", "Boot completed — starting monitor service")
            val serviceIntent = Intent(context, AppMonitorService::class.java)
            context.startForegroundService(serviceIntent)
        }
    }
}
