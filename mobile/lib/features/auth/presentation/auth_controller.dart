import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../core/network/api_client.dart";
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
    ref.invalidate(authStateProvider);
  }

  String? get errorMessage {
    final error = state.error;
    if (error == null) return null;
    return error is ApiException ? error.message : "Something went wrong. Please try again.";
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, void>(AuthController.new);
