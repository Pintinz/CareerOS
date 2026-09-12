import "package:flutter/material.dart";

import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
import "../../intelligence/presentation/intelligence_feed_tab.dart";
import "../../opportunities/presentation/opportunities_tab.dart";
import "../../profile/presentation/profile_tab.dart";
import "home_tab.dart";

/// Main bottom navigation shell (master spec §6): Home, Opportunities, Prepare,
/// Intelligence, Profile. Prepare (aptitude/interview prep, Phases 6-7) is still an honest
/// empty state (§79 — never fabricate content); the rest now have real content.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static const _tabs = [
    HomeTab(),
    OpportunitiesTab(),
    PhasePendingPlaceholder(
      icon: Icons.fact_check_outlined,
      title: "Prepare",
      message: "Aptitude tests and interview preparation arrive in Phases 6-7.",
    ),
    IntelligenceFeedTab(),
    ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(child: IndexedStack(index: _index, children: _tabs)),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        backgroundColor: AppColors.card,
        indicatorColor: AppColors.blue.withValues(alpha: 0.12),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: "Home"),
          NavigationDestination(
            icon: Icon(Icons.work_outline_rounded),
            selectedIcon: Icon(Icons.work_rounded),
            label: "Opportunities",
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            selectedIcon: Icon(Icons.fact_check),
            label: "Prepare",
          ),
          NavigationDestination(
            icon: Icon(Icons.newspaper_outlined),
            selectedIcon: Icon(Icons.newspaper),
            label: "Intelligence",
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded),
            label: "Profile",
          ),
        ],
      ),
    );
  }
}
