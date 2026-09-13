import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/scholarship_models.dart";
import "../data/scholarship_repository.dart";

final scholarshipRepositoryProvider = Provider<ScholarshipRepository>((ref) {
  return ScholarshipRepository(apiClient: ref.watch(apiClientProvider));
});

class ScholarshipListState {
  const ScholarshipListState({
    this.items = const [],
    this.total = 0,
    this.page = 1,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
    this.filters = const ScholarshipFilters(),
  });

  final List<ScholarshipCard> items;
  final int total;
  final int page;
  final bool isLoading;
  final bool isLoadingMore;
  final Object? error;
  final ScholarshipFilters filters;

  bool get hasMore => items.length < total;

  ScholarshipListState copyWith({
    List<ScholarshipCard>? items,
    int? total,
    int? page,
    bool? isLoading,
    bool? isLoadingMore,
    Object? error,
    bool clearError = false,
    ScholarshipFilters? filters,
  }) =>
      ScholarshipListState(
        items: items ?? this.items,
        total: total ?? this.total,
        page: page ?? this.page,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        error: clearError ? null : (error ?? this.error),
        filters: filters ?? this.filters,
      );
}

class ScholarshipListController extends Notifier<ScholarshipListState> {
  @override
  ScholarshipListState build() {
    Future.microtask(refresh);
    return const ScholarshipListState(isLoading: true);
  }

  ScholarshipRepository get _repo => ref.read(scholarshipRepositoryProvider);

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repo.list(page: 1, filters: state.filters);
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
      final result = await _repo.list(page: nextPage, filters: state.filters);
      state = state.copyWith(
        items: [...state.items, ...result.items],
        total: result.total,
        page: nextPage,
        isLoadingMore: false,
      );
    } catch (e) {
      state = state.copyWith(isLoadingMore: false, error: e);
    }
  }

  Future<void> updateFilters(ScholarshipFilters filters) async {
    state = state.copyWith(filters: filters);
    await refresh();
  }

  Future<void> toggleSave(String scholarshipId) async {
    final index = state.items.indexWhere((s) => s.id == scholarshipId);
    if (index == -1) return;
    final item = state.items[index];
    final updated = ScholarshipCard(
      id: item.id,
      slug: item.slug,
      name: item.name,
      organization: item.organization,
      country: item.country,
      degreeLevels: item.degreeLevels,
      fundingType: item.fundingType,
      applicationDeadline: item.applicationDeadline,
      thumbnailUrl: item.thumbnailUrl,
      isVerified: item.isVerified,
      isFeatured: item.isFeatured,
      isSaved: !item.isSaved,
      isDemo: item.isDemo,
    );
    final newItems = [...state.items];
    newItems[index] = updated;
    state = state.copyWith(items: newItems);

    try {
      if (updated.isSaved) {
        await _repo.save(scholarshipId);
      } else {
        await _repo.unsave(scholarshipId);
      }
    } catch (_) {
      final revertedItems = [...state.items];
      revertedItems[index] = item;
      state = state.copyWith(items: revertedItems);
    }
  }
}

final scholarshipListProvider =
    NotifierProvider<ScholarshipListController, ScholarshipListState>(ScholarshipListController.new);

final scholarshipDetailProvider = FutureProvider.autoDispose.family<ScholarshipDetail, String>((ref, idOrSlug) {
  return ref.watch(scholarshipRepositoryProvider).getByIdOrSlug(idOrSlug);
});
