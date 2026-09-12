import "package:flutter/material.dart";

import "../../../theme/app_colors.dart";
import "../../jobs/presentation/job_list_tab.dart";
import "../../scholarships/presentation/scholarship_list_tab.dart";

/// Top-level "Opportunities" tab (spec §6/§12): Jobs and Scholarships sub-tabs. Internships and
/// graduate programmes reuse the job data model (see ARCHITECTURE.md) and aren't separate
/// sub-tabs yet — revisit once there's enough of that content to warrant splitting it out.
class OpportunitiesTab extends StatefulWidget {
  const OpportunitiesTab({super.key});

  @override
  State<OpportunitiesTab> createState() => _OpportunitiesTabState();
}

class _OpportunitiesTabState extends State<OpportunitiesTab> with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Text("Opportunities", style: Theme.of(context).textTheme.headlineMedium),
        ),
        TabBar(
          controller: _tabController,
          labelColor: AppColors.blue,
          unselectedLabelColor: AppColors.muted,
          indicatorColor: AppColors.blue,
          tabs: const [Tab(text: "Jobs"), Tab(text: "Scholarships")],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [JobListTab(), ScholarshipListTab()],
          ),
        ),
      ],
    );
  }
}
