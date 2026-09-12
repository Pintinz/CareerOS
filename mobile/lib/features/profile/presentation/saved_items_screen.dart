import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
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
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppColors.blue,
          unselectedLabelColor: AppColors.muted,
          indicatorColor: AppColors.blue,
          tabs: const [Tab(text: "Jobs"), Tab(text: "Scholarships")],
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
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text(e.userMessage)),
      data: (jobs) {
        if (jobs.isEmpty) {
          return const PhasePendingPlaceholder(
            icon: Icons.bookmark_border,
            title: "No saved jobs",
            message: "Tap the bookmark icon on a job to save it here.",
          );
        }
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_savedJobsProvider),
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: jobs.length,
            separatorBuilder: (context, index) => const SizedBox(height: 12),
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
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text(e.userMessage)),
      data: (scholarships) {
        if (scholarships.isEmpty) {
          return const PhasePendingPlaceholder(
            icon: Icons.bookmark_border,
            title: "No saved scholarships",
            message: "Tap the bookmark icon on a scholarship to save it here.",
          );
        }
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_savedScholarshipsProvider),
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: scholarships.length,
            separatorBuilder: (context, index) => const SizedBox(height: 12),
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
