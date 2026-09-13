import "package:flutter/material.dart";

import "../design/design.dart";
import "career_card.dart";
import "icon_tile.dart";

/// A real metric with an icon. Pass `value: null` while loading/unavailable — it renders "—",
/// never a placeholder number.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.tone = AppTone.primary,
    this.onTap,
  });

  final String label;
  final String? value;
  final IconData icon;
  final AppTone tone;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      onTap: onTap,
      semanticLabel: "$label: ${value ?? "not available"}",
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: ExcludeSemantics(
        child: Row(
          children: [
            IconTile(icon: icon, tone: tone, size: 40),
            Gap.sm,
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(value ?? "—", maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.headlineSmall),
                  Text(label, maxLines: 2, overflow: TextOverflow.ellipsis, style: context.text.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact value-over-label pair for use inside an existing container (results, headers).
class MetricTile extends StatelessWidget {
  const MetricTile({
    super.key,
    required this.label,
    required this.value,
    this.tone,
    this.icon,
    this.alignment = CrossAxisAlignment.start,
  });

  final String label;
  final String? value;
  final AppTone? tone;
  final IconData? icon;
  final CrossAxisAlignment alignment;

  @override
  Widget build(BuildContext context) {
    final valueColor = tone?.color(context) ?? context.colors.textPrimary;
    return Semantics(
      label: "$label: ${value ?? "not available"}",
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: alignment,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 16, color: valueColor),
                  Gap.xxs,
                ],
                Flexible(
                  child: Text(
                    value ?? "—",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.text.titleLarge?.copyWith(color: valueColor),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: alignment == CrossAxisAlignment.center ? TextAlign.center : TextAlign.start,
              style: context.text.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
