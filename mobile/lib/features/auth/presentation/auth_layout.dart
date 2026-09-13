import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";

/// Shared frame for login/register so both screens share brand header, spacing and error styling.
class AuthLayout extends StatelessWidget {
  const AuthLayout({
    super.key,
    required this.title,
    required this.subtitle,
    required this.form,
    required this.footer,
    this.showBack = false,
  });

  final String title;
  final String subtitle;
  final Widget form;
  final Widget footer;
  final bool showBack;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: showBack ? AppBar() : null,
      body: SafeArea(
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.xl, AppSpacing.xl, AppSpacing.xl),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (!showBack) Gap.xl,
                  const CareerOSLogo(markSize: 36),
                  Gap.xxl,
                  Semantics(header: true, child: Text(title, style: context.text.headlineMedium)),
                  Gap.xs,
                  Text(subtitle, style: context.text.bodyLarge?.copyWith(color: context.colors.textSecondary)),
                  Gap.xxl,
                  form,
                  Gap.xl,
                  footer,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Inline, friendly form-level error (never a raw exception string).
class AuthErrorBanner extends StatelessWidget {
  const AuthErrorBanner({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.sm),
        decoration: BoxDecoration(color: AppTone.danger.tint(context), borderRadius: AppRadius.mdAll),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(AppIcons.error, size: 20, color: AppColors.error),
            Gap.xs,
            Expanded(child: Text(message, style: context.text.bodyMedium?.copyWith(color: AppColors.error))),
          ],
        ),
      ),
    );
  }
}

/// "Don't have an account? Sign up" footer row.
class AuthSwitchPrompt extends StatelessWidget {
  const AuthSwitchPrompt({super.key, required this.prompt, required this.actionLabel, required this.onPressed});

  final String prompt;
  final String actionLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text(prompt, style: context.text.bodyMedium),
        TextButton(onPressed: onPressed, child: Text(actionLabel)),
      ],
    );
  }
}
