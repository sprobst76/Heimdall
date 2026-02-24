package de.heimdall.heimdall_child.agent

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.util.Log
import android.view.accessibility.AccessibilityEvent

class HeimdallAccessibilityService : AccessibilityService() {
    companion object {
        private const val TAG = "HeimdallA11y"
        var instance: HeimdallAccessibilityService? = null
            private set
        var currentPackage: String = ""
            private set
        // Listeners that get notified on app change
        var onAppChanged: ((String) -> Unit)? = null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        // Configure to listen for window state changes
        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 200
        }
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val pkg = event.packageName?.toString() ?: return
            if (pkg != currentPackage && pkg != "android" && !pkg.startsWith("com.android.systemui")) {
                val oldPkg = currentPackage
                currentPackage = pkg
                Log.d(TAG, "App changed: $oldPkg -> $pkg")
                onAppChanged?.invoke(pkg)
            }
        }
    }

    override fun onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        instance = null
        super.onDestroy()
        Log.i(TAG, "Accessibility service destroyed")
    }

    fun isActive(): Boolean = instance != null

    /**
     * Navigate away from the currently blocked app by pressing the Home button.
     * Called by AppMonitorService immediately before showing the blocking overlay,
     * so the blocked app is pushed to the background rather than staying visible
     * behind the overlay.
     */
    fun pressHome() {
        performGlobalAction(GLOBAL_ACTION_HOME)
    }
}
