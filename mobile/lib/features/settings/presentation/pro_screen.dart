import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";

/// Settings → CareerOS Pro (spec §10/§57). No purchase flow exists — this screen must never
/// imply one does. Shows the prepared entitlement architecture (ad-free, unlimited usage,
/// advanced analytics) honestly labeled "Coming Soon", with no button that looks purchasable.
class ProScreen extends StatelessWidget {
  const ProScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    const features = [
      (Icons.block_outlined, "No ads"),
      (AppIcons.cv, "Unlimited ATS analyses"),
      (AppIcons.aptitude, "Unlimited aptitude tests"),
      (AppIcons.analytics, "Advanced analytics"),
      (AppIcons.interview, "Premium interview practice content"),
      (Icons.file_copy_outlined, "Multiple CV features"),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text("CareerOS Pro")),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.lg),
            decoration: BoxDecoration(
              borderRadius: AppRadius.heroAll,
              gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colors.heroGradient),
              border: colors.isDark ? Border.all(color: colors.border) : null,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    CareerOSMark(size: 36, onDark: true, decorative: true),
                    Gap.sm,
                    Icon(AppIcons.pro, color: Colors.white),
                  ],
                ),
                Gap.md,
                Text("CareerOS Pro", style: context.text.headlineSmall?.copyWith(color: Colors.white)),
                Gap.xs,
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: AppRadius.pillAll),
                  child: Text("Coming Soon", style: context.text.labelMedium?.copyWith(color: Colors.white)),
                ),
              ],
            ),
          ),
          Gap.section,
          CareerListGroup(
            title: "What's planned",
            children: [for (final (icon, title) in features) CareerListRow(icon: icon, tone: AppTone.purple, title: title)],
          ),
          Gap.lg,
          Text(
            "CareerOS Pro purchases are not yet available. This screen shows what's planned — "
            "there is nothing to buy here yet, and nothing on this screen will charge you.",
            style: context.text.bodySmall,
          ),
        ],
      ),
    );
  }
}
