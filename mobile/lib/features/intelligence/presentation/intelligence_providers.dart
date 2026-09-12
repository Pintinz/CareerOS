import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/intelligence_models.dart";
import "../data/intelligence_repository.dart";

final intelligenceRepositoryProvider = Provider<IntelligenceRepository>((ref) {
  return IntelligenceRepository(apiClient: ref.watch(apiClientProvider));
});

class IntelligenceListState {
  const IntelligenceListState({
    this.items = const [],
    this.total = 0,
    this.page = 1,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
    this.category,
    this.followedOnly = false,
  });

  final List<IntelligenceCard> items;
  final int total;
  final int page;
  final bool isLoading;
  final bool isLoadingMore;
  final Object? error;
  final String? category;
  final bool followedOnly;

  bool get hasMore => items.length < total;

  IntelligenceListState copyWith({
    List<IntelligenceCard>? items,
    int? total,
    int? page,
    bool? isLoading,
    bool? isLoadingMore,
    Object? error,
    bool clearError = false,
    String? category,
    bool clearCategory = false,
    bool? followedOnly,
  }) =>
      IntelligenceListState(
        items: items ?? this.items,
        total: total ?? this.total,
        page: page ?? this.page,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        error: clearError ? null : (error ?? this.error),
        category: clearCategory ? null : (category ?? this.category),
        followedOnly: followedOnly ?? this.followedOnly,
      );
}

class IntelligenceListController extends Notifier<IntelligenceListState> {
  @override
  IntelligenceListState build() {
    Future.microtask(refresh);
    return const IntelligenceListState(isLoading: true);
  }

  IntelligenceRepository get _repo => ref.read(intelligenceRepositoryProvider);

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repo.list(page: 1, category: state.category, followedOnly: state.followedOnly);
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
      final result = await _repo.list(page: nextPage, category: state.category, followedOnly: state.followedOnly);
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

  Future<void> setCategory(String? category) async {
    state = state.copyWith(category: category, clearCategory: category == null);
    await refresh();
  }

  Future<void> setFollowedOnly(bool value) async {
    state = state.copyWith(followedOnly: value);
    await refresh();
  }
}

final intelligenceListProvider =
    NotifierProvider<IntelligenceListController, IntelligenceListState>(IntelligenceListController.new);

final intelligenceDetailProvider = FutureProvider.autoDispose.family<IntelligenceDetail, String>((ref, idOrSlug) {
  return ref.watch(intelligenceRepositoryProvider).getByIdOrSlug(idOrSlug);
});
