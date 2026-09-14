import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/job_models.dart";
import "../data/job_repository.dart";

final jobRepositoryProvider = Provider<JobRepository>((ref) {
  return JobRepository(apiClient: ref.watch(apiClientProvider));
});

class JobListState {
  const JobListState({
    this.items = const [],
    this.total = 0,
    this.page = 1,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
    this.filters = const JobFilters(),
  });

  final List<JobCard> items;
  final int total;
  final int page;
  final bool isLoading;
  final bool isLoadingMore;
  final Object? error;
  final JobFilters filters;

  bool get hasMore => items.length < total;

  JobListState copyWith({
    List<JobCard>? items,
    int? total,
    int? page,
    bool? isLoading,
    bool? isLoadingMore,
    Object? error,
    bool clearError = false,
    JobFilters? filters,
  }) =>
      JobListState(
        items: items ?? this.items,
        total: total ?? this.total,
        page: page ?? this.page,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        error: clearError ? null : (error ?? this.error),
        filters: filters ?? this.filters,
      );
}

/// The job-backed Opportunities feeds. Each has its own list state, and its base filter is always
/// applied on top of whatever the user refines. Graduate programmes are a real opportunity type,
/// classified at the source (never inferred from an experienced-hire title).
enum JobFeed {
  all,
  internships,
  graduatePrograms;

  JobFilters apply(JobFilters filters) => switch (this) {
        JobFeed.all => filters,
        JobFeed.internships => filters.copyWith(opportunityType: "INTERNSHIP"),
        JobFeed.graduatePrograms => filters.copyWith(opportunityType: "GRADUATE_PROGRAM"),
      };
}

class JobListController extends FamilyNotifier<JobListState, JobFeed> {
  @override
  JobListState build(JobFeed arg) {
    Future.microtask(refresh);
    return const JobListState(isLoading: true);
  }

  JobRepository get _repo => ref.read(jobRepositoryProvider);

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repo.list(page: 1, filters: arg.apply(state.filters));
      state = state.copyWith(items: result.items, total: result.total, page: 1, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e);
    }
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;
    state = state.copyWith(isLoadingMore: true);
    try {
      final nextPage = state.page + 1;
      final result = await _repo.list(page: nextPage, filters: arg.apply(state.filters));
      state = state.copyWith(items: [...state.items, ...result.items], total: result.total, page: nextPage, isLoadingMore: false);
    } catch (e) {
      state = state.copyWith(isLoadingMore: false, error: e);
    }
  }

  Future<void> updateFilters(JobFilters filters) async {
    state = state.copyWith(filters: filters);
    await refresh();
  }

  Future<void> toggleSave(String jobId) async {
    final index = state.items.indexWhere((j) => j.id == jobId);
    if (index == -1) return;
    final job = state.items[index];
    // copyWith keeps every field (demo flag, availability, opportunity type) — only the save state flips.
    final updated = job.copyWith(isSaved: !job.isSaved);
    final newItems = [...state.items];
    newItems[index] = updated;
    state = state.copyWith(items: newItems);

    try {
      if (updated.isSaved) {
        await _repo.save(jobId);
      } else {
        await _repo.unsave(jobId);
      }
    } catch (_) {
      // Revert on failure — optimistic update didn't stick.
      final revertedItems = [...state.items];
      revertedItems[index] = job;
      state = state.copyWith(items: revertedItems);
    }
  }
}

final jobFeedProvider = NotifierProvider.family<JobListController, JobListState, JobFeed>(JobListController.new);

/// The main "Jobs" feed.
final jobListProvider = jobFeedProvider(JobFeed.all);

final jobDetailProvider = FutureProvider.autoDispose.family<JobDetail, String>((ref, idOrSlug) {
  return ref.watch(jobRepositoryProvider).getByIdOrSlug(idOrSlug);
});
