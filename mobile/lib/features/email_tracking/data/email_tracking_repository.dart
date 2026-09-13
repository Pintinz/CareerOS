import "../../../core/network/api_client.dart";
import "email_tracking_models.dart";

class EmailTrackingRepository {
  EmailTrackingRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<ProviderAvailability> getProviderAvailability() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/email-tracking/providers");
    return ProviderAvailability.fromJson(response.data!);
  }

  Future<List<EmailConnection>> listConnections() async {
    final response = await _apiClient.get<List<dynamic>>("/email-tracking/connections");
    return response.data!.map((e) => EmailConnection.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<String> startConnectGmail() async {
    final response = await _apiClient.post<Map<String, dynamic>>("/email-tracking/gmail/connect");
    return response.data!["authorization_url"] as String;
  }

  Future<String> startConnectOutlook() async {
    final response = await _apiClient.post<Map<String, dynamic>>("/email-tracking/outlook/connect");
    return response.data!["authorization_url"] as String;
  }

  Future<void> disconnect(String connectionId) => _apiClient.delete("/email-tracking/connections/$connectionId");

  Future<int> deleteTrackingData() async {
    final response = await _apiClient.delete<Map<String, dynamic>>("/email-tracking/data");
    return response.data!["deleted_events"] as int;
  }

  Future<List<RecruitmentEmailEvent>> listEvents({String? applicationId}) async {
    final response = await _apiClient.get<List<dynamic>>(
      "/email-tracking/events",
      queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return response.data!.map((e) => RecruitmentEmailEvent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<RecruitmentEmailEvent> getEvent(String eventId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/email-tracking/events/$eventId");
    return RecruitmentEmailEvent.fromJson(response.data!);
  }

  Future<RecruitmentEmailEvent> confirmEvent(String eventId) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/email-tracking/events/$eventId/confirm");
    return RecruitmentEmailEvent.fromJson(response.data!);
  }

  Future<RecruitmentEmailEvent> ignoreEvent(String eventId) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/email-tracking/events/$eventId/ignore");
    return RecruitmentEmailEvent.fromJson(response.data!);
  }

  Future<RecruitmentEmailEvent> assignApplication(String eventId, String applicationId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/email-tracking/events/$eventId/assign-application",
      data: {"application_id": applicationId},
    );
    return RecruitmentEmailEvent.fromJson(response.data!);
  }

  Future<String?> getPrepHint(String eventId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/email-tracking/events/$eventId/prep-hint");
    return response.data!["prep_flow"] as String?;
  }
}
