import "package:flutter/material.dart";

import "app_colors.dart";
import "career_colors.dart";

/// Semantic color intent. Features pick a tone, never a raw color, so meaning stays consistent
/// (e.g. every "interview" status is [warning], every destructive action is [danger]).
enum AppTone {
  neutral,
  primary,
  info,
  success,
  warning,
  danger,
  purple;

  Color color(BuildContext context) => switch (this) {
        AppTone.neutral => context.colors.textSecondary,
        AppTone.primary => context.colors.primary,
        AppTone.info => AppColors.cyan,
        AppTone.success => AppColors.success,
        AppTone.warning => AppColors.warning,
        AppTone.danger => AppColors.error,
        AppTone.purple => AppColors.purple,
      };

  /// Background tint for chips, icon tiles and highlight surfaces.
  Color tint(BuildContext context) => context.colors.tint(color(context));

  /// Readable foreground for text placed on [tint]. Amber and cyan are too light for small text on
  /// a light tint, so they darken slightly in light mode.
  Color onTint(BuildContext context) {
    final base = color(context);
    if (context.colors.isDark) return base;
    return switch (this) {
      AppTone.warning => const Color(0xFFB9770E),
      AppTone.info => const Color(0xFF0B8DB3),
      AppTone.success => const Color(0xFF12874F),
      _ => base,
    };
  }
}
