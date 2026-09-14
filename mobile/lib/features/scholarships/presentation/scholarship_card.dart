import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../data/scholarship_models.dart";

/// The one scholarship card: provider · name · country · degree level · funding · deadline · save.
class ScholarshipCardTile extends StatelessWidget {
  const ScholarshipCardTile({super.key, required this.scholarship, required this.onTap, this.onToggleSave});

  final ScholarshipCard scholarship;
  final VoidCallback onTap;

  /// Null hides the bookmark.
  final VoidCallback? onToggleSave;

  @override
  Widget build(BuildContext context) {
    final deadline = scholarship.applicationDeadline;
    final fullyFunded = scholarship.fundingType == "FULLY_FUNDED";
    final availability = OpportunityAvailability.fromApi(scholarship.availability);

    return CareerCard(
      onTap: onTap,
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, AppSpacing.xxs, AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          NetworkImageWithFallback(
            url: scholarship.thumbnailUrl,
            fallbackText: scholarship.organization ?? scholarship.name,
            fallbackIcon: AppIcons.scholarship,
            tone: AppTone.purple,
            size: 48,
          ),
          Gap.sm,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (scholarship.organization != null)
                  Text(scholarship.organization!, style: context.text.labelMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(scholarship.name, style: context.text.titleMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
                if (scholarship.country != null) ...[
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Icon(AppIcons.location, size: 14, color: context.colors.textSecondary),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(scholarship.country!, style: context.text.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                      ),
                    ],
                  ),
                ],
                Gap.sm,
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (!availability.isActive) TagChip(label: availability.shortLabel, tone: availability.tone),
                    if (scholarship.awardType == "FELLOWSHIP") const TagChip(label: "Fellowship", tone: AppTone.purple),
                    // Funding the provider didn't state is never labelled.
                    if (isStatedValue(scholarship.fundingType))
                      TagChip(label: humanizeEnum(scholarship.fundingType), tone: fullyFunded ? AppTone.success : null),
                    for (final level in scholarship.degreeLevels ?? const <String>[]) TagChip(label: humanizeEnum(level)),
                    if (scholarship.isDemo) const TagChip(label: "DEMO"),
                  ],
                ),
                if (deadline != null && availability.isActive) ...[
                  Gap.sm,
                  Row(
                    children: [
                      Icon(AppIcons.deadline, size: 14, color: DateLabels.deadlineTone(deadline).onTint(context)),
                      const SizedBox(width: 4),
                      Text(
                        DateLabels.deadline(deadline),
                        style: context.text.bodySmall?.copyWith(
                          color: DateLabels.deadlineTone(deadline).onTint(context),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          if (onToggleSave != null)
            IconButton(
              tooltip: scholarship.isSaved ? "Remove from saved" : "Save scholarship",
              onPressed: onToggleSave,
              icon: Icon(
                scholarship.isSaved ? AppIcons.savedSelected : AppIcons.saved,
                color: scholarship.isSaved ? context.colors.primary : context.colors.textSecondary,
              ),
            )
          else
            Gap.sm,
        ],
      ),
    );
  }
}
