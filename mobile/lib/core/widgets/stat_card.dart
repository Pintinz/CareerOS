import "package:flutter/material.dart";

import "../design/design.dart";
import "career_card.dart";
import "career_progress.dart";
import "icon_tile.dart";

/// Tabular figures keep numbers from shifting width as values change.
const _tabular = [FontFeature.tabularFigures()];

/// A real metric: large value, short label, optional one-line descriptor and optional progress.
/// Pass `value: null` while loading/unavailable — it renders "—", never a placeholder number.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.tone = AppTone.primary,
    this.caption,
    this.progress,
    this.onTap,
  });

  final String label;
  final String? value;
  final IconData icon;
  final AppTone tone;

  /// Short truthful descriptor under the label ("of 3 created", "Not enough data yet").
  final String? caption;

  /// 0–1 when the value is a share of a real maximum (a percentage score). Drawn as a slim bar.
  final double? progress;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    // Value leads with the icon tucked top-right, so the label gets the card's full width and short
    // labels ("Tests completed") stay on one line in a two-column grid.
    return CareerCard(
      onTap: onTap,
      semanticLabel: [label, value ?? "not available", if (caption != null) caption!].join(": "),
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.sm, AppSpacing.md),
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.xxs),
                    child: Text(
                      value ?? "—",
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.text.headlineSmall?.copyWith(fontFeatures: _tabular, letterSpacing: -0.4),
                    ),
                  ),
                ),
                IconTile(icon: icon, tone: tone, size: 32),
              ],
            ),
            const SizedBox(height: 2),
            Text(label, maxLines: 2, overflow: TextOverflow.ellipsis, style: context.text.labelMedium),
            if (caption != null) ...[
              const SizedBox(height: 2),
              Text(caption!, maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.bodySmall),
            ],
            if (progress != null) ...[
              Gap.xs,
              CareerProgressBar(value: progress!, tone: tone, height: 5, semanticLabel: label),
            ],
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
                    style: context.text.titleLarge?.copyWith(color: valueColor, fontFeatures: _tabular),
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
