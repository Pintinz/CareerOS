import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";
import "package:intl/intl.dart";

import "../../../theme/app_colors.dart";
import "../data/job_models.dart";

class JobCardTile extends StatelessWidget {
  const JobCardTile({super.key, required this.job, required this.onTap, required this.onToggleSave});

  final JobCard job;
  final VoidCallback onTap;
  final VoidCallback onToggleSave;

  static final _timeFormat = DateFormat("MMM d");

  String get _employmentTypeLabel => job.employmentType.replaceAll("_", "-").toLowerCase();
  String get _workModeLabel => job.workMode.replaceAll("_", " ").toLowerCase();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _CompanyAvatar(logoUrl: job.company.logoUrl, name: job.company.name),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            job.title,
                            style: Theme.of(context).textTheme.titleLarge,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          visualDensity: VisualDensity.compact,
                          onPressed: onToggleSave,
                          icon: Icon(
                            job.isSaved ? Icons.bookmark : Icons.bookmark_border,
                            color: job.isSaved ? AppColors.blue : AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                    Text(job.company.name, style: Theme.of(context).textTheme.bodyMedium),
                    if (job.location != null) ...[
                      const SizedBox(height: 2),
                      Text(job.location!, style: Theme.of(context).textTheme.bodyMedium),
                    ],
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        _Chip(label: _employmentTypeLabel),
                        _Chip(label: _workModeLabel),
                        if (job.isUrgent) const _Chip(label: "Urgent", color: AppColors.danger),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        if (job.publishedAt != null)
                          Text(
                            "Posted ${_timeFormat.format(job.publishedAt!)}",
                            style: Theme.of(context).textTheme.bodyMedium,
                          )
                        else
                          const SizedBox.shrink(),
                        if (job.isVerified)
                          const Row(
                            children: [
                              Icon(Icons.verified, size: 14, color: AppColors.success),
                              SizedBox(width: 4),
                              Text("Verified", style: TextStyle(fontSize: 12, color: AppColors.success)),
                            ],
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CompanyAvatar extends StatelessWidget {
  const _CompanyAvatar({required this.logoUrl, required this.name});

  final String? logoUrl;
  final String name;

  @override
  Widget build(BuildContext context) {
    final fallback = Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: AppColors.blue.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      alignment: Alignment.center,
      child: Text(
        name.isNotEmpty ? name[0].toUpperCase() : "?",
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.blue),
      ),
    );

    if (logoUrl == null || logoUrl!.isEmpty) return fallback;

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: CachedNetworkImage(
        imageUrl: logoUrl!,
        width: 48,
        height: 48,
        fit: BoxFit.cover,
        placeholder: (context, url) => fallback,
        errorWidget: (context, url, error) => fallback,
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, this.color = AppColors.muted});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}
