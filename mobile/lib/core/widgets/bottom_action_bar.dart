import "package:flutter/material.dart";

import "../design/design.dart";

/// Pinned bottom bar for a detail screen's primary CTA (with an optional secondary beside it).
/// Use as `Scaffold.bottomNavigationBar`.
class BottomActionBar extends StatelessWidget {
  const BottomActionBar({super.key, required this.primary, this.secondary, this.leading});

  final Widget primary;
  final Widget? secondary;

  /// Optional compact leading content (e.g. a deadline label).
  final Widget? leading;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(top: BorderSide(color: colors.border)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.sm, AppSpacing.pageH, AppSpacing.sm),
          child: Row(
            children: [
              if (leading != null) ...[Flexible(child: leading!), Gap.sm],
              if (secondary != null) ...[secondary!, Gap.sm],
              Expanded(child: primary),
            ],
          ),
        ),
      ),
    );
  }
}
