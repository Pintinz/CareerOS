import "../../../core/network/api_client.dart";
import "application_models.dart";

class ApplicationRepository {
  ApplicationRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<({List<Application> items, int total})> list({int page = 1, ApplicationStage? stage}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/applications",
      queryParameters: {"page": page, "page_size": 20, if (stage != null) "stage": stage.wireValue},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => Application.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<Application> get(String id) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/applications/$id");
    return Application.fromJson(response.data!);
  }

  Future<Application> createFromJob(String jobId, {ApplicationStage stage = ApplicationStage.applied}) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/applications",
      data: {"job_id": jobId, "current_stage": stage.wireValue},
    );
    return Application.fromJson(response.data!);
  }

  Future<Application> createManual({
    required String companyName,
    required String roleTitle,
    String? location,
    String? jobUrl,
    ApplicationStage stage = ApplicationStage.saved,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/applications",
      data: {
        "company_name": companyName,
        "role_title": roleTitle,
        if (location != null && location.isNotEmpty) "location": location,
        if (jobUrl != null && jobUrl.isNotEmpty) "job_url": jobUrl,
        "current_stage": stage.wireValue,
      },
    );
    return Application.fromJson(response.data!);
  }

  Future<Application> updateStage(String id, ApplicationStage stage, {String? note}) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/applications/$id/stage",
      data: {"stage": stage.wireValue, if (note != null && note.isNotEmpty) "note": note},
    );
    return Application.fromJson(response.data!);
  }

  Future<ApplicationNote> addNote(String id, String text) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/applications/$id/notes", data: {"text": text});
    return ApplicationNote.fromJson(response.data!);
  }

  Future<void> delete(String id) => _apiClient.delete("/applications/$id");

  Future<int> activeCount() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/me/applications-summary");
    return response.data!["active_applications"] as int;
  }
}
