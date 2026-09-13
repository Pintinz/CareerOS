import "package:flutter/material.dart";
import "package:intl/intl.dart";

import "../../../theme/app_colors.dart";
import "../data/scholarship_models.dart";

class ScholarshipCardTile extends StatelessWidget {
  const ScholarshipCardTile({super.key, required this.scholarship, required this.onTap, required this.onToggleSave});

  final ScholarshipCard scholarship;
  final VoidCallback onTap;
  final VoidCallback onToggleSave;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      scholarship.name,
                      style: Theme.of(context).textTheme.titleLarge,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: onToggleSave,
                    icon: Icon(
                      scholarship.isSaved ? Icons.bookmark : Icons.bookmark_border,
                      color: scholarship.isSaved ? AppColors.blue : AppColors.muted,
                    ),
                  ),
                ],
              ),
              if (scholarship.organization != null)
                Text(scholarship.organization!, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  _Chip(
                    label: scholarship.fundingType.replaceAll("_", " "),
                    color: scholarship.fundingType == "FULLY_FUNDED" ? AppColors.success : AppColors.muted,
                  ),
                  if (scholarship.country != null) _Chip(label: scholarship.country!),
                  for (final level in scholarship.degreeLevels ?? []) _Chip(label: level),
                  if (scholarship.isDemo) const _Chip(label: "DEMO", color: AppColors.muted),
                ],
              ),
              if (scholarship.applicationDeadline != null) ...[
                const SizedBox(height: 8),
                Text(
                  "Deadline: ${DateFormat.yMMMd().format(scholarship.applicationDeadline!)}",
                  style: const TextStyle(fontSize: 12, color: AppColors.danger, fontWeight: FontWeight.w600),
                ),
              ],
            ],
          ),
        ),
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
      decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
      child: Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
