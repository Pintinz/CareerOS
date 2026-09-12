import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../theme/app_colors.dart";

/// Splash screen (master spec §7): shows branding briefly, then routes to onboarding, login,
/// or home depending on local state. The actual redirect decision lives in app_router.dart's
/// GoRouter `redirect` — this screen only needs to render while that resolves.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watching authStateProvider here ensures the router's redirect re-evaluates once it
    // resolves, even though the redirect itself reads the provider via ref.read.
    ref.watch(authStateProvider);

    return const Scaffold(
      backgroundColor: AppColors.navy,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.workspace_premium_rounded, color: Colors.white, size: 64),
            SizedBox(height: 16),
            Text(
              "CareerOS",
              style: TextStyle(
                color: Colors.white,
                fontSize: 32,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
              ),
            ),
            SizedBox(height: 8),
            Text(
              "Skills. Opportunities. Intelligence.\nA Brighter You.",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 14, height: 1.4),
            ),
            SizedBox(height: 32),
            SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}
