import "package:flutter/material.dart";

/// CareerOS design-system palette (see ARCHITECTURE.md / master spec §5).
/// Single source of truth — features must reference these, never hardcode hex values.
abstract final class AppColors {
  static const navy = Color(0xFF081B3A);
  static const blue = Color(0xFF1677FF);
  static const cyan = Color(0xFF12A8FF);
  static const background = Color(0xFFF6F8FC);
  static const card = Color(0xFFFFFFFF);
  static const text = Color(0xFF10213D);
  static const muted = Color(0xFF718096);
  static const success = Color(0xFF19B36B);
  static const warning = Color(0xFFF5A623);
  static const danger = Color(0xFFE84D5B);
  static const purple = Color(0xFF7557FF);
}
