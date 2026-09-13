import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../../jobs/data/job_models.dart";
import "../../jobs/presentation/job_card.dart";
import "../../jobs/presentation/job_providers.dart";
import "../../scholarships/data/scholarship_models.dart";
import "../../scholarships/presentation/scholarship_card.dart";
import "../../scholarships/presentation/scholarship_providers.dart";

final _savedJobsProvider = FutureProvider.autoDispose<List<JobCard>>((ref) async {
  final result = await ref.watch(jobRepositoryProvider).listSaved();
  return result.items;
});

final _savedScholarshipsProvider = FutureProvider.autoDispose<List<ScholarshipCard>>((ref) async {
  final result = await ref.watch(scholarshipRepositoryProvider).listSaved();
  return result.items;
});

class SavedItemsScreen extends ConsumerStatefulWidget {
  const SavedItemsScreen({super.key});

  @override
  ConsumerState<SavedItemsScreen> createState() => _SavedItemsScreenState();
}

class _SavedItemsScreenState extends ConsumerState<SavedItemsScreen> with SingleTickerProviderStateMixin {
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
    return Scaffold(
      appBar: AppBar(
        title: const Text("Saved"),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, 0, AppSpacing.pageH, AppSpacing.sm),
            child: CareerPillTabBar(controller: _tabController, tabs: const ["Jobs", "Scholarships"]),
          ),
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [_SavedJobsTab(), _SavedScholarshipsTab()],
      ),
    );
  }
}

class _SavedJobsTab extends ConsumerWidget {
  const _SavedJobsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobsAsync = ref.watch(_savedJobsProvider);
    return jobsAsync.when(
      loading: () => const SkeletonList(),
      error: (e, _) => ErrorState(title: "We couldn't load saved jobs", message: e.userMessage, onRetry: () => ref.invalidate(_savedJobsProvider)),
      data: (jobs) {
        if (jobs.isEmpty) {
          return EmptyState(
            icon: AppIcons.saved,
            title: "No saved jobs yet",
            message: "Bookmark jobs to compare them later and come back when you're ready to apply.",
            actionLabel: "Browse Opportunities",
            onAction: () => context.go("/home?tab=opportunities"),
          );
        }
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_savedJobsProvider),
          child: ListView.separated(
            padding: AppSpacing.page,
            itemCount: jobs.length,
            separatorBuilder: (context, index) => Gap.sm,
            itemBuilder: (context, index) {
              final job = jobs[index];
              return JobCardTile(
                job: job,
                onTap: () => context.push("/jobs/${job.slug}"),
                onToggleSave: () async {
                  // Unconditional unsave — every job on this screen is, by definition, saved.
                  await ref.read(jobRepositoryProvider).unsave(job.id);
                  ref.invalidate(_savedJobsProvider);
                },
              );
            },
          ),
        );
      },
    );
  }
}

class _SavedScholarshipsTab extends ConsumerWidget {
  const _SavedScholarshipsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scholarshipsAsync = ref.watch(_savedScholarshipsProvider);
    return scholarshipsAsync.when(
      loading: () => const SkeletonList(),
      error: (e, _) => ErrorState(
        title: "We couldn't load saved scholarships",
        message: e.userMessage,
        onRetry: () => ref.invalidate(_savedScholarshipsProvider),
      ),
      data: (scholarships) {
        if (scholarships.isEmpty) {
          return EmptyState(
            icon: AppIcons.saved,
            title: "No saved scholarships yet",
            message: "Bookmark scholarships to keep track of deadlines and requirements.",
            actionLabel: "Browse Opportunities",
            onAction: () => context.go("/home?tab=opportunities"),
          );
        }
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_savedScholarshipsProvider),
          child: ListView.separated(
            padding: AppSpacing.page,
            itemCount: scholarships.length,
            separatorBuilder: (context, index) => Gap.sm,
            itemBuilder: (context, index) {
              final scholarship = scholarships[index];
              return ScholarshipCardTile(
                scholarship: scholarship,
                onTap: () => context.push("/scholarships/${scholarship.slug}"),
                onToggleSave: () async {
                  // Unconditional unsave — every scholarship on this screen is, by definition, saved.
                  await ref.read(scholarshipRepositoryProvider).unsave(scholarship.id);
                  ref.invalidate(_savedScholarshipsProvider);
                },
              );
            },
          ),
        );
      },
    );
  }
}
