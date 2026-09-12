import "package:flutter_riverpod/flutter_riverpod.dart";

import "network/api_client.dart";
import "storage/app_preferences.dart";
import "storage/secure_storage.dart";

/// Root-level singletons. Feature providers should depend on these rather than constructing
/// their own SecureStorage/ApiClient instances.
final secureStorageProvider = Provider<SecureStorage>((ref) => SecureStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(secureStorage: ref.watch(secureStorageProvider));
});

/// Overridden in main.dart once SharedPreferences has loaded (see bootstrap in main.dart) —
/// kept as a throwing default so a missing override fails loudly instead of silently.
final appPreferencesProvider = Provider<AppPreferences>((ref) {
  throw UnimplementedError("appPreferencesProvider must be overridden in main.dart bootstrap");
});

enum AuthState { unknown, authenticated, unauthenticated }

final authStateProvider = FutureProvider<AuthState>((ref) async {
  final hasSession = await ref.watch(secureStorageProvider).hasSession;
  return hasSession ? AuthState.authenticated : AuthState.unauthenticated;
});
