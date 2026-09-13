import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/email_tracking/data/email_tracking_models.dart';
import 'package:careeros/features/email_tracking/data/email_tracking_repository.dart';

/// Test double for [EmailTrackingRepository] — same rationale as every other Fake*Repository in
/// this test suite: overrides every network-hitting method so widget tests never touch a real
/// ApiClient/Dio.
class FakeEmailTrackingRepository extends EmailTrackingRepository {
  FakeEmailTrackingRepository() : super(apiClient: ApiClient());

  ProviderAvailability availability = const ProviderAvailability(
    gmailAvailable: false,
    outlookAvailable: false,
    forwardEmailAvailable: false,
  );
  List<EmailConnection> connections = [];
  List<RecruitmentEmailEvent> events = [];
  final List<String> disconnectCalls = [];
  final List<String> confirmCalls = [];
  final List<String> ignoreCalls = [];
  final List<(String eventId, String applicationId)> assignCalls = [];
  String? nextAuthorizationUrl = 'https://mock-provider.careeros.test/authorize';
  String? nextPrepHint;

  @override
  Future<ProviderAvailability> getProviderAvailability() async => availability;

  @override
  Future<List<EmailConnection>> listConnections() async => connections;

  @override
  Future<String> startConnectGmail() async => nextAuthorizationUrl!;

  @override
  Future<String> startConnectOutlook() async => nextAuthorizationUrl!;

  @override
  Future<void> disconnect(String connectionId) async {
    disconnectCalls.add(connectionId);
    connections = connections.where((c) => c.id != connectionId).toList();
  }

  @override
  Future<int> deleteTrackingData() async {
    final count = events.length;
    events = [];
    return count;
  }

  @override
  Future<List<RecruitmentEmailEvent>> listEvents({String? applicationId}) async {
    if (applicationId == null) return events;
    return events.where((e) => e.matchedApplicationId == applicationId).toList();
  }

  @override
  Future<RecruitmentEmailEvent> getEvent(String eventId) async => events.firstWhere((e) => e.id == eventId);

  @override
  Future<RecruitmentEmailEvent> confirmEvent(String eventId) async {
    confirmCalls.add(eventId);
    final index = events.indexWhere((e) => e.id == eventId);
    final updated = _withStatus(events[index], RecruitmentEventStatus.confirmed);
    events[index] = updated;
    return updated;
  }

  @override
  Future<RecruitmentEmailEvent> ignoreEvent(String eventId) async {
    ignoreCalls.add(eventId);
    final index = events.indexWhere((e) => e.id == eventId);
    final updated = _withStatus(events[index], RecruitmentEventStatus.ignored);
    events[index] = updated;
    return updated;
  }

  @override
  Future<RecruitmentEmailEvent> assignApplication(String eventId, String applicationId) async {
    assignCalls.add((eventId, applicationId));
    final index = events.indexWhere((e) => e.id == eventId);
    final updated = _withMatch(events[index], applicationId);
    events[index] = updated;
    return updated;
  }

  @override
  Future<String?> getPrepHint(String eventId) async => nextPrepHint;

  RecruitmentEmailEvent _withStatus(RecruitmentEmailEvent event, RecruitmentEventStatus status) => RecruitmentEmailEvent(
        id: event.id,
        provider: event.provider,
        senderEmail: event.senderEmail,
        senderDomain: event.senderDomain,
        senderName: event.senderName,
        subject: event.subject,
        evidenceExcerpt: event.evidenceExcerpt,
        receivedAt: event.receivedAt,
        matchedApplicationId: event.matchedApplicationId,
        candidateApplicationIds: event.candidateApplicationIds,
        detectedStage: event.detectedStage,
        confidenceScore: event.confidenceScore,
        confidenceLabel: event.confidenceLabel,
        evidence: event.evidence,
        status: status,
        createdAt: event.createdAt,
        reviewedAt: DateTime.now(),
      );

  RecruitmentEmailEvent _withMatch(RecruitmentEmailEvent event, String applicationId) => RecruitmentEmailEvent(
        id: event.id,
        provider: event.provider,
        senderEmail: event.senderEmail,
        senderDomain: event.senderDomain,
        senderName: event.senderName,
        subject: event.subject,
        evidenceExcerpt: event.evidenceExcerpt,
        receivedAt: event.receivedAt,
        matchedApplicationId: applicationId,
        candidateApplicationIds: const [],
        detectedStage: event.detectedStage,
        confidenceScore: event.confidenceScore,
        confidenceLabel: event.confidenceLabel,
        evidence: event.evidence,
        status: RecruitmentEventStatus.suggested,
        createdAt: event.createdAt,
        reviewedAt: event.reviewedAt,
      );
}

RecruitmentEmailEvent buildSampleRecruitmentEvent({
  String id = 'event-1',
  EmailProvider provider = EmailProvider.gmail,
  String senderDomain = 'exxonmobil.com',
  ApplicationStage? detectedStage,
  String? matchedApplicationId,
  List<String> candidateApplicationIds = const [],
  RecruitmentEventStatus status = RecruitmentEventStatus.suggested,
  String confidenceLabel = 'HIGH',
  List<String> evidence = const ['"invited to complete an online assessment" was detected'],
}) {
  return RecruitmentEmailEvent(
    id: id,
    provider: provider,
    senderEmail: 'recruiting@$senderDomain',
    senderDomain: senderDomain,
    senderName: 'ExxonMobil Recruiting',
    subject: 'Online assessment invitation',
    evidenceExcerpt: 'invited to complete an online assessment',
    receivedAt: DateTime(2026, 9, 13),
    matchedApplicationId: matchedApplicationId,
    candidateApplicationIds: candidateApplicationIds,
    detectedStage: detectedStage ?? ApplicationStage.aptitudeTest,
    confidenceScore: 0.8,
    confidenceLabel: confidenceLabel,
    evidence: evidence,
    status: status,
    createdAt: DateTime(2026, 9, 13),
  );
}
