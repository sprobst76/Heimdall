package de.heimdall.heimdall_child.agent

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

/**
 * Detects active VPN connections and HTTP proxy settings.
 *
 * Used by AppMonitorService to spot circumvention attempts.
 * Checks are lightweight (no I/O) and safe to call from the main thread.
 */
object VpnDetector {

    /**
     * Returns a non-null reason string if a bypass is detected:
     *   "vpn"   — a VPN transport layer is active
     *   "proxy" — a system-wide HTTP proxy is configured
     * Returns null if nothing suspicious is found.
     */
    fun detect(context: Context): String? {
        if (isVpnActive(context)) return "vpn"
        if (isProxyActive()) return "proxy"
        return null
    }

    /**
     * True if any active network has TRANSPORT_VPN capability.
     * Covers both always-on VPNs and user-installed VPN apps.
     */
    private fun isVpnActive(context: Context): Boolean {
        return try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE)
                as ConnectivityManager
            cm.allNetworks.any { network ->
                cm.getNetworkCapabilities(network)
                    ?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true
            }
        } catch (_: Exception) {
            false
        }
    }

    /**
     * True if a global HTTP proxy host is set via system properties.
     * Manual proxy settings (Wi-Fi → Advanced) are reflected here.
     */
    private fun isProxyActive(): Boolean {
        return try {
            val host = System.getProperty("http.proxyHost")
            !host.isNullOrEmpty()
        } catch (_: Exception) {
            false
        }
    }
}
