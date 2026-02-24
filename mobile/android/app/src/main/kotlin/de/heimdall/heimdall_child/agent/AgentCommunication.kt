package de.heimdall.heimdall_child.agent

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.time.Instant
import java.util.concurrent.TimeUnit

class AgentCommunication(private val context: Context) {
    companion object {
        private const val TAG = "HeimdallComm"
        private const val PREFS_NAME = "heimdall_agent"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_DEVICE_TOKEN = "device_token"
        private const val KEY_DEVICE_ID = "device_id"
        private const val DEFAULT_SERVER = "http://10.0.2.2:8000"  // emulator -> localhost
        private const val API_PREFIX = "/api/v1"
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()

    var onRuleUpdate: ((JSONObject) -> Unit)? = null
    var onBlockApp: ((String) -> Unit)? = null
    var onUnblockApp: ((String) -> Unit)? = null
    var onConnected: (() -> Unit)? = null

    val serverUrl: String get() = prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER) ?: DEFAULT_SERVER
    val deviceToken: String get() = prefs.getString(KEY_DEVICE_TOKEN, "") ?: ""
    val deviceId: String get() = prefs.getString(KEY_DEVICE_ID, "") ?: ""
    val isRegistered: Boolean get() = deviceToken.isNotEmpty()
    private val apiBase: String get() = "$serverUrl$API_PREFIX"

    fun configure(serverUrl: String, deviceToken: String, deviceId: String) {
        prefs.edit()
            .putString(KEY_SERVER_URL, serverUrl)
            .putString(KEY_DEVICE_TOKEN, deviceToken)
            .putString(KEY_DEVICE_ID, deviceId)
            .apply()
    }

    // -- REST endpoints --

    suspend fun sendHeartbeat(activeApp: String? = null): JSONObject? = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("timestamp", Instant.now().toString())
            put("active_app", activeApp)
        }
        postJson("/agent/heartbeat", body)
    }

    suspend fun sendUsageEvent(
        appPackage: String?,
        appGroupId: String?,
        eventType: String,  // "start" | "stop" | "blocked"
        startedAt: String? = null,
        endedAt: String? = null,
        durationSeconds: Int? = null
    ): JSONObject? = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("app_package", appPackage)
            put("app_group_id", appGroupId)
            put("event_type", eventType)
            put("started_at", startedAt)
            put("ended_at", endedAt)
            put("duration_seconds", durationSeconds)
        }
        postJson("/agent/usage-event", body)
    }

    suspend fun fetchRules(): JSONObject? = withContext(Dispatchers.IO) {
        getJson("/agent/rules/current")
    }

    // -- WebSocket --

    fun connectWebSocket() {
        val wsUrl = serverUrl.replace("http://", "ws://").replace("https://", "wss://")
        val url = "$wsUrl$API_PREFIX/agent/ws"
        Log.i(TAG, "Connecting WebSocket to $url")

        val request = Request.Builder().url(url).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                // Send device token as first message for authentication
                ws.send(deviceToken)
                Log.i(TAG, "WebSocket opened, sent auth token")
                onConnected?.invoke()
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val msg = JSONObject(text)
                    val type = msg.optString("type", "")
                    Log.d(TAG, "WS message: $type")

                    when (type) {
                        "auth_ok" -> Log.i(TAG, "WebSocket authenticated")
                        "rule_update" -> onRuleUpdate?.invoke(msg.optJSONObject("rules") ?: JSONObject())
                        "block_app" -> onBlockApp?.invoke(msg.optString("app_group_id", ""))
                        "unblock_app" -> onUnblockApp?.invoke(msg.optString("app_group_id", ""))
                        "pong", "heartbeat_ack", "ack" -> { /* expected */ }
                        else -> Log.d(TAG, "Unhandled WS type: $type")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing WS message", e)
                }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "WebSocket failure: ${t.message}")
                // Reconnect after delay
                scope.launch {
                    delay(5000)
                    if (isRegistered) connectWebSocket()
                }
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WebSocket closed: $code $reason")
            }
        })
    }

    fun sendWsHeartbeat() {
        webSocket?.send(JSONObject().apply { put("type", "heartbeat") }.toString())
    }

    fun disconnectWebSocket() {
        webSocket?.close(1000, "Agent shutting down")
        webSocket = null
    }

    // -- HTTP helpers --

    private fun postJson(path: String, body: JSONObject): JSONObject? {
        val request = Request.Builder()
            .url("$apiBase$path")
            .header("X-Device-Token", deviceToken)
            .post(body.toString().toRequestBody(JSON_MEDIA))
            .build()
        return executeRequest(request)
    }

    private fun getJson(path: String): JSONObject? {
        val request = Request.Builder()
            .url("$apiBase$path")
            .header("X-Device-Token", deviceToken)
            .get()
            .build()
        return executeRequest(request)
    }

    private fun executeRequest(request: Request): JSONObject? {
        return try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    response.body?.string()?.let { JSONObject(it) }
                } else {
                    Log.e(TAG, "HTTP ${response.code}: ${response.message}")
                    null
                }
            }
        } catch (e: IOException) {
            Log.e(TAG, "Request failed: ${e.message}")
            null
        }
    }

    fun destroy() {
        disconnectWebSocket()
        scope.cancel()
    }
}
