import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../../aptitude/presentation/preparation_hub_screen.dart";
import "../../intelligence/presentation/intelligence_feed_tab.dart";
import "../../opportunities/presentation/opportunities_tab.dart";
import "../../profile/presentation/profile_tab.dart";
import "home_tab.dart";

/// Main bottom navigation shell — the five CareerOS hubs, in fixed order:
/// Home · Opportunities · Prepare · Intelligence · Profile (see mobile-navigation.md).
/// Jobs, scholarships, ATS and tests live inside those hubs, never as extra tabs.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, this.initialTab});

  /// Hub name from `/home?tab=` — home, opportunities, prepare, intelligence or profile.
  final String? initialTab;

  static const tabNames = ["home", "opportunities", "prepare", "intelligence", "profile"];

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  late int _index = HomeShell.tabNames.indexOf(widget.initialTab ?? "home").clamp(0, HomeShell.tabNames.length - 1);

  void _selectTab(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final tabs = [
      HomeTab(onSelectTab: _selectTab),
      const OpportunitiesTab(),
      const PreparationHubScreen(),
      const IntelligenceFeedTab(),
      const ProfileTab(),
    ];

    return Scaffold(
      body: SafeArea(bottom: false, child: IndexedStack(index: _index, children: tabs)),
      bottomNavigationBar: CareerNavigationBar(
        selectedIndex: _index,
        onSelected: _selectTab,
        items: const [
          CareerNavItem(icon: AppIcons.home, selectedIcon: AppIcons.homeSelected, label: "Home"),
          CareerNavItem(icon: AppIcons.opportunities, selectedIcon: AppIcons.opportunitiesSelected, label: "Opportunities"),
          CareerNavItem(icon: AppIcons.prepare, selectedIcon: AppIcons.prepareSelected, label: "Prepare"),
          CareerNavItem(icon: AppIcons.intelligence, selectedIcon: AppIcons.intelligenceSelected, label: "Intelligence"),
          CareerNavItem(icon: AppIcons.profile, selectedIcon: AppIcons.profileSelected, label: "Profile"),
        ],
      ),
    );
  }
}
