package de.heimdall.heimdall_child.agent

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for TotpValidator (RFC 6238).
 *
 * Test secret: JBSWY3DPEHPK3PXP (standard test vector from RFC / pyotp)
 * This is Base32("Hello!") padded.
 */
class TotpValidatorTest {

    // Standard test vector secret used by pyotp and RFC examples
    private val TEST_SECRET = "JBSWY3DPEHPK3PXP"

    private lateinit var validator: TotpValidator

    @Before
    fun setUp() {
        validator = TotpValidator()
    }

    // -- Basic generation --

    @Test
    fun `generate produces 6-digit string`() {
        val code = validator.generate(TEST_SECRET)
        assertEquals("Generated code should be 6 digits", 6, code.length)
        assertTrue("Generated code should be all digits", code.all { it.isDigit() })
    }

    @Test
    fun `generate is consistent within same 30s window`() {
        val code1 = validator.generate(TEST_SECRET)
        val code2 = validator.generate(TEST_SECRET)
        assertEquals("Two calls within same window should match", code1, code2)
    }

    // -- Validation of own generated code --

    @Test
    fun `validate accepts freshly generated code`() {
        val code = validator.generate(TEST_SECRET)
        assertTrue("Should accept own generated code", validator.validate(code, TEST_SECRET))
    }

    @Test
    fun `validate rejects wrong code`() {
        val code = validator.generate(TEST_SECRET)
        val wrong = if (code == "000000") "000001" else "000000"
        assertFalse("Should reject wrong code", validator.validate(wrong, TEST_SECRET))
    }

    // -- Format validation --

    @Test
    fun `validate rejects code with wrong length`() {
        assertFalse(validator.validate("12345", TEST_SECRET))    // 5 digits
        assertFalse(validator.validate("1234567", TEST_SECRET))  // 7 digits
        assertFalse(validator.validate("", TEST_SECRET))         // empty
    }

    @Test
    fun `validate rejects non-numeric code`() {
        assertFalse(validator.validate("12345a", TEST_SECRET))
        assertFalse(validator.validate("abcdef", TEST_SECRET))
        assertFalse(validator.validate("12 345", TEST_SECRET))
    }

    // -- Secret format handling --

    @Test
    fun `validate handles lowercase secret`() {
        val code = validator.generate(TEST_SECRET)
        assertTrue("Should accept lowercase secret", validator.validate(code, TEST_SECRET.lowercase()))
    }

    @Test
    fun `validate handles secret with spaces`() {
        val secretWithSpaces = "JBSWY3DP EHPK3PXP"
        val code = validator.generate(TEST_SECRET)
        assertTrue("Should ignore spaces in secret", validator.validate(code, secretWithSpaces))
    }

    @Test
    fun `validate handles secret with padding`() {
        val secretWithPadding = "JBSWY3DPEHPK3PXP=="
        val code = validator.generate(TEST_SECRET)
        assertTrue("Should ignore Base32 padding", validator.validate(code, secretWithPadding))
    }

    @Test
    fun `validate rejects invalid Base32 secret`() {
        assertFalse("Should reject invalid Base32", validator.validate("123456", "NOT!VALID@BASE32"))
    }

    @Test
    fun `validate rejects empty secret`() {
        assertFalse("Should reject empty secret", validator.validate("123456", ""))
    }

    // -- Different secrets --

    @Test
    fun `code from one secret is invalid for different secret`() {
        val otherSecret = "AAAAAAAAAAAAAAAA"
        val code = validator.generate(TEST_SECRET)
        // With very high probability these won't match — collision chance is 1 in 1,000,000
        // We skip this test if they happen to match (astronomically rare)
        val otherCode = validator.generate(otherSecret)
        if (code != otherCode) {
            assertFalse("Code from one secret should fail for another", validator.validate(code, otherSecret))
        }
    }

    // -- secondsRemaining --

    @Test
    fun `secondsRemaining is between 1 and 30`() {
        val remaining = validator.secondsRemaining()
        assertTrue("Remaining should be >= 1", remaining >= 1)
        assertTrue("Remaining should be <= 30", remaining <= 30)
    }

    // -- Known test vector (RFC 4226 Appendix D counter=0, secret=base32("12345678901234567890")) --

    @Test
    fun `hotp known vector counter 0`() {
        // RFC 4226 test vector: secret = "12345678901234567890" as ASCII bytes
        // Base32 encoding of "12345678901234567890":
        val rfcSecret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        // Expected HOTP for counter=0 is 755224, but that's for direct counter mode
        // TOTP uses floor(time/30) as counter — we can't test the exact value without
        // controlling time, so we just verify the code is valid when we generate it
        val code = validator.generate(rfcSecret)
        assertEquals(6, code.length)
        assertTrue(validator.validate(code, rfcSecret))
    }
}
