import "dart:convert";

import "package:shared_preferences/shared_preferences.dart";

import "interview_models.dart";

/// A queued local answer mutation made while offline — same rationale as the aptitude engine's
/// `PendingMutation` (spec §36): the backend stays the authority, this is just a best-effort
/// local mirror replayed once connectivity returns.
class PendingInterviewMutation {
  const PendingInterviewMutation({
    required this.sessionId,
    required this.questionId,
    this.answerText,
    this.notes,
    this.audioPath,
    this.audioDurationSeconds,
    this.selfRating,
    this.usedStar,
    this.gaveMeasurableResult,
    this.answeredExactQuestion,
    this.isSkipped,
    this.isMarkedPracticed,
    this.isSaved,
  });

  final String sessionId;
  final String questionId;
  final String? answerText;
  final String? notes;
  final String? audioPath;
  final int? audioDurationSeconds;
  final int? selfRating;
  final bool? usedStar;
  final bool? gaveMeasurableResult;
  final bool? answeredExactQuestion;
  final bool? isSkipped;
  final bool? isMarkedPracticed;
  final bool? isSaved;

  Map<String, dynamic> toJson() => {
        "session_id": sessionId,
        "question_id": questionId,
        "answer_text": answerText,
        "notes": notes,
        "audio_path": audioPath,
        "audio_duration_seconds": audioDurationSeconds,
        "self_rating": selfRating,
        "used_star": usedStar,
        "gave_measurable_result": gaveMeasurableResult,
        "answered_exact_question": answeredExactQuestion,
        "is_skipped": isSkipped,
        "is_marked_practiced": isMarkedPracticed,
        "is_saved": isSaved,
      };

  factory PendingInterviewMutation.fromJson(Map<String, dynamic> json) => PendingInterviewMutation(
        sessionId: json["session_id"] as String,
        questionId: json["question_id"] as String,
        answerText: json["answer_text"] as String?,
        notes: json["notes"] as String?,
        audioPath: json["audio_path"] as String?,
        audioDurationSeconds: json["audio_duration_seconds"] as int?,
        selfRating: json["self_rating"] as int?,
        usedStar: json["used_star"] as bool?,
        gaveMeasurableResult: json["gave_measurable_result"] as bool?,
        answeredExactQuestion: json["answered_exact_question"] as bool?,
        isSkipped: json["is_skipped"] as bool?,
        isMarkedPracticed: json["is_marked_practiced"] as bool?,
        isSaved: json["is_saved"] as bool?,
      );
}

/// Local persistence for an in-progress interview practice/mock session (spec §36) — mirrors
/// [AptitudeOfflineCache]'s approach (SharedPreferences, one JSON blob per active session) rather
/// than the unused Drift dependency; see ARCHITECTURE.md.
class InterviewOfflineCache {
  InterviewOfflineCache(this._prefs);

  final SharedPreferences _prefs;

  static Future<InterviewOfflineCache> create() async => InterviewOfflineCache(await SharedPreferences.getInstance());

  static const _sessionKeyPrefix = "interview_session_";
  static const _mutationsKey = "interview_pending_mutations";

  Future<void> saveSession(InterviewSessionDetail detail) =>
      _prefs.setString("$_sessionKeyPrefix${detail.id}", jsonEncode(_sessionToJson(detail)));

  Future<void> clearSession(String sessionId) => _prefs.remove("$_sessionKeyPrefix$sessionId");

  List<PendingInterviewMutation> pendingMutationsFor(String sessionId) =>
      _allMutations().where((m) => m.sessionId == sessionId).toList();

  Future<void> enqueueMutation(PendingInterviewMutation mutation) async {
    final remaining = _allMutations().where((m) => !(m.sessionId == mutation.sessionId && m.questionId == mutation.questionId)).toList()
      ..add(mutation);
    await _prefs.setString(_mutationsKey, jsonEncode(remaining.map((m) => m.toJson()).toList()));
  }

  Future<void> clearMutationsForSession(String sessionId) async {
    final remaining = _allMutations().where((m) => m.sessionId != sessionId).toList();
    await _prefs.setString(_mutationsKey, jsonEncode(remaining.map((m) => m.toJson()).toList()));
  }

  List<PendingInterviewMutation> _allMutations() {
    final raw = _prefs.getString(_mutationsKey);
    if (raw == null) return [];
    try {
      return (jsonDecode(raw) as List).map((e) => PendingInterviewMutation.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      return [];
    }
  }

  static Map<String, dynamic> _sessionToJson(InterviewSessionDetail detail) => {
        "id": detail.id,
        "mode": detail.mode.wireValue,
        "status": detail.status.wireValue,
        "application_id": detail.applicationId,
        "job_id": detail.jobId,
        "company_id": detail.companyId,
        "categories_requested": detail.categoriesRequested,
        "question_count": detail.questionCount,
        "time_per_question_seconds": detail.timePerQuestionSeconds,
        "questions": detail.questions
            .map((q) => {
                  "id": q.id,
                  "order_index": q.orderIndex,
                  "question_text": q.questionText,
                  "category_name": q.categoryName,
                  "topic_name": q.topicName,
                  "difficulty": q.difficulty.wireValue,
                  "evaluation_points": q.evaluationPoints,
                  "follow_up_prompt": q.followUpPrompt,
                  "suggested_star_story_ids": q.suggestedStarStoryIds,
                  "time_limit_seconds": q.timeLimitSeconds,
                  "answer_state": q.answerState == null
                      ? null
                      : {
                          "answer_text": q.answerState!.answerText,
                          "notes": q.answerState!.notes,
                          "audio_path": q.answerState!.audioPath,
                          "audio_duration_seconds": q.answerState!.audioDurationSeconds,
                          "self_rating": q.answerState!.selfRating,
                          "used_star": q.answerState!.usedStar,
                          "gave_measurable_result": q.answerState!.gaveMeasurableResult,
                          "answered_exact_question": q.answerState!.answeredExactQuestion,
                          "is_skipped": q.answerState!.isSkipped,
                          "is_marked_practiced": q.answerState!.isMarkedPracticed,
                          "is_saved": q.answerState!.isSaved,
                        },
                })
            .toList(),
      };

  InterviewSessionDetail? loadSession(String sessionId) {
    final raw = _prefs.getString("$_sessionKeyPrefix$sessionId");
    if (raw == null) return null;
    try {
      return InterviewSessionDetail.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }
}
