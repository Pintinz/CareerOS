import "package:dio/dio.dart";

import "../../../core/network/api_client.dart";
import "ats_models.dart";

class AtsRepository {
  AtsRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<CvDocument> uploadCv({
    required String filePath,
    required String filename,
    String? name,
    bool isPrimary = false,
  }) async {
    final formData = FormData.fromMap({
      "file": await MultipartFile.fromFile(filePath, filename: filename),
      if (name != null) "name": name,
      "is_primary": isPrimary.toString(),
    });
    final response = await _apiClient.post<Map<String, dynamic>>("/ats/cv", data: formData);
    return CvDocument.fromJson(response.data!);
  }

  Future<List<CvDocument>> listCvs() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/ats/cv");
    return (response.data!["items"] as List).map((e) => CvDocument.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> deleteCv(String cvId) => _apiClient.delete("/ats/cv/$cvId");

  Future<AtsAnalysis> analyze({
    String? cvDocumentId,
    String? cvText,
    String? jobId,
    String? jobDescription,
    String? jobTitle,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/ats/analyze",
      data: {
        if (cvDocumentId != null) "cv_document_id": cvDocumentId,
        if (cvText != null) "cv_text": cvText,
        if (jobId != null) "job_id": jobId,
        if (jobDescription != null) "job_description": jobDescription,
        if (jobTitle != null) "job_title": jobTitle,
      },
    );
    return AtsAnalysis.fromJson(response.data!);
  }

  Future<({List<AtsAnalysis> items, int total})> listAnalyses({int page = 1}) async {
    final response =
        await _apiClient.get<Map<String, dynamic>>("/ats/analyses", queryParameters: {"page": page, "page_size": 20});
    final data = response.data!;
    final items = (data["items"] as List).map((e) => AtsAnalysis.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }
}
