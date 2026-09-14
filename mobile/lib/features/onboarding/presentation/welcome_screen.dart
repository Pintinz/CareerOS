import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";

/// The front door for signed-out users (mockup board §1): brand, what CareerOS covers, and one
/// primary action. "Get Started" is the new-user path (onboarding carousel → create account);
/// returning users take "Log in".
class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  // Capabilities that exist in the app today — keep this list truthful.
  static const _features = [
    "Jobs & Internships",
    "Scholarships",
    "Company News",
    "Interview Preparation",
    "Application Tracking",
  ];

  @override
  Widget build(BuildContext context) {
    final onNavy = Colors.white.withValues(alpha: 0.78);

    return Scaffold(
      backgroundColor: AppColors.navy,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0.9, -0.9),
            radius: 1.4,
            colors: [Color(0xFF0D3B84), AppColors.navy],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: Column(
                    children: [
                      const Spacer(flex: 3),
                      const CareerOSMark(size: 104, onDark: true, decorative: true),
                      Gap.xs,
                      const CareerOSWordmark(height: 34, onDark: true),
                      Gap.md,
                      Semantics(
                        header: true,
                        child: Text(
                          "Your Career Intelligence\n& Opportunity Platform",
                          textAlign: TextAlign.center,
                          style: context.text.titleMedium?.copyWith(color: onNavy, height: 1.35),
                        ),
                      ),
                      const Spacer(flex: 2),
                      Gap.lg,
                      Align(
                        alignment: Alignment.center,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            for (final feature in _features)
                              Padding(
                                padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      width: 24,
                                      height: 24,
                                      decoration: const BoxDecoration(color: AppColors.blue, shape: BoxShape.circle),
                                      child: const Icon(AppIcons.check, size: 16, color: Colors.white),
                                    ),
                                    Gap.sm,
                                    Flexible(
                                      child: Text(feature, style: context.text.bodyLarge?.copyWith(color: Colors.white)),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),
                      const Spacer(flex: 3),
                      Gap.xl,
                      PrimaryButton(
                        label: "Get Started",
                        onPressed: () => context.push("/onboarding"),
                      ),
                      Gap.xs,
                      Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text("Already have an account?", style: context.text.bodyMedium?.copyWith(color: onNavy)),
                          TextButton(
                            onPressed: () => context.push("/login"),
                            style: TextButton.styleFrom(foregroundColor: AppColors.brightBlue),
                            child: const Text("Log in"),
                          ),
                        ],
                      ),
                      Gap.sm,
                      Text(
                        "Opportunities Today. A Brighter You Tomorrow.",
                        textAlign: TextAlign.center,
                        style: context.text.labelMedium?.copyWith(color: Colors.white.withValues(alpha: 0.55), letterSpacing: 0.4),
                      ),
                      Gap.lg,
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
