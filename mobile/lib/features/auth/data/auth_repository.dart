import "../../../core/network/api_client.dart";
import "../../../core/storage/secure_storage.dart";

class AuthRepository {
  AuthRepository({required ApiClient apiClient, required SecureStorage secureStorage})
      : _apiClient = apiClient,
        _secureStorage = secureStorage;

  final ApiClient _apiClient;
  final SecureStorage _secureStorage;

  Future<void> register({required String email, required String password}) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/auth/register",
      data: {"email": email, "password": password},
    );
    await _storeTokens(response.data!);
  }

  Future<void> login({required String email, required String password}) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/auth/login",
      data: {"email": email, "password": password},
    );
    await _storeTokens(response.data!);
  }

  Future<void> logout() => _secureStorage.clear();

  /// Permanently deletes the account server-side (all user-owned data), then clears the session.
  Future<void> deleteAccount() async {
    await _apiClient.delete<void>("/auth/me");
    await _secureStorage.clear();
  }

  Future<void> _storeTokens(Map<String, dynamic> body) => _secureStorage.saveTokens(
        accessToken: body["access_token"] as String,
        refreshToken: body["refresh_token"] as String,
      );
}
