import "package:flutter/material.dart";

import "../design/design.dart";

/// Segmented pill tabs: the selected tab is a filled electric-blue pill on a muted track (mockup
/// board: Opportunities, Interview Preparation, Application Tracker). Use for peer views of the
/// same content; use the underline [TabBar] for sections of a detail screen.
class CareerPillTabBar extends StatelessWidget implements PreferredSizeWidget {
  const CareerPillTabBar({super.key, required this.tabs, this.controller, this.scrollable = false, this.onTap});

  final List<String> tabs;
  final TabController? controller;
  final bool scrollable;
  final ValueChanged<int>? onTap;

  @override
  Size get preferredSize => const Size.fromHeight(44);

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      height: 44,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: colors.surfaceMuted, borderRadius: AppRadius.pillAll),
      child: TabBar(
        controller: controller,
        onTap: onTap,
        isScrollable: scrollable,
        tabAlignment: scrollable ? TabAlignment.start : TabAlignment.fill,
        dividerHeight: 0,
        indicatorSize: TabBarIndicatorSize.tab,
        indicator: BoxDecoration(
          color: colors.primary,
          borderRadius: AppRadius.pillAll,
          boxShadow: colors.isDark ? null : [BoxShadow(color: colors.primary.withValues(alpha: 0.25), blurRadius: 8, offset: const Offset(0, 2))],
        ),
        labelColor: Colors.white,
        unselectedLabelColor: colors.textSecondary,
        labelStyle: context.text.labelMedium?.copyWith(fontWeight: FontWeight.w700),
        unselectedLabelStyle: context.text.labelMedium,
        labelPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        splashBorderRadius: AppRadius.pillAll,
        overlayColor: WidgetStateProperty.all(Colors.transparent),
        tabs: [for (final label in tabs) Tab(text: label, height: 36)],
      ),
    );
  }
}
