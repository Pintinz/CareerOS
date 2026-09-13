import "package:flutter/material.dart";

import "../design/design.dart";

/// Status pill — always text (plus optional icon), never color alone.
class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.label, this.tone = AppTone.neutral, this.icon, this.dense = false});

  final String label;
  final AppTone tone;
  final IconData? icon;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final foreground = tone.onTint(context);
    return Container(
      padding: EdgeInsets.symmetric(horizontal: dense ? 8 : 10, vertical: dense ? 3 : 5),
      decoration: BoxDecoration(color: tone.tint(context), borderRadius: AppRadius.pillAll),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: dense ? 12 : 14, color: foreground),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.text.labelSmall?.copyWith(color: foreground, fontSize: dense ? 10.5 : 11.5),
            ),
          ),
        ],
      ),
    );
  }
}

/// Neutral metadata tag (work mode, employment type, degree level). Pass [tone] only when the tag
/// carries meaning (e.g. "Fully funded" → success, "DEMO" → neutral, "Urgent" → danger).
class TagChip extends StatelessWidget {
  const TagChip({super.key, required this.label, this.tone, this.icon});

  final String label;
  final AppTone? tone;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final foreground = tone?.onTint(context) ?? colors.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: tone?.tint(context) ?? colors.surfaceMuted,
        borderRadius: AppRadius.smAll,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 13, color: foreground),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.text.labelSmall?.copyWith(color: foreground),
            ),
          ),
        ],
      ),
    );
  }
}

/// Selectable filter pill for feeds (wraps Material's [FilterChip] for accessibility + tests).
class AppFilterChip extends StatelessWidget {
  const AppFilterChip({super.key, required this.label, required this.selected, required this.onSelected, this.icon});

  final String label;
  final bool selected;
  final ValueChanged<bool> onSelected;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    // Selected = filled brand pill with white text (mockup board), unselected = outlined surface.
    return FilterChip(
      label: Text(label),
      avatar: icon == null ? null : Icon(icon, size: 16, color: selected ? Colors.white : colors.textSecondary),
      selected: selected,
      onSelected: onSelected,
      showCheckmark: false,
      backgroundColor: colors.surface,
      selectedColor: colors.primary,
      labelStyle: context.text.labelMedium?.copyWith(color: selected ? Colors.white : colors.textPrimary),
      side: BorderSide(color: selected ? colors.primary : colors.border),
      shape: const StadiumBorder(),
      materialTapTargetSize: MaterialTapTargetSize.padded,
    );
  }
}
