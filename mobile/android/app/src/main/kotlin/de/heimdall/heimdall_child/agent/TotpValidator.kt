package de.heimdall.heimdall_child.agent

import android.util.Log
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.nio.ByteBuffer

/**
 * Offline TOTP validation (RFC 6238 / RFC 4226).
 *
 * Used for parent unlock (Eltern-Freischaltung): the parent sees a 6-digit
 * TOTP code in the parent app; the child enters it in the child app; this
 * class validates it locally using the cached totp_config.secret (Base32).
 *
 * Algorithm: HOTP(K, T) where T = floor(unixtime / 30)
 * - HMAC-SHA1 over 8-byte big-endian counter
 * - Dynamic truncation → 6-digit decimal
 *
 * Allows ±1 time window (90s total) to compensate for clock drift.
 */
class TotpValidator {
    companion object {
        private const val TAG = "HeimdallTotp"
        private const val PERIOD_SECONDS = 30L
        private const val DIGITS = 6
        private const val ALLOWED_DRIFT_WINDOWS = 1
        private val BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    }

    /**
     * Validate a 6-digit TOTP code against a Base32-encoded secret.
     *
     * @param code     6-digit string entered by the user
     * @param base32Secret  TOTP secret as Base32 string (spaces and padding ignored)
     * @return true if the code is valid within the allowed time drift
     */
    fun validate(code: String, base32Secret: String): Boolean {
        if (code.length != DIGITS || !code.all { it.isDigit() }) {
            Log.w(TAG, "Invalid TOTP code format: length=${code.length}")
            return false
        }

        val secretBytes = try {
            base32Decode(base32Secret.uppercase().replace(" ", "").replace("=", ""))
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode TOTP secret: ${e.message}")
            return false
        }

        val counter = System.currentTimeMillis() / 1000L / PERIOD_SECONDS
        for (delta in -ALLOWED_DRIFT_WINDOWS..ALLOWED_DRIFT_WINDOWS) {
            val expected = hotp(secretBytes, counter + delta)
            if (expected == code) {
                Log.i(TAG, "TOTP valid (delta=$delta)")
                return true
            }
        }
        Log.d(TAG, "TOTP invalid for all windows")
        return false
    }

    /**
     * Generate the current TOTP code for a secret (useful for testing and debug).
     */
    fun generate(base32Secret: String): String {
        val secretBytes = base32Decode(base32Secret.uppercase().replace(" ", "").replace("=", ""))
        val counter = System.currentTimeMillis() / 1000L / PERIOD_SECONDS
        return hotp(secretBytes, counter)
    }

    /**
     * Returns seconds remaining in the current 30s window.
     */
    fun secondsRemaining(): Int {
        return (PERIOD_SECONDS - (System.currentTimeMillis() / 1000L % PERIOD_SECONDS)).toInt()
    }

    // -- HOTP (RFC 4226) --

    private fun hotp(key: ByteArray, counter: Long): String {
        val msg = ByteBuffer.allocate(8).putLong(counter).array()
        val mac = Mac.getInstance("HmacSHA1")
        mac.init(SecretKeySpec(key, "HmacSHA1"))
        val hash = mac.doFinal(msg)

        // Dynamic truncation
        val offset = hash.last().toInt() and 0x0F
        val code = ((hash[offset].toInt() and 0x7F) shl 24) or
                   ((hash[offset + 1].toInt() and 0xFF) shl 16) or
                   ((hash[offset + 2].toInt() and 0xFF) shl 8) or
                    (hash[offset + 3].toInt() and 0xFF)

        return (code % 1_000_000).toString().padStart(DIGITS, '0')
    }

    // -- Base32 decoder (RFC 4648) --

    private fun base32Decode(input: String): ByteArray {
        if (input.isEmpty()) throw IllegalArgumentException("Empty Base32 secret")
        var bits = 0
        var bitsCount = 0
        val output = mutableListOf<Byte>()

        for (char in input) {
            val value = BASE32_ALPHABET.indexOf(char)
            if (value < 0) throw IllegalArgumentException("Invalid Base32 char: '$char'")
            bits = (bits shl 5) or value
            bitsCount += 5
            if (bitsCount >= 8) {
                bitsCount -= 8
                output.add(((bits ushr bitsCount) and 0xFF).toByte())
            }
        }

        if (output.isEmpty()) throw IllegalArgumentException("Base32 decoded to empty byte array")
        return output.toByteArray()
    }
}
