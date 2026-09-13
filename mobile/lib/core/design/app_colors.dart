import "package:flutter/material.dart";

/// CareerOS brand + semantic palette (see .claude/skills/careeros-ui-system/references/design-tokens.md).
///
/// These constants are identical in light and dark mode. Anything that changes with the theme
/// (backgrounds, surfaces, text, borders) must come from `context.colors` ([CareerColors]) instead,
/// so dark mode keeps working.
abstract final class AppColors {
  // Brand
  static const navy = Color(0xFF071A38);
  static const blue = Color(0xFF1677FF);
  static const brightBlue = Color(0xFF249BFF);
  static const cyan = Color(0xFF13BDEB);

  // Semantic
  static const success = Color(0xFF18B76A);
  static const warning = Color(0xFFF5A623);
  static const error = Color(0xFFE84D5B);
  static const purple = Color(0xFF7557FF);

  // Light neutrals
  static const lightBackground = Color(0xFFF6F8FC);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightSurfaceMuted = Color(0xFFEEF2F8);
  static const lightTextPrimary = Color(0xFF10213D);
  static const lightTextSecondary = Color(0xFF66758C);
  static const lightBorder = Color(0xFFE6EBF2);

  // Dark neutrals
  static const darkBackground = Color(0xFF07111F);
  static const darkSurface = Color(0xFF0C1B31);
  static const darkSurfaceElevated = Color(0xFF112642);
  static const darkSurfaceMuted = Color(0xFF0F2139);
  static const darkTextPrimary = Color(0xFFF6F9FF);
  static const darkTextSecondary = Color(0xFF9AA9BD);
  static const darkBorder = Color(0xFF1D3352);

  // ---------------------------------------------------------------------------------------------
  // Legacy aliases kept only while screens migrate to the design system. They are light-mode
  // values and will not adapt to dark mode — new code must not use them.
  // ---------------------------------------------------------------------------------------------
  static const danger = error;
  static const background = lightBackground;
  static const card = lightSurface;
  static const text = lightTextPrimary;
  static const muted = lightTextSecondary;
}
