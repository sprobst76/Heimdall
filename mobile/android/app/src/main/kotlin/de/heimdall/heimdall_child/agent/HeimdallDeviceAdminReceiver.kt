package de.heimdall.heimdall_child.agent

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import android.widget.Toast

class HeimdallDeviceAdminReceiver : DeviceAdminReceiver() {
    companion object {
        private const val TAG = "HeimdallAdmin"
    }

    override fun onEnabled(context: Context, intent: Intent) {
        Log.i(TAG, "Device admin enabled")
    }

    override fun onDisabled(context: Context, intent: Intent) {
        Log.w(TAG, "Device admin disabled")
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        return "Heimdall Kindersicherung: Deaktivierung erfordert den Eltern-PIN."
    }
}
