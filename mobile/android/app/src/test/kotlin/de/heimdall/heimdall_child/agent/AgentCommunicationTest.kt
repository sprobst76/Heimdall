package de.heimdall.heimdall_child.agent

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AgentCommunicationTest {

    private lateinit var server: MockWebServer
    private lateinit var comm: AgentCommunication

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()

        val context = ApplicationProvider.getApplicationContext<Context>()
        comm = AgentCommunication(context)
        comm.configure(
            serverUrl = server.url("/").toString().trimEnd('/'),
            deviceToken = "test-token-123",
            deviceId = "device-abc",
        )
    }

    @After
    fun tearDown() {
        comm.destroy()
        server.shutdown()
    }

    @Test
    fun test_configure_stores_credentials() {
        assertEquals("test-token-123", comm.deviceToken)
        assertEquals("device-abc", comm.deviceId)
        assertTrue(comm.isRegistered)
    }

    @Test
    fun test_isRegistered_false_without_token() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        // Clear the prefs
        context.getSharedPreferences("heimdall_agent", Context.MODE_PRIVATE)
            .edit().clear().commit()
        val fresh = AgentCommunication(context)
        assertFalse(fresh.isRegistered)
        fresh.destroy()
    }

    @Test
    fun test_sendHeartbeat_success() = runTest {
        server.enqueue(MockResponse()
            .setBody("""{"status":"ok"}""")
            .setHeader("Content-Type", "application/json"))

        val result = comm.sendHeartbeat(activeApp = "chrome")

        assertNotNull(result)
        assertEquals("ok", result!!.getString("status"))

        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path!!.contains("/agent/heartbeat"))
        assertEquals("test-token-123", request.getHeader("X-Device-Token"))
    }

    @Test
    fun test_sendHeartbeat_serverError() = runTest {
        server.enqueue(MockResponse().setResponseCode(500))

        val result = comm.sendHeartbeat()
        assertNull(result)
    }

    @Test
    fun test_fetchRules_success() = runTest {
        val rulesJson = """{"daily_limit_minutes":120,"day_type":"school"}"""
        server.enqueue(MockResponse()
            .setBody(rulesJson)
            .setHeader("Content-Type", "application/json"))

        val result = comm.fetchRules()

        assertNotNull(result)
        assertEquals(120, result!!.getInt("daily_limit_minutes"))

        val request = server.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path!!.contains("/agent/rules/current"))
    }

    @Test
    fun test_sendUsageEvent_success() = runTest {
        server.enqueue(MockResponse()
            .setBody("""{"id":"evt-1"}""")
            .setHeader("Content-Type", "application/json"))

        val result = comm.sendUsageEvent(
            appPackage = "com.minecraft",
            appGroupId = "games",
            eventType = "start",
        )

        assertNotNull(result)
        assertEquals("evt-1", result!!.getString("id"))

        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path!!.contains("/agent/usage-event"))
        val body = JSONObject(request.body.readUtf8())
        assertEquals("com.minecraft", body.getString("app_package"))
        assertEquals("start", body.getString("event_type"))
    }
}
