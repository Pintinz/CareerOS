import "../../../core/network/api_client.dart";
import "aptitude_models.dart";

class AptitudeRepository {
  AptitudeRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<List<QuestionCategory>> listCategories() async {
    final response = await _apiClient.get<List<dynamic>>("/aptitude/categories");
    return response.data!.map((e) => QuestionCategory.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<TestSessionDetail> createSession({
    required TestMode mode,
    required List<String> sections,
    required String difficulty,
    required int questionCount,
    required String timing,
    int? timeLimitMinutes,
    String? applicationId,
    String? jobId,
    List<String>? topicSlugs,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/aptitude/sessions",
      data: {
        "mode": mode.wireValue,
        "sections": sections,
        "difficulty": difficulty,
        "question_count": questionCount,
        "timing": timing,
        if (timeLimitMinutes != null) "time_limit_minutes": timeLimitMinutes,
        if (applicationId != null) "application_id": applicationId,
        if (jobId != null) "job_id": jobId,
        if (topicSlugs != null) "topic_slugs": topicSlugs,
      },
    );
    return TestSessionDetail.fromJson(response.data!);
  }

  Future<TestSessionDetail> getSession(String sessionId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/aptitude/sessions/$sessionId");
    return TestSessionDetail.fromJson(response.data!);
  }

  Future<({List<TestSessionSummary> items, int total})> listSessions({int page = 1, String? status}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/aptitude/sessions",
      queryParameters: {"page": page, "page_size": 20, if (status != null) "status": status},
    );
    final data = response.data!;
    final items = (data["items"] as List).map((e) => TestSessionSummary.fromJson(e as Map<String, dynamic>)).toList();
    return (items: items, total: data["total"] as int);
  }

  Future<SessionQuestion> updateAnswer({
    required String sessionId,
    required String questionId,
    List<String>? selectedOptionIds,
    double? answerNumericValue,
    int? timeSpentSeconds,
  }) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/aptitude/sessions/$sessionId/answers/$questionId",
      data: {
        "selected_option_ids": selectedOptionIds,
        "answer_numeric_value": answerNumericValue,
        "time_spent_seconds": timeSpentSeconds,
      },
    );
    return SessionQuestion.fromJson(response.data!);
  }

  Future<SessionQuestion> toggleFlag({required String sessionId, required String questionId}) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/aptitude/sessions/$sessionId/flag/$questionId");
    return SessionQuestion.fromJson(response.data!);
  }

  Future<TestResult> submit(String sessionId) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/aptitude/sessions/$sessionId/submit");
    return TestResult.fromJson(response.data!);
  }

  Future<TestResult> getResults(String sessionId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/aptitude/sessions/$sessionId/results");
    return TestResult.fromJson(response.data!);
  }

  Future<SessionReview> getReview(String sessionId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/aptitude/sessions/$sessionId/review");
    return SessionReview.fromJson(response.data!);
  }

  Future<AptitudeAnalytics> getAnalytics() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/aptitude/analytics");
    return AptitudeAnalytics.fromJson(response.data!);
  }

  Future<Recommendations> getRecommendations() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/aptitude/recommendations");
    return Recommendations.fromJson(response.data!);
  }
}
