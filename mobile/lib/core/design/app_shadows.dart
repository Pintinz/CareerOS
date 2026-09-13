import "package:flutter/material.dart";

import "app_colors.dart";
import "career_colors.dart";

/// Soft, refined elevation. Dark mode relies on lighter surfaces + borders instead of shadows.
abstract final class AppShadows {
  static List<BoxShadow> card(BuildContext context) => context.colors.isDark
      ? const []
      : [BoxShadow(color: AppColors.navy.withValues(alpha: 0.04), blurRadius: 16, offset: const Offset(0, 4))];

  static List<BoxShadow> raised(BuildContext context) => context.colors.isDark
      ? const []
      : [BoxShadow(color: AppColors.navy.withValues(alpha: 0.08), blurRadius: 24, offset: const Offset(0, 10))];

  /// Colored glow under a hero surface (light mode only).
  static List<BoxShadow> hero(BuildContext context) => context.colors.isDark
      ? const []
      : [BoxShadow(color: AppColors.blue.withValues(alpha: 0.22), blurRadius: 28, offset: const Offset(0, 12))];
}
