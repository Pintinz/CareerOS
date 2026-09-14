import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../../jobs/presentation/job_list_tab.dart";
import "../../jobs/presentation/job_providers.dart";
import "../../scholarships/presentation/scholarship_list_tab.dart";

/// Opportunities hub — "What opportunities can I pursue?". Jobs, Internships and Graduate Programs
/// are job-backed feeds (see [JobFeed]); Scholarships (and fellowships) have their own model. Every
/// feed shows verified, published CareerOS records only — no live web search from the app.
class OpportunitiesTab extends StatefulWidget {
  const OpportunitiesTab({super.key});

  @override
  State<OpportunitiesTab> createState() => _OpportunitiesTabState();
}

class _OpportunitiesTabState extends State<OpportunitiesTab> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 4, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.xs, 0),
          child: HubHeader(
            title: "Opportunities",
            subtitle: "Jobs, scholarships, internships and graduate programmes",
            trailing: IconButton(
              tooltip: "Saved opportunities",
              onPressed: () => context.push("/saved"),
              icon: const Icon(AppIcons.saved),
            ),
          ),
        ),
        Gap.xs,
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, 0),
          child: CareerPillTabBar(
            controller: _tabController,
            scrollable: true,
            tabs: const ["Jobs", "Scholarships", "Internships", "Graduate Programs"],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [
              JobListTab(),
              ScholarshipListTab(),
              JobListTab(feed: JobFeed.internships),
              JobListTab(feed: JobFeed.graduatePrograms),
            ],
          ),
        ),
      ],
    );
  }
}
