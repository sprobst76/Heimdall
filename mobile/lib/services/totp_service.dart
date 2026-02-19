import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:otp/otp.dart';

/// Manages TOTP secret caching and offline code verification for the child app.
///
/// The secret is cached in secure storage after a successful rules sync.
/// Offline verification allows the child to unlock even without internet.
class TotpService {
  static const String _secretKey = 'totp_secret';
  static const String _modeKey = 'totp_mode';
  static const String _tanMinutesKey = 'totp_tan_minutes';
  static const String _overrideMinutesKey = 'totp_override_minutes';

  final FlutterSecureStorage _storage;

  TotpService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  /// Cache the TOTP config received from a rules/status sync.
  Future<void> cacheConfig({
    required String secret,
    required String mode,
    required int tanMinutes,
    required int overrideMinutes,
  }) async {
    await Future.wait([
      _storage.write(key: _secretKey, value: secret),
      _storage.write(key: _modeKey, value: mode),
      _storage.write(key: _tanMinutesKey, value: tanMinutes.toString()),
      _storage.write(key: _overrideMinutesKey, value: overrideMinutes.toString()),
    ]);
  }

  /// Clear the cached TOTP config (e.g. when TOTP is disabled).
  Future<void> clearConfig() async {
    await Future.wait([
      _storage.delete(key: _secretKey),
      _storage.delete(key: _modeKey),
      _storage.delete(key: _tanMinutesKey),
      _storage.delete(key: _overrideMinutesKey),
    ]);
  }

  /// Check whether a TOTP secret is cached.
  Future<bool> hasConfig() async {
    final secret = await _storage.read(key: _secretKey);
    return secret != null && secret.isNotEmpty;
  }

  /// Verify a 6-digit code offline using the cached secret.
  ///
  /// Allows ±1 period (30 s) of clock drift. Returns false if no secret is cached.
  Future<bool> verifyOffline(String code) async {
    final secret = await _storage.read(key: _secretKey);
    if (secret == null || secret.isEmpty) return false;

    final now = DateTime.now().millisecondsSinceEpoch;

    // Check current period and ±1 period for clock tolerance
    for (final offset in [-30000, 0, 30000]) {
      final expected = OTP.generateTOTPCodeString(
        secret,
        now + offset,
        algorithm: Algorithm.SHA1,
        isGoogle: true,
      );
      if (expected == code) return true;
    }
    return false;
  }

  /// Return the cached mode ('tan', 'override', 'both'), or 'tan' as default.
  Future<String> getCachedMode() async {
    return await _storage.read(key: _modeKey) ?? 'tan';
  }

  Future<int> getCachedTanMinutes() async {
    final v = await _storage.read(key: _tanMinutesKey);
    return v != null ? int.tryParse(v) ?? 30 : 30;
  }

  Future<int> getCachedOverrideMinutes() async {
    final v = await _storage.read(key: _overrideMinutesKey);
    return v != null ? int.tryParse(v) ?? 30 : 30;
  }
}
