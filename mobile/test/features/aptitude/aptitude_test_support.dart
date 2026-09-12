import 'package:careeros/core/app_providers.dart';
import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/applications/data/application_repository.dart';
import 'package:careeros/features/applications/presentation/application_providers.dart';
import 'package:careeros/features/aptitude/data/aptitude_models.dart';
import 'package:careeros/features/aptitude/data/aptitude_offline_cache.dart';
import 'package:careeros/features/aptitude/data/aptitude_repository.dart';
import 'package:careeros/features/aptitude/presentation/aptitude_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Test double for [AptitudeRepository] — overrides every network-hitting method so widget tests
/// never touch a real ApiClient/Dio. The base class is only extended (not reimplemented from
/// scratch) so a currently-unused inherited method doesn't silently compile against a stale
/// signature if the interface changes later.
class FakeAptitudeRepository extends AptitudeRepository {
  FakeAptitudeRepository() : super(apiClient: ApiClient());

  List<QuestionCategory> categories = const [
    QuestionCategory(id: 'cat-numerical', name: 'Numerical Reasoning', slug: 'numerical'),
    QuestionCategory(id: 'cat-verbal', name: 'Verbal Reasoning', slug: 'verbal'),
  ];

  TestSessionDetail Function(String sessionId)? sessionProvider;
  TestSessionDetail? Function()? onCreateSession;
  TestResult? resultOverride;
  SessionReview? reviewOverride;
  AptitudeAnalytics analyticsOverride = AptitudeAnalytics.empty;
  Recommendations recommendationsOverride = Recommendations.empty;
  List<TestSessionSummary> historyOverride = const [];

  final List<Map<String, dynamic>> answerCalls = [];
  final List<String> flagCalls = [];
  bool submitCalled = false;

  @override
  Future<List<QuestionCategory>> listCategories() async => categories;

  @override
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
    final session = onCreateSession?.call() ?? buildSampleSession();
    return session;
  }

  @override
  Future<TestSessionDetail> getSession(String sessionId) async {
    return sessionProvider?.call(sessionId) ?? buildSampleSession(id: sessionId);
  }

  @override
  Future<({List<TestSessionSummary> items, int total})> listSessions({int page = 1, String? status}) async {
    return (items: historyOverride, total: historyOverride.length);
  }

  @override
  Future<SessionQuestion> updateAnswer({
    required String sessionId,
    required String questionId,
    List<String>? selectedOptionIds,
    double? answerNumericValue,
    int? timeSpentSeconds,
  }) async {
    answerCalls.add({'sessionId': sessionId, 'questionId': questionId, 'selectedOptionIds': selectedOptionIds});
    final session = sessionProvider?.call(sessionId) ?? buildSampleSession(id: sessionId);
    final question = session.questions.firstWhere((q) => q.id == questionId);
    return question.copyWith(
      answerState: SessionAnswerState(
        selectedOptionIds: selectedOptionIds,
        answerNumericValue: answerNumericValue,
        isFlagged: question.answerState?.isFlagged ?? false,
      ),
    );
  }

  @override
  Future<SessionQuestion> toggleFlag({required String sessionId, required String questionId}) async {
    flagCalls.add(questionId);
    final session = sessionProvider?.call(sessionId) ?? buildSampleSession(id: sessionId);
    final question = session.questions.firstWhere((q) => q.id == questionId);
    final current = question.answerState ?? const SessionAnswerState();
    return question.copyWith(
      answerState: SessionAnswerState(
        selectedOptionIds: current.selectedOptionIds,
        answerNumericValue: current.answerNumericValue,
        isFlagged: !current.isFlagged,
      ),
    );
  }

  @override
  Future<TestResult> submit(String sessionId) async {
    submitCalled = true;
    return resultOverride ?? buildSampleResult(sessionId: sessionId);
  }

  @override
  Future<TestResult> getResults(String sessionId) async => resultOverride ?? buildSampleResult(sessionId: sessionId);

  @override
  Future<SessionReview> getReview(String sessionId) async =>
      reviewOverride ?? SessionReview(sessionId: sessionId, questions: const []);

  @override
  Future<AptitudeAnalytics> getAnalytics() async => analyticsOverride;

  @override
  Future<Recommendations> getRecommendations() async => recommendationsOverride;
}

TestSessionDetail buildSampleSession({
  String id = 'session-1',
  TestStatus status = TestStatus.inProgress,
  DateTime? expiresAt,
  int? timeLimitSeconds,
  List<SessionQuestion>? questions,
}) {
  final builtQuestions = questions ??
      [
        const SessionQuestion(
          id: 'q1',
          orderIndex: 0,
          questionText: 'What is 15% of 200?',
          questionType: QuestionType.singleChoice,
          difficulty: QuestionDifficulty.easy,
          marks: 1,
          negativeMarks: 0.25,
          categoryName: 'Numerical Reasoning',
          topicName: 'Percentages',
          topicSlug: 'percentages',
          options: [
            TestOption(id: 'opt-correct', optionText: '30', displayOrder: 0),
            TestOption(id: 'opt-wrong', optionText: '20', displayOrder: 1),
          ],
        ),
        const SessionQuestion(
          id: 'q2',
          orderIndex: 1,
          questionText: 'What is the capital-style question 2?',
          questionType: QuestionType.singleChoice,
          difficulty: QuestionDifficulty.medium,
          marks: 1,
          negativeMarks: 0.25,
          categoryName: 'Numerical Reasoning',
          topicName: 'Ratios',
          topicSlug: 'ratios',
          options: [
            TestOption(id: 'q2-a', optionText: 'A', displayOrder: 0),
            TestOption(id: 'q2-b', optionText: 'B', displayOrder: 1),
          ],
        ),
      ];

  return TestSessionDetail(
    id: id,
    mode: TestMode.practice,
    status: status,
    startedAt: DateTime.now(),
    expiresAt: expiresAt,
    timeLimitSeconds: timeLimitSeconds,
    autoSubmitted: false,
    questionCount: builtQuestions.length,
    totalMarks: builtQuestions.length.toDouble(),
    questions: builtQuestions,
    serverTime: DateTime.now(),
    remainingSeconds: expiresAt?.difference(DateTime.now()).inSeconds,
  );
}

TestResult buildSampleResult({String sessionId = 'session-1'}) {
  return TestResult(
    sessionId: sessionId,
    status: TestStatus.submitted,
    score: 1.5,
    totalMarks: 2,
    percentage: 75,
    correctCount: 1,
    incorrectCount: 1,
    unansweredCount: 0,
    timeUsedSeconds: 120,
    timeLimitSeconds: null,
    autoSubmitted: false,
    sectionBreakdown: const {
      'Numerical Reasoning': SectionResult(correct: 1, total: 2, percentage: 50),
    },
    performanceLabel: 'Good Performance',
  );
}

/// Test double for [ApplicationRepository] used by screens that also read the applications
/// feature (the job-context picker, the home dashboard's upcoming-stage card).
class FakeApplicationRepository extends ApplicationRepository {
  FakeApplicationRepository({this.items = const []}) : super(apiClient: ApiClient());

  List<Application> items;

  @override
  Future<({List<Application> items, int total})> list({ApplicationStage? stage, int page = 1}) async {
    return (items: items, total: items.length);
  }

  @override
  Future<Application> get(String id) async => items.firstWhere((a) => a.id == id);

  @override
  Future<int> activeCount() async => items.length;
}

/// Overrides to hand a [ProviderScope] in tests: a fake aptitude repository/offline cache, and
/// (optionally) a fake application repository so screens that also touch application data don't
/// hit the network. Async because [AptitudeOfflineCache.create] loads SharedPreferences.
Future<List<Override>> aptitudeTestOverrides({
  required FakeAptitudeRepository repository,
  FakeApplicationRepository? applicationRepository,
}) async {
  SharedPreferences.setMockInitialValues({});
  final offlineCache = await AptitudeOfflineCache.create();
  return [
    aptitudeRepositoryProvider.overrideWithValue(repository),
    aptitudeOfflineCacheProvider.overrideWithValue(offlineCache),
    if (applicationRepository != null) applicationRepositoryProvider.overrideWithValue(applicationRepository),
  ];
}
