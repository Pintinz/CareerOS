import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../data/application_models.dart";
import "stage_badge.dart";

/// The one application tracker row: company mark · role · company · stage · applied/updated date.
class ApplicationCardTile extends StatelessWidget {
  const ApplicationCardTile({super.key, required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    final applied = application.appliedDate;
    final dateLabel = applied != null
        ? "Applied ${DateLabels.published(applied).toLowerCase()}"
        : "Updated ${DateLabels.published(application.updatedAt).toLowerCase()}";

    return CareerCard(
      onTap: () => context.push("/applications/${application.id}"),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          NetworkImageWithFallback(url: null, fallbackText: application.companyName, size: 48, tone: stageTone(application.currentStage)),
          Gap.sm,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(application.roleTitle, style: context.text.titleMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(
                  [application.companyName, if (application.location != null) application.location!].join(" · "),
                  style: context.text.bodyMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Gap.sm,
                Row(
                  children: [
                    Flexible(child: StageBadge(stage: application.currentStage, dense: true)),
                    Gap.xs,
                    Flexible(child: Text(dateLabel, style: context.text.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis)),
                  ],
                ),
              ],
            ),
          ),
          Icon(AppIcons.chevron, color: context.colors.textSecondary),
        ],
      ),
    );
  }
}
