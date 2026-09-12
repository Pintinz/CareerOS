import "package:flutter/foundation.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../core/app_providers.dart";
import "../features/auth/presentation/login_screen.dart";
import "../features/auth/presentation/register_screen.dart";
import "../features/home/presentation/home_shell.dart";
import "../features/onboarding/presentation/onboarding_screen.dart";
import "../features/splash/presentation/splash_screen.dart";

class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authStateProvider, (_, __) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _RouterRefreshNotifier(ref);

  return GoRouter(
    initialLocation: "/splash",
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final authState = ref.read(authStateProvider);

      // Auth state hasn't resolved yet (first launch) — stay on splash until it does.
      if (!authState.hasValue) {
        return location == "/splash" ? null : "/splash";
      }

      final isAuthenticated = authState.value == AuthState.authenticated;
      final hasOnboarded = ref.read(appPreferencesProvider).hasCompletedOnboarding;
      final isAuthRoute = location == "/login" || location == "/register";

      if (!hasOnboarded) {
        return location == "/onboarding" ? null : "/onboarding";
      }
      if (location == "/onboarding") {
        return isAuthenticated ? "/home" : "/login";
      }
      if (!isAuthenticated) {
        return isAuthRoute ? null : "/login";
      }
      // Authenticated + onboarded: keep out of splash/auth/onboarding routes.
      if (location == "/splash" || isAuthRoute) {
        return "/home";
      }
      return null;
    },
    routes: [
      GoRoute(path: "/splash", builder: (context, state) => const SplashScreen()),
      GoRoute(path: "/onboarding", builder: (context, state) => const OnboardingScreen()),
      GoRoute(path: "/login", builder: (context, state) => const LoginScreen()),
      GoRoute(path: "/register", builder: (context, state) => const RegisterScreen()),
      GoRoute(path: "/home", builder: (context, state) => const HomeShell()),
    ],
  );
});
