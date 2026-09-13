import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/data/interview_repository.dart';

/// Test double for [InterviewRepository] — same rationale as the aptitude engine's
/// FakeAptitudeRepository: overrides every network-hitting method so widget tests never touch a
/// real ApiClient/Dio.
class FakeInterviewRepository extends InterviewRepository {
  FakeInterviewRepository() : super(apiClient: ApiClient());

  List<InterviewCategory> categories = const [
    InterviewCategory(id: 'cat-behavioral', name: 'Behavioral', slug: 'behavioral'),
    InterviewCategory(id: 'cat-technical', name: 'Technical', slug: 'technical'),
  ];

  InterviewSessionDetail Function(String sessionId)? sessionProvider;
  InterviewSessionDetail? Function()? onCreateSession;
  SessionCompletion? completionOverride;
  InterviewAnalytics analyticsOverride = InterviewAnalytics.empty;
  Readiness readinessOverride = Readiness.empty;
  List<InterviewSessionSummary> historyOverride = const [];
  List<StarStory> starStoriesOverride = const [];
  CompanyPrep? companyPrepOverride;
  PreparationProgress? preparationProgressOverride;
  final List<Map<String, dynamic>> answerCalls = [];

  @override
  Future<List<InterviewCategory>> listCategories() async => categories;

  @override
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
    bool autoMix = false,
  }) async {
    return onCreateSession?.call() ?? buildSampleInterviewSession();
  }

  @override
  Future<InterviewSessionDetail> getSession(String sessionId) async {
    return sessionProvider?.call(sessionId) ?? buildSampleInterviewSession(id: sessionId);
  }

  @override
  Future<({List<InterviewSessionSummary> items, int total})> listSessions({int page = 1}) async {
    return (items: historyOverride, total: historyOverride.length);
  }

  @override
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
    answerCalls.add({
      'sessionId': sessionId, 'questionId': questionId, 'selfRating': selfRating, 'usedStar': usedStar,
      'isMarkedPracticed': isMarkedPracticed,
    });
    final session = sessionProvider?.call(sessionId) ?? buildSampleInterviewSession(id: sessionId);
    final question = session.questions.firstWhere((q) => q.id == questionId);
    return question.copyWith(
      answerState: SessionAnswerState(
        answerText: answerText ?? question.answerState?.answerText,
        notes: notes ?? question.answerState?.notes,
        audioPath: audioPath ?? question.answerState?.audioPath,
        audioDurationSeconds: audioDurationSeconds ?? question.answerState?.audioDurationSeconds,
        selfRating: selfRating ?? question.answerState?.selfRating,
        usedStar: usedStar ?? question.answerState?.usedStar,
        gaveMeasurableResult: gaveMeasurableResult ?? question.answerState?.gaveMeasurableResult,
        answeredExactQuestion: answeredExactQuestion ?? question.answerState?.answeredExactQuestion,
        isSkipped: isSkipped ?? question.answerState?.isSkipped ?? false,
        isMarkedPracticed: isMarkedPracticed ?? question.answerState?.isMarkedPracticed ?? false,
        isSaved: isSaved ?? question.answerState?.isSaved ?? false,
      ),
    );
  }

  @override
  Future<SessionCompletion> completeSession(String sessionId) async =>
      completionOverride ?? buildSampleCompletion(sessionId: sessionId);

  @override
  Future<InterviewAnalytics> getAnalytics() async => analyticsOverride;

  @override
  Future<Readiness> getReadiness({String? applicationId}) async => readinessOverride;

  @override
  Future<CompanyPrep> getCompanyPrep(String applicationId) async =>
      companyPrepOverride ?? const CompanyPrep(disclaimer: 'CareerOS practice based on the company, role and available public information. Not an official employer interview guide.');

  @override
  Future<PreparationProgress> getPreparationProgress({String? applicationId}) async =>
      preparationProgressOverride ?? const PreparationProgress(checklist: [], questionsToAsk: [], reviewedTopics: []);

  @override
  Future<List<StarStory>> listStarStories({String? category}) async => starStoriesOverride;

  MockMixPreview mockMixPreviewOverride = const MockMixPreview(
    categoryCounts: {'cat-technical': 4, 'cat-behavioral': 3},
    categoryNames: {'cat-technical': 'Technical', 'cat-behavioral': 'Behavioral'},
    source: 'role_default',
  );

  @override
  Future<MockMixPreview> getMockMixPreview({int questionCount = 10, String? applicationId, String? jobId}) async =>
      mockMixPreviewOverride;
}

InterviewSessionDetail buildSampleInterviewSession({
  String id = 'interview-session-1',
  InterviewSessionMode mode = InterviewSessionMode.practice,
  InterviewSessionStatus status = InterviewSessionStatus.inProgress,
  int? timePerQuestionSeconds,
  List<SessionQuestion>? questions,
}) {
  final builtQuestions = questions ??
      const [
        SessionQuestion(
          id: 'iq1',
          orderIndex: 0,
          questionText: 'Tell me about a time you solved a difficult problem.',
          categoryName: 'Behavioral',
          difficulty: InterviewDifficulty.easy,
          answerGuidance: AnswerGuidance(assessing: 'Problem-solving approach', strongAnswerIncludes: ['A clear approach']),
          evaluationPoints: ['A clear approach'],
        ),
      ];
  return InterviewSessionDetail(
    id: id,
    mode: mode,
    status: status,
    categoriesRequested: const ['behavioral'],
    questionCount: builtQuestions.length,
    timePerQuestionSeconds: timePerQuestionSeconds,
    questions: builtQuestions,
  );
}

SessionCompletion buildSampleCompletion({String sessionId = 'interview-session-1'}) {
  return SessionCompletion(
    sessionId: sessionId,
    questionsCompleted: 1,
    questionsSkipped: 0,
    averageSelfRating: 4,
    categoryBreakdown: const {'Behavioral': CategoryCompletion(completed: 1, total: 1)},
    areasPracticed: const ['Behavioral'],
    areasStillUncovered: const [],
  );
}
