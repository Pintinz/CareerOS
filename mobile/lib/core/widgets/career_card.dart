import "package:flutter/material.dart";

import "../design/design.dart";

enum CareerCardVariant {
  /// Surface + hairline border + soft shadow. The default content container.
  standard,

  /// Larger radius and padding for feature entry points (Prepare areas, hero-adjacent content).
  feature,

  /// Muted ground without border/shadow — for grouping inside a page without adding weight.
  muted,

  /// Border only, no shadow — for dense lists and nested-but-flat groupings.
  outlined,
}

/// The single CareerOS container primitive. Prefer spacing and [SectionHeader]s before reaching
/// for another card; never nest cards more than one level.
class CareerCard extends StatelessWidget {
  const CareerCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding,
    this.variant = CareerCardVariant.standard,
    this.color,
    this.semanticLabel,
  });

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry? padding;
  final CareerCardVariant variant;

  /// Overrides the surface color (e.g. a tone tint). Use sparingly.
  final Color? color;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final radius = variant == CareerCardVariant.feature ? AppRadius.featureAll : AppRadius.cardAll;
    final background = color ??
        switch (variant) {
          CareerCardVariant.muted => colors.surfaceMuted,
          _ => colors.surface,
        };
    final hasBorder = variant != CareerCardVariant.muted && color == null;
    final hasShadow = variant == CareerCardVariant.standard || variant == CareerCardVariant.feature;
    final resolvedPadding = padding ?? (variant == CareerCardVariant.feature ? AppSpacing.cardLarge : AppSpacing.card);

    Widget content = Padding(padding: resolvedPadding, child: child);
    if (onTap != null) {
      content = InkWell(onTap: onTap, borderRadius: radius, child: content);
    }

    Widget card = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: radius,
        boxShadow: hasShadow && color == null ? AppShadows.card(context) : null,
      ),
      child: Material(
        color: background,
        shape: RoundedRectangleBorder(
          borderRadius: radius,
          side: hasBorder ? BorderSide(color: colors.border) : BorderSide.none,
        ),
        clipBehavior: Clip.antiAlias,
        child: content,
      ),
    );

    if (semanticLabel != null) {
      card = Semantics(label: semanticLabel, button: onTap != null, container: true, child: card);
    }
    return card;
  }
}
