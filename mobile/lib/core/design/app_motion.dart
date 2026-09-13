import "package:flutter/widgets.dart";

/// Restrained motion. Nothing bounces, glows or loops for decoration.
abstract final class AppMotion {
  static const fast = Duration(milliseconds: 180);
  static const normal = Duration(milliseconds: 240);
  static const slow = Duration(milliseconds: 280);
  static const curve = Curves.easeOutCubic;

  /// [normal], or zero when the user asked the OS to reduce motion.
  static Duration of(BuildContext context, [Duration duration = normal]) =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false ? Duration.zero : duration;
}
