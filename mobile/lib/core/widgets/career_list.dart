import "package:flutter/material.dart";

import "../design/design.dart";
import "icon_tile.dart";

/// A titled group of [CareerListRow]s inside one bordered surface (settings, profile, secondary
/// navigation). Rows are separated by inset dividers — never one card per row.
class CareerListGroup extends StatelessWidget {
  const CareerListGroup({super.key, this.title, required this.children});

  final String? title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title != null)
          Padding(
            padding: const EdgeInsets.only(left: AppSpacing.xxs, bottom: AppSpacing.xs),
            child: Semantics(
              header: true,
              // Sentence case rather than all caps: calmer, and easier to read at small sizes.
              child: Text(title!, style: context.text.labelMedium?.copyWith(fontWeight: FontWeight.w600)),
            ),
          ),
        Material(
          color: colors.surface,
          shape: RoundedRectangleBorder(borderRadius: AppRadius.cardAll, side: BorderSide(color: colors.border)),
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: [
              for (var i = 0; i < children.length; i++) ...[
                if (i > 0) Divider(height: 1, indent: 68, color: colors.border),
                children[i],
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// Navigation/settings row: icon tile · title · optional subtitle · trailing (chevron by default).
class CareerListRow extends StatelessWidget {
  const CareerListRow({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.onTap,
    this.trailing,
    this.tone = AppTone.primary,
    this.destructive = false,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final Widget? trailing;
  final AppTone tone;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final effectiveTone = destructive ? AppTone.danger : tone;
    return InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 60),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
          child: Row(
            children: [
              IconTile(icon: icon, tone: effectiveTone, size: 38),
              Gap.md,
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: context.text.titleSmall?.copyWith(color: destructive ? AppColors.error : null),
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 2),
                      Text(subtitle!, style: context.text.bodySmall),
                    ],
                  ],
                ),
              ),
              if (trailing != null)
                trailing!
              else if (onTap != null && !destructive)
                Icon(AppIcons.chevron, color: context.colors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}
