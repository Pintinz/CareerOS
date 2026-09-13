import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../data/job_models.dart";

/// The one job card. `compact` is the fixed-width carousel variant used on Home.
///
/// Hierarchy (screen-patterns.md): logo · title · company · location • work mode · employment
/// type · posted time · bookmark · verified (real) · DEMO for demo data. No descriptions.
class JobCardTile extends StatelessWidget {
  const JobCardTile({
    super.key,
    required this.job,
    required this.onTap,
    this.onToggleSave,
    this.compact = false,
  });

  final JobCard job;
  final VoidCallback onTap;

  /// Null hides the bookmark (e.g. read-only previews).
  final VoidCallback? onToggleSave;
  final bool compact;

  String get _meta {
    final location = job.location?.trim() ?? "";
    final workMode = humanizeEnum(job.workMode);
    return [
      if (location.isNotEmpty) location,
      // Avoid "Remote • Remote" when the listing's location already states the work mode.
      if (location.toLowerCase() != workMode.toLowerCase()) workMode,
    ].join(" • ");
  }

  @override
  Widget build(BuildContext context) {
    return compact ? _buildCompact(context) : _buildList(context);
  }

  Widget _tags() => Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          TagChip(label: humanizeEnum(job.employmentType)),
          if (job.experienceLevel != null) TagChip(label: humanizeEnum(job.experienceLevel!)),
          if (job.applicationDeadline != null && DateLabels.daysUntil(job.applicationDeadline!) >= 0 && DateLabels.daysUntil(job.applicationDeadline!) <= 14)
            TagChip(
              label: DateLabels.deadline(job.applicationDeadline!),
              icon: AppIcons.deadline,
              tone: DateLabels.deadlineTone(job.applicationDeadline!),
            ),
          if (job.isUrgent) const TagChip(label: "Urgent", tone: AppTone.danger),
          if (job.isDemo) const TagChip(label: "DEMO"),
        ],
      );

  Widget _saveButton(BuildContext context) => IconButton(
        tooltip: job.isSaved ? "Remove from saved" : "Save job",
        onPressed: onToggleSave,
        icon: Icon(
          job.isSaved ? AppIcons.savedSelected : AppIcons.saved,
          color: job.isSaved ? context.colors.primary : context.colors.textSecondary,
        ),
      );

  Widget _footer(BuildContext context) => Row(
        children: [
          if (job.publishedAt != null)
            Flexible(
              child: Text(DateLabels.published(job.publishedAt!), style: context.text.bodySmall, maxLines: 1),
            ),
          const Spacer(),
          if (job.isVerified)
            Semantics(
              label: "Verified employer",
              child: const Icon(AppIcons.verified, size: 16, color: AppColors.success),
            ),
        ],
      );

  Widget _buildList(BuildContext context) {
    return CareerCard(
      onTap: onTap,
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, AppSpacing.xxs, AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          NetworkImageWithFallback(url: job.company.logoUrl, fallbackText: job.company.name, size: 48),
          Gap.sm,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(job.title, style: context.text.titleMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(job.company.name, style: context.text.bodyMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Icon(AppIcons.location, size: 14, color: context.colors.textSecondary),
                    const SizedBox(width: 4),
                    Expanded(child: Text(_meta, style: context.text.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis)),
                  ],
                ),
                Gap.sm,
                _tags(),
                Gap.sm,
                Padding(padding: const EdgeInsets.only(right: AppSpacing.sm), child: _footer(context)),
              ],
            ),
          ),
          if (onToggleSave != null) _saveButton(context) else Gap.sm,
        ],
      ),
    );
  }

  Widget _buildCompact(BuildContext context) {
    return SizedBox(
      width: 272,
      child: CareerCard(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                NetworkImageWithFallback(url: job.company.logoUrl, fallbackText: job.company.name, size: 40),
                Gap.sm,
                Expanded(
                  child: Text(job.company.name, style: context.text.labelMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                ),
                if (job.isVerified) const Icon(AppIcons.verified, size: 16, color: AppColors.success),
              ],
            ),
            Gap.sm,
            Text(job.title, style: context.text.titleMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 4),
            Text(_meta, style: context.text.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis),
            const Spacer(),
            _tags(),
            Gap.sm,
            _footer(context),
          ],
        ),
      ),
    );
  }
}
