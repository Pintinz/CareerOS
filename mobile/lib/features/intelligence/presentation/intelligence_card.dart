import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../data/intelligence_models.dart";

/// The one company-intelligence card: company · category · headline · summary · published date.
class IntelligenceCardTile extends StatelessWidget {
  const IntelligenceCardTile({super.key, required this.post, this.showSummary = true});

  final IntelligenceCard post;
  final bool showSummary;

  @override
  Widget build(BuildContext context) {
    final company = post.company;
    return CareerCard(
      onTap: () => context.push("/intelligence/${post.slug}"),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              NetworkImageWithFallback(
                url: company?.logoUrl,
                fallbackText: company?.name ?? post.headline,
                fallbackIcon: company == null ? AppIcons.intelligence : null,
                tone: AppTone.info,
                size: 32,
              ),
              Gap.xs,
              Expanded(
                child: Text(
                  company?.name ?? "Industry",
                  style: context.text.labelMedium?.copyWith(color: context.colors.textPrimary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              StatusChip(label: humanizeEnum(post.category), tone: AppTone.info, dense: true),
            ],
          ),
          Gap.sm,
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(post.headline, style: context.text.titleMedium, maxLines: 3, overflow: TextOverflow.ellipsis),
                    if (showSummary && post.summary != null && post.summary!.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(post.summary!, style: context.text.bodyMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
                    ],
                  ],
                ),
              ),
              if (post.thumbnailUrl != null) ...[
                Gap.sm,
                NetworkImageWithFallback(
                  url: post.thumbnailUrl,
                  fallbackText: post.headline,
                  fallbackIcon: AppIcons.intelligence,
                  tone: AppTone.info,
                  size: 72,
                  radius: AppRadius.md,
                ),
              ],
            ],
          ),
          if (post.publishedAt != null) ...[
            Gap.sm,
            Row(
              children: [
                Icon(AppIcons.time, size: 14, color: context.colors.textSecondary),
                const SizedBox(width: 4),
                Text(DateLabels.published(post.publishedAt!), style: context.text.bodySmall),
                if (post.isFeatured) ...[
                  Text("  ·  ", style: context.text.bodySmall),
                  Text("Featured", style: context.text.bodySmall?.copyWith(color: context.colors.primary, fontWeight: FontWeight.w600)),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
