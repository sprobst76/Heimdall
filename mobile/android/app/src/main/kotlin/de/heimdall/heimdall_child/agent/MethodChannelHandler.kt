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

    fun initialize() {
        communication = AgentCommunication(context)
        cache = OfflineRuleCache(context)
        channel.setMethodCallHandler(this)
        Log.i(TAG, "Method channel handler initialized")
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "startMonitoring" -> {
                val intent = Intent(context, AppMonitorService::class.java)
                context.startForegroundService(intent)
                result.success(true)
            }
            "stopMonitoring" -> {
                val intent = Intent(context, AppMonitorService::class.java)
                context.stopService(intent)
                result.success(true)
            }
            "checkPermissions" -> {
                val permissions = mapOf(
                    "accessibility" to isAccessibilityEnabled(),
                    "usageStats" to isUsageStatsGranted(),
                    "deviceAdmin" to isDeviceAdminActive(),
                    "overlay" to Settings.canDrawOverlays(context),
                    "notification" to true  // Always true for Android 8+
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
                            result.success(rules.toString())
                        } else {
                            val cached = cache?.getCachedRules()
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
                result.success(true)
            }
            "unblockGroup" -> {
                val groupId = call.argument<String>("groupId") ?: ""
                AppMonitorService.instance?.blockedGroups?.remove(groupId)
                result.success(true)
            }
            "isMonitoringActive" -> {
                result.success(AppMonitorService.instance != null)
            }
            "isAccessibilityActive" -> {
                result.success(HeimdallAccessibilityService.instance != null)
            }
            "updateAppGroupMap" -> {
                val map = call.argument<Map<String, String>>("map") ?: emptyMap()
                AppMonitorService.instance?.appGroupMap = map
                cache?.cacheAppGroupMap(map)
                result.success(true)
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
