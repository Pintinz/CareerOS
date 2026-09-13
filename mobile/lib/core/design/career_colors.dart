import "package:flutter/material.dart";

import "app_colors.dart";

/// Mode-dependent color roles, attached to [ThemeData] as an extension. Read with `context.colors`.
@immutable
class CareerColors extends ThemeExtension<CareerColors> {
  const CareerColors({
    required this.isDark,
    required this.background,
    required this.surface,
    required this.surfaceElevated,
    required this.surfaceMuted,
    required this.textPrimary,
    required this.textSecondary,
    required this.border,
    required this.primary,
    required this.heroGradient,
  });

  final bool isDark;
  final Color background;
  final Color surface;
  final Color surfaceElevated;

  /// Subtle grouping ground: skeletons, input fills, ad containers, segmented-control tracks.
  final Color surfaceMuted;
  final Color textPrimary;
  final Color textSecondary;
  final Color border;

  /// Brand blue tuned for contrast on this mode's surfaces.
  final Color primary;
  final List<Color> heroGradient;

  static const light = CareerColors(
    isDark: false,
    background: AppColors.lightBackground,
    surface: AppColors.lightSurface,
    surfaceElevated: AppColors.lightSurface,
    surfaceMuted: AppColors.lightSurfaceMuted,
    textPrimary: AppColors.lightTextPrimary,
    textSecondary: AppColors.lightTextSecondary,
    border: AppColors.lightBorder,
    primary: AppColors.blue,
    heroGradient: [AppColors.navy, Color(0xFF0D3B84), AppColors.blue],
  );

  static const dark = CareerColors(
    isDark: true,
    background: AppColors.darkBackground,
    surface: AppColors.darkSurface,
    surfaceElevated: AppColors.darkSurfaceElevated,
    surfaceMuted: AppColors.darkSurfaceMuted,
    textPrimary: AppColors.darkTextPrimary,
    textSecondary: AppColors.darkTextSecondary,
    border: AppColors.darkBorder,
    primary: AppColors.brightBlue,
    heroGradient: [AppColors.darkSurface, AppColors.darkSurfaceElevated, Color(0xFF0D3B84)],
  );

  /// Tint for a tone-colored background (chips, icon tiles, highlights).
  Color tint(Color color) => color.withValues(alpha: isDark ? 0.18 : 0.10);

  @override
  CareerColors copyWith({
    bool? isDark,
    Color? background,
    Color? surface,
    Color? surfaceElevated,
    Color? surfaceMuted,
    Color? textPrimary,
    Color? textSecondary,
    Color? border,
    Color? primary,
    List<Color>? heroGradient,
  }) {
    return CareerColors(
      isDark: isDark ?? this.isDark,
      background: background ?? this.background,
      surface: surface ?? this.surface,
      surfaceElevated: surfaceElevated ?? this.surfaceElevated,
      surfaceMuted: surfaceMuted ?? this.surfaceMuted,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      border: border ?? this.border,
      primary: primary ?? this.primary,
      heroGradient: heroGradient ?? this.heroGradient,
    );
  }

  @override
  CareerColors lerp(ThemeExtension<CareerColors>? other, double t) {
    if (other is! CareerColors) return this;
    return CareerColors(
      isDark: t < 0.5 ? isDark : other.isDark,
      background: Color.lerp(background, other.background, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceElevated: Color.lerp(surfaceElevated, other.surfaceElevated, t)!,
      surfaceMuted: Color.lerp(surfaceMuted, other.surfaceMuted, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      border: Color.lerp(border, other.border, t)!,
      primary: Color.lerp(primary, other.primary, t)!,
      heroGradient: [
        for (var i = 0; i < heroGradient.length; i++)
          Color.lerp(heroGradient[i], other.heroGradient[i], t)!,
      ],
    );
  }
}

extension CareerThemeContext on BuildContext {
  /// Mode-aware color roles. Falls back to the light palette if a theme without the extension is
  /// in scope (e.g. a bare MaterialApp in a widget test).
  CareerColors get colors => Theme.of(this).extension<CareerColors>() ?? CareerColors.light;

  TextTheme get text => Theme.of(this).textTheme;
}
