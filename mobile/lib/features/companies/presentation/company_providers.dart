import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/company_models.dart";
import "../data/company_repository.dart";

final companyRepositoryProvider = Provider<CompanyRepository>((ref) {
  return CompanyRepository(apiClient: ref.watch(apiClientProvider));
});

final companyDetailProvider = FutureProvider.autoDispose.family<Company, String>((ref, idOrSlug) {
  return ref.watch(companyRepositoryProvider).getByIdOrSlug(idOrSlug);
});

class CompanyFollowController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> toggle(String companyId, bool currentlyFollowing) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      if (currentlyFollowing) {
        await ref.read(companyRepositoryProvider).unfollow(companyId);
      } else {
        await ref.read(companyRepositoryProvider).follow(companyId);
      }
    });
  }
}

final companyFollowControllerProvider = AsyncNotifierProvider<CompanyFollowController, void>(
  CompanyFollowController.new,
);
