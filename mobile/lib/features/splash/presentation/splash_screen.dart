import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";

/// Splash screen (master spec §7): brand moment while auth state resolves. The redirect decision
/// lives in app_router.dart's GoRouter `redirect` — this screen only renders while that resolves.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watching authStateProvider here ensures the router's redirect re-evaluates once it
    // resolves, even though the redirect itself reads the provider via ref.read.
    ref.watch(authStateProvider);

    return Scaffold(
      backgroundColor: AppColors.navy,
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.2),
            radius: 1.1,
            colors: [Color(0xFF0D2E63), AppColors.navy],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(flex: 5),
              const CareerOSMark(size: 88, onDark: true),
              Gap.lg,
              const CareerOSWordmark(fontSize: 34, onDark: true),
              Gap.sm,
              Text(
                "Opportunities Today.\nA Brighter You Tomorrow.",
                textAlign: TextAlign.center,
                style: context.text.bodyMedium?.copyWith(color: Colors.white.withValues(alpha: 0.72)),
              ),
              const Spacer(flex: 6),
              SizedBox.square(
                dimension: 24,
                child: CircularProgressIndicator(strokeWidth: 2.2, color: Colors.white.withValues(alpha: 0.6)),
              ),
              Gap.xxl,
            ],
          ),
        ),
      ),
    );
  }
}
