import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/ats_models.dart";
import "../data/ats_repository.dart";

final atsRepositoryProvider = Provider<AtsRepository>((ref) {
  return AtsRepository(apiClient: ref.watch(apiClientProvider));
});

final cvListProvider = FutureProvider.autoDispose<List<CvDocument>>((ref) {
  return ref.watch(atsRepositoryProvider).listCvs();
});

final atsAnalysisHistoryProvider = FutureProvider.autoDispose<List<AtsAnalysis>>((ref) async {
  final result = await ref.watch(atsRepositoryProvider).listAnalyses();
  return result.items;
});

/// Drives the analyze action itself (upload happens separately via cvListProvider refresh).
class AtsAnalysisController extends AsyncNotifier<AtsAnalysis?> {
  @override
  AtsAnalysis? build() => null;

  Future<void> analyze({
    String? cvDocumentId,
    String? cvText,
    String? jobId,
    String? jobDescription,
    String? jobTitle,
  }) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(atsRepositoryProvider).analyze(
            cvDocumentId: cvDocumentId,
            cvText: cvText,
            jobId: jobId,
            jobDescription: jobDescription,
            jobTitle: jobTitle,
          ),
    );
  }

  void reset() => state = const AsyncData(null);
}

final atsAnalysisControllerProvider = AsyncNotifierProvider<AtsAnalysisController, AtsAnalysis?>(
  AtsAnalysisController.new,
);
