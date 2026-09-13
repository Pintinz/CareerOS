import "package:flutter/widgets.dart";

/// 8-pt spacing scale. Use these instead of literal numbers in padding, gaps and margins.
abstract final class AppSpacing {
  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
  static const double xxl = 32;
  static const double xxxl = 40;
  static const double huge = 48;

  /// Default horizontal page padding on phones.
  static const double pageH = lg;

  /// Gap between major page sections.
  static const double section = 28;

  /// Standard scrollable page insets (extra bottom room so content clears the nav bar/FAB).
  static const EdgeInsets page = EdgeInsets.fromLTRB(pageH, md, pageH, xxl);

  /// Horizontal-only page padding for rows that manage their own vertical rhythm.
  static const EdgeInsets pageHorizontal = EdgeInsets.symmetric(horizontal: pageH);

  static const EdgeInsets card = EdgeInsets.all(md);
  static const EdgeInsets cardLarge = EdgeInsets.all(lg);
}

/// Fixed-size gaps, so layouts read as `Gap.md` rather than `SizedBox(height: 16)`.
abstract final class Gap {
  static const xxs = SizedBox(width: AppSpacing.xxs, height: AppSpacing.xxs);
  static const xs = SizedBox(width: AppSpacing.xs, height: AppSpacing.xs);
  static const sm = SizedBox(width: AppSpacing.sm, height: AppSpacing.sm);
  static const md = SizedBox(width: AppSpacing.md, height: AppSpacing.md);
  static const lg = SizedBox(width: AppSpacing.lg, height: AppSpacing.lg);
  static const xl = SizedBox(width: AppSpacing.xl, height: AppSpacing.xl);
  static const xxl = SizedBox(width: AppSpacing.xxl, height: AppSpacing.xxl);
  static const section = SizedBox(width: AppSpacing.section, height: AppSpacing.section);
}
