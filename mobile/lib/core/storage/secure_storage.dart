import "package:flutter_secure_storage/flutter_secure_storage.dart";

/// Wraps flutter_secure_storage for the handful of values that must never live in
/// SharedPreferences/Drift: auth tokens. Everything else (cached feed data, saved jobs,
/// question sets) belongs in the Drift local database, not here.
class SecureStorage {
  SecureStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _accessTokenKey = "careeros_access_token";
  static const _refreshTokenKey = "careeros_refresh_token";

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<String?> get accessToken => _storage.read(key: _accessTokenKey);

  Future<String?> get refreshToken => _storage.read(key: _refreshTokenKey);

  Future<bool> get hasSession async => await accessToken != null;

  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}
