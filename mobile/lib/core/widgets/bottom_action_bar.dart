import "package:flutter/material.dart";

import "../design/design.dart";

/// Pinned bottom bar for a detail screen's primary CTA (with an optional secondary beside it).
/// Use as `Scaffold.bottomNavigationBar`.
class BottomActionBar extends StatelessWidget {
  const BottomActionBar({super.key, required this.primary, this.secondary, this.caption});

  final Widget primary;
  final Widget? secondary;

  /// Optional one-line summary above the buttons (e.g. "20 questions · Mixed · Untimed"). It sits on
  /// its own line so it never squeezes the primary label.
  final Widget? caption;

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
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (caption != null) ...[
                DefaultTextStyle.merge(
                  style: context.text.labelMedium,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  child: caption!,
                ),
                Gap.xs,
              ],
              Row(
                children: [
                  if (secondary != null) ...[secondary!, Gap.sm],
                  Expanded(child: primary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
