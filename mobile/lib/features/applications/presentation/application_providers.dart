import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/application_models.dart";
import "../data/application_repository.dart";

final applicationRepositoryProvider = Provider<ApplicationRepository>((ref) {
  return ApplicationRepository(apiClient: ref.watch(apiClientProvider));
});

class ApplicationListState {
  const ApplicationListState({
    this.items = const [],
    this.total = 0,
    this.isLoading = false,
    this.error,
    this.stageFilter,
  });

  final List<Application> items;
  final int total;
  final bool isLoading;
  final Object? error;
  final ApplicationStage? stageFilter;

  ApplicationListState copyWith({
    List<Application>? items,
    int? total,
    bool? isLoading,
    Object? error,
    bool clearError = false,
    ApplicationStage? stageFilter,
    bool clearStageFilter = false,
  }) =>
      ApplicationListState(
        items: items ?? this.items,
        total: total ?? this.total,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        stageFilter: clearStageFilter ? null : (stageFilter ?? this.stageFilter),
      );
}

class ApplicationListController extends Notifier<ApplicationListState> {
  @override
  ApplicationListState build() {
    Future.microtask(refresh);
    return const ApplicationListState(isLoading: true);
  }

  ApplicationRepository get _repo => ref.read(applicationRepositoryProvider);

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repo.list(stage: state.stageFilter);
      state = state.copyWith(items: result.items, total: result.total, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e);
    }
  }

  Future<void> setStageFilter(ApplicationStage? stage) async {
    state = state.copyWith(stageFilter: stage, clearStageFilter: stage == null);
    await refresh();
  }
}

final applicationListProvider =
    NotifierProvider<ApplicationListController, ApplicationListState>(ApplicationListController.new);

final applicationDetailProvider = FutureProvider.autoDispose.family<Application, String>((ref, id) {
  return ref.watch(applicationRepositoryProvider).get(id);
});

final activeApplicationsCountProvider = FutureProvider.autoDispose<int>((ref) {
  return ref.watch(applicationRepositoryProvider).activeCount();
});
