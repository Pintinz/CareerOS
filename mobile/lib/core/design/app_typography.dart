import "package:flutter/material.dart";

import "career_colors.dart";

/// CareerOS type scale mapped onto Material's [TextTheme] slots, so both `context.text.titleLarge`
/// and stock Material widgets pick up the same hierarchy.
abstract final class AppTypography {
  /// Preferred family is Plus Jakarta Sans. It is not bundled yet, so this stays `null` (platform
  /// default: Roboto on Android, SF Pro on iOS). Once the font files are added under
  /// `assets/fonts/` and declared in pubspec.yaml, set this to "PlusJakartaSans".
  static const String? fontFamily = null;
  static const List<String> fontFamilyFallback = ["Plus Jakarta Sans", "Inter", "SF Pro Text", "Roboto"];

  /// Test-only family for styles used outside the localized text theme (buttons, app bars). Widget
  /// tests have no platform default font, so without it those labels render as placeholder blocks
  /// in UI audit captures.
  @visibleForTesting
  static String? debugFontFamily;

  static TextTheme textTheme(CareerColors c) {
    TextStyle style(double size, FontWeight weight, Color color, {double? height, double spacing = 0}) => TextStyle(
          fontFamily: fontFamily ?? debugFontFamily,
          fontFamilyFallback: fontFamilyFallback,
          fontSize: size,
          fontWeight: weight,
          color: color,
          height: height,
          letterSpacing: spacing,
        );

    return TextTheme(
      // Display
      displayLarge: style(36, FontWeight.w800, c.textPrimary, height: 1.15, spacing: -0.8),
      displayMedium: style(34, FontWeight.w800, c.textPrimary, height: 1.15, spacing: -0.6),
      displaySmall: style(32, FontWeight.w800, c.textPrimary, height: 1.2, spacing: -0.5),
      // Page titles
      headlineLarge: style(28, FontWeight.w700, c.textPrimary, height: 1.2, spacing: -0.4),
      headlineMedium: style(26, FontWeight.w700, c.textPrimary, height: 1.2, spacing: -0.3),
      headlineSmall: style(22, FontWeight.w700, c.textPrimary, height: 1.25, spacing: -0.2),
      // Section / card titles
      titleLarge: style(19, FontWeight.w700, c.textPrimary, height: 1.3, spacing: -0.1),
      titleMedium: style(16, FontWeight.w600, c.textPrimary, height: 1.35),
      titleSmall: style(14, FontWeight.w600, c.textPrimary, height: 1.35),
      // Body
      bodyLarge: style(15, FontWeight.w400, c.textPrimary, height: 1.5),
      bodyMedium: style(14, FontWeight.w400, c.textSecondary, height: 1.45),
      bodySmall: style(12.5, FontWeight.w400, c.textSecondary, height: 1.4),
      // Labels
      labelLarge: style(15, FontWeight.w600, c.textPrimary, height: 1.2),
      labelMedium: style(13, FontWeight.w600, c.textSecondary, height: 1.2),
      labelSmall: style(11, FontWeight.w600, c.textSecondary, height: 1.2, spacing: 0.2),
    );
  }
}
