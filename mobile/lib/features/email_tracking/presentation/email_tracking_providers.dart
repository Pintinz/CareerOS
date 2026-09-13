import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../data/email_tracking_models.dart";
import "../data/email_tracking_repository.dart";

final emailTrackingRepositoryProvider = Provider<EmailTrackingRepository>((ref) {
  return EmailTrackingRepository(apiClient: ref.watch(apiClientProvider));
});

final providerAvailabilityProvider = FutureProvider.autoDispose<ProviderAvailability>((ref) {
  return ref.watch(emailTrackingRepositoryProvider).getProviderAvailability();
});

final emailConnectionsProvider = FutureProvider.autoDispose<List<EmailConnection>>((ref) {
  return ref.watch(emailTrackingRepositoryProvider).listConnections();
});

final recruitmentEventsProvider = FutureProvider.autoDispose<List<RecruitmentEmailEvent>>((ref) {
  return ref.watch(emailTrackingRepositoryProvider).listEvents();
});

/// Home dashboard's "Application Updates" card (spec §31) — only the count, never subject/body.
final needsReviewCountProvider = FutureProvider.autoDispose<int>((ref) async {
  final events = await ref.watch(recruitmentEventsProvider.future);
  return events.where((e) => e.needsReview).length;
});

final applicationRecruitmentEventsProvider = FutureProvider.autoDispose.family<List<RecruitmentEmailEvent>, String>((ref, applicationId) {
  return ref.watch(emailTrackingRepositoryProvider).listEvents(applicationId: applicationId);
});

final recruitmentEventDetailProvider = FutureProvider.autoDispose.family<RecruitmentEmailEvent, String>((ref, eventId) {
  return ref.watch(emailTrackingRepositoryProvider).getEvent(eventId);
});
