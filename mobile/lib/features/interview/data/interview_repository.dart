import "../../../core/network/api_client.dart";
import "interview_models.dart";

class InterviewRepository {
  InterviewRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<List<InterviewCategory>> listCategories() async {
    final response = await _apiClient.get<List<dynamic>>("/interview/categories");
    return response.data!.map((e) => InterviewCategory.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<InterviewSessionDetail> createSession({
    required InterviewSessionMode mode,
    List<String> categories = const [],
    Map<String, int>? categoryCounts,
    String difficulty = "MIXED",
    int questionCount = 10,
    int? timePerQuestionSeconds,
    String? applicationId,
    String? jobId,
    String? companyId,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/interview/sessions",
      data: {
        "mode": mode.wireValue,
        "categories": categories,
        if (categoryCounts != null) "category_counts": categoryCounts,
        "difficulty": difficulty,
        "question_count": questionCount,
        if (timePerQuestionSeconds != null) "time_per_question_seconds": timePerQuestionSeconds,
        if (applicationId != null) "application_id": applicationId,
        if (jobId != null) "job_id": jobId,
        if (companyId != null) "company_id": companyId,
      },
    );
    return InterviewSessionDetail.fromJson(response.data!);
  }

  Future<InterviewSessionDetail> getSession(String sessionId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/interview/sessions/$sessionId");
    return InterviewSessionDetail.fromJson(response.data!);
  }

  Future<({List<InterviewSessionSummary> items, int total})> listSessions({int page = 1}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/interview/sessions", queryParameters: {"page": page, "page_size": 20},
    );
    final data = response.data!;
    return (
      items: (data["items"] as List).map((e) => InterviewSessionSummary.fromJson(e as Map<String, dynamic>)).toList(),
      total: data["total"] as int,
    );
  }

  Future<SessionQuestion> updateAnswer({
    required String sessionId,
    required String questionId,
    String? answerText,
    String? notes,
    String? audioPath,
    int? audioDurationSeconds,
    int? selfRating,
    bool? usedStar,
    bool? gaveMeasurableResult,
    bool? answeredExactQuestion,
    bool? isSkipped,
    bool? isMarkedPracticed,
    bool? isSaved,
  }) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/interview/sessions/$sessionId/answers/$questionId",
      data: {
        if (answerText != null) "answer_text": answerText,
        if (notes != null) "notes": notes,
        if (audioPath != null) "audio_path": audioPath,
        if (audioDurationSeconds != null) "audio_duration_seconds": audioDurationSeconds,
        if (selfRating != null) "self_rating": selfRating,
        if (usedStar != null) "used_star": usedStar,
        if (gaveMeasurableResult != null) "gave_measurable_result": gaveMeasurableResult,
        if (answeredExactQuestion != null) "answered_exact_question": answeredExactQuestion,
        if (isSkipped != null) "is_skipped": isSkipped,
        if (isMarkedPracticed != null) "is_marked_practiced": isMarkedPracticed,
        if (isSaved != null) "is_saved": isSaved,
      },
    );
    return SessionQuestion.fromJson(response.data!);
  }

  Future<SessionCompletion> completeSession(String sessionId) async {
    final response = await _apiClient.post<Map<String, dynamic>>("/interview/sessions/$sessionId/complete");
    return SessionCompletion.fromJson(response.data!);
  }

  Future<InterviewAnalytics> getAnalytics() async {
    final response = await _apiClient.get<Map<String, dynamic>>("/interview/analytics");
    return InterviewAnalytics.fromJson(response.data!);
  }

  Future<Readiness> getReadiness({String? applicationId}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/interview/readiness", queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return Readiness.fromJson(response.data!);
  }

  Future<CompanyPrep> getCompanyPrep(String applicationId) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/interview/prep/company", queryParameters: {"application_id": applicationId},
    );
    return CompanyPrep.fromJson(response.data!);
  }

  Future<PreparationProgress> getPreparationProgress({String? applicationId}) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      "/interview/prep/progress", queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return PreparationProgress.fromJson(response.data!);
  }

  Future<PreparationProgress> updateChecklistItem({required String key, required bool isDone, String? applicationId}) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/interview/prep/checklist",
      data: {"key": key, "is_done": isDone},
      queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return PreparationProgress.fromJson(response.data!);
  }

  Future<PreparationProgress> updateQuestionToAsk({
    String? id, String? text, String? category, String? status, bool isCustom = false, String? applicationId,
  }) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/interview/prep/questions-to-ask",
      data: {
        if (id != null) "id": id,
        if (text != null) "text": text,
        if (category != null) "category": category,
        "status": status,
        "is_custom": isCustom,
      },
      queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return PreparationProgress.fromJson(response.data!);
  }

  Future<PreparationProgress> updateTopicReview({required String topicSlug, required bool isReviewed, String? applicationId}) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/interview/prep/topics",
      data: {"topic_slug": topicSlug, "is_reviewed": isReviewed},
      queryParameters: applicationId != null ? {"application_id": applicationId} : null,
    );
    return PreparationProgress.fromJson(response.data!);
  }

  Future<List<StarStory>> listStarStories({String? category}) async {
    final response = await _apiClient.get<List<dynamic>>(
      "/star-stories", queryParameters: category != null ? {"category": category} : null,
    );
    return response.data!.map((e) => StarStory.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<StarStory> getStarStory(String storyId) async {
    final response = await _apiClient.get<Map<String, dynamic>>("/star-stories/$storyId");
    return StarStory.fromJson(response.data!);
  }

  Future<StarStory> createStarStory({
    required String title,
    required StarCategory category,
    String? situation,
    String? task,
    String? action,
    String? result,
    String? lessons,
    List<String> skillsDemonstrated = const [],
    String? metrics,
    String? companyContext,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      "/star-stories",
      data: {
        "title": title,
        "category": category.wireValue,
        "situation": situation,
        "task": task,
        "action": action,
        "result": result,
        "lessons": lessons,
        "skills_demonstrated": skillsDemonstrated,
        "metrics": metrics,
        "company_context": companyContext,
      },
    );
    return StarStory.fromJson(response.data!);
  }

  Future<StarStory> updateStarStory(
    String storyId, {
    String? title,
    StarCategory? category,
    String? situation,
    String? task,
    String? action,
    String? result,
    String? lessons,
    List<String>? skillsDemonstrated,
    String? metrics,
    String? companyContext,
  }) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      "/star-stories/$storyId",
      data: {
        if (title != null) "title": title,
        if (category != null) "category": category.wireValue,
        if (situation != null) "situation": situation,
        if (task != null) "task": task,
        if (action != null) "action": action,
        if (result != null) "result": result,
        if (lessons != null) "lessons": lessons,
        if (skillsDemonstrated != null) "skills_demonstrated": skillsDemonstrated,
        if (metrics != null) "metrics": metrics,
        if (companyContext != null) "company_context": companyContext,
      },
    );
    return StarStory.fromJson(response.data!);
  }

  Future<void> deleteStarStory(String storyId) => _apiClient.delete("/star-stories/$storyId");
}
