import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../core/network/api_client.dart";
import "../../profile/presentation/profile_providers.dart";
import "../data/auth_repository.dart";

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    apiClient: ref.watch(apiClientProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});

/// Drives login/register screens: idle -> loading -> data (success) or error.
/// On success it invalidates [authStateProvider] so the router redirect re-evaluates and
/// navigates to home — screens should not navigate manually on success.
class AuthController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> login({required String email, required String password}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).login(email: email, password: password),
    );
    ref.invalidate(authStateProvider);
  }

  Future<void> register({required String email, required String password}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).register(email: email, password: password),
    );
    ref.invalidate(authStateProvider);
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    await _clearLocalUserData();
    ref.invalidate(authStateProvider);
  }

  /// Deletes the account (spec: in-app deletion required by Google Play and the App Store). Throws
  /// [ApiException] on failure so the caller can show it; local data is only wiped on success.
  Future<void> deleteAccount() async {
    await ref.read(authRepositoryProvider).deleteAccount();
    await _clearLocalUserData();
    ref.invalidate(authStateProvider);
  }

  /// Offline practice caches and user-scoped providers must not survive into another account.
  Future<void> _clearLocalUserData() async {
    await ref.read(aptitudeOfflineCacheProvider).clearAll();
    await ref.read(interviewOfflineCacheProvider).clearAll();
    ref.invalidate(userProfileProvider);
    ref.invalidate(currentUserProvider);
  }

  String? get errorMessage {
    final error = state.error;
    if (error == null) return null;
    return error is ApiException ? error.message : "Something went wrong. Please try again.";
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, void>(AuthController.new);
