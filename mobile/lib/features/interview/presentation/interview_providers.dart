import "dart:async";

import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../core/network/api_client.dart";
import "../data/interview_models.dart";
import "../data/interview_offline_cache.dart";
import "../data/interview_repository.dart";

final interviewRepositoryProvider = Provider<InterviewRepository>((ref) {
  return InterviewRepository(apiClient: ref.watch(apiClientProvider));
});

final interviewCategoriesProvider = FutureProvider.autoDispose<List<InterviewCategory>>((ref) {
  return ref.watch(interviewRepositoryProvider).listCategories();
});

final interviewAnalyticsProvider = FutureProvider.autoDispose<InterviewAnalytics>((ref) {
  return ref.watch(interviewRepositoryProvider).getAnalytics();
});

final interviewReadinessProvider = FutureProvider.autoDispose.family<Readiness, String?>((ref, applicationId) {
  return ref.watch(interviewRepositoryProvider).getReadiness(applicationId: applicationId);
});

final interviewSessionHistoryProvider = FutureProvider.autoDispose<List<InterviewSessionSummary>>((ref) async {
  final result = await ref.watch(interviewRepositoryProvider).listSessions();
  return result.items;
});

final companyPrepProvider = FutureProvider.autoDispose.family<CompanyPrep, String>((ref, applicationId) {
  return ref.watch(interviewRepositoryProvider).getCompanyPrep(applicationId);
});

final preparationProgressProvider = FutureProvider.autoDispose.family<PreparationProgress, String?>((ref, applicationId) {
  return ref.watch(interviewRepositoryProvider).getPreparationProgress(applicationId: applicationId);
});

final starStoriesProvider = FutureProvider.autoDispose<List<StarStory>>((ref) {
  return ref.watch(interviewRepositoryProvider).listStarStories();
});

final starStoryProvider = FutureProvider.autoDispose.family<StarStory, String>((ref, storyId) {
  return ref.watch(interviewRepositoryProvider).getStarStory(storyId);
});

/// Drives session creation from the configuration screen.
class InterviewSessionCreationController extends AsyncNotifier<InterviewSessionDetail?> {
  @override
  InterviewSessionDetail? build() => null;

  Future<InterviewSessionDetail?> create({
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
    state = const AsyncLoading();
    final result = await AsyncValue.guard(
      () => ref.read(interviewRepositoryProvider).createSession(
            mode: mode,
            categories: categories,
            categoryCounts: categoryCounts,
            difficulty: difficulty,
            questionCount: questionCount,
            timePerQuestionSeconds: timePerQuestionSeconds,
            applicationId: applicationId,
            jobId: jobId,
            companyId: companyId,
          ),
    );
    state = result;
    return result.valueOrNull;
  }
}

final interviewSessionCreationControllerProvider =
    AsyncNotifierProvider<InterviewSessionCreationController, InterviewSessionDetail?>(InterviewSessionCreationController.new);

class InterviewSessionState {
  const InterviewSessionState({
    this.session,
    this.isLoading = true,
    this.error,
    this.currentIndex = 0,
    this.remainingSeconds,
    this.isCompleting = false,
    this.hasUnsyncedChanges = false,
    this.completion,
  });

  final InterviewSessionDetail? session;
  final bool isLoading;
  final Object? error;
  final int currentIndex;
  final int? remainingSeconds;
  final bool isCompleting;
  final bool hasUnsyncedChanges;
  final SessionCompletion? completion;

  SessionQuestion? get currentQuestion {
    final s = session;
    if (s == null || s.questions.isEmpty) return null;
    return s.questions[currentIndex.clamp(0, s.questions.length - 1)];
  }

  bool get isCompleted => session?.status.isCompleted ?? false;

  InterviewSessionState copyWith({
    InterviewSessionDetail? session,
    bool? isLoading,
    Object? error,
    bool clearError = false,
    int? currentIndex,
    int? remainingSeconds,
    bool clearRemainingSeconds = false,
    bool? isCompleting,
    bool? hasUnsyncedChanges,
    SessionCompletion? completion,
  }) =>
      InterviewSessionState(
        session: session ?? this.session,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        currentIndex: currentIndex ?? this.currentIndex,
        remainingSeconds: clearRemainingSeconds ? null : (remainingSeconds ?? this.remainingSeconds),
        isCompleting: isCompleting ?? this.isCompleting,
        hasUnsyncedChanges: hasUnsyncedChanges ?? this.hasUnsyncedChanges,
        completion: completion ?? this.completion,
      );
}

/// Owns one active interview session: server-first loading with an offline-cache fallback,
/// answering (text/notes/self-rating/STAR checkboxes) with offline queueing, a self-paced
/// per-question countdown for Mock Interview (informational only — never server-enforced, unlike
/// the aptitude engine's timer; see ARCHITECTURE.md), and completion.
class InterviewSessionController extends FamilyNotifier<InterviewSessionState, String> {
  Timer? _questionTicker;
  int? _questionRemainingSeconds;

  @override
  InterviewSessionState build(String sessionId) {
    ref.onDispose(() => _questionTicker?.cancel());
    Future.microtask(_load);
    final cached = _cache.loadSession(sessionId);
    return InterviewSessionState(session: cached, isLoading: true);
  }

  InterviewRepository get _repo => ref.read(interviewRepositoryProvider);
  InterviewOfflineCache get _cache => ref.read(interviewOfflineCacheProvider);

  Future<void> _load() async {
    await _syncPending();
    try {
      final session = await _repo.getSession(arg);
      await _cache.saveSession(session);
      state = state.copyWith(session: session, isLoading: false, clearError: true);
      _restartQuestionTimer();
      if (session.status.isCompleted && state.completion == null) {
        // Idempotent on the backend — re-fetches the same completion stats without re-mutating
        // anything, so a deep link straight to results still shows real numbers.
        final completion = await _repo.completeSession(arg);
        state = state.copyWith(completion: completion);
      }
    } catch (e) {
      if (state.session != null) {
        state = state.copyWith(isLoading: false, hasUnsyncedChanges: true);
        _restartQuestionTimer();
      } else {
        state = state.copyWith(isLoading: false, error: e);
      }
    }
  }

  void _restartQuestionTimer() {
    _questionTicker?.cancel();
    final session = state.session;
    final limit = session?.timePerQuestionSeconds;
    if (session == null || session.status.isCompleted || limit == null) {
      state = state.copyWith(clearRemainingSeconds: true);
      return;
    }
    _questionRemainingSeconds = limit;
    state = state.copyWith(remainingSeconds: _questionRemainingSeconds);
    _questionTicker = Timer.periodic(const Duration(seconds: 1), (_) {
      _questionRemainingSeconds = (_questionRemainingSeconds ?? 0) - 1;
      if (_questionRemainingSeconds! <= 0) {
        _questionRemainingSeconds = 0;
        _questionTicker?.cancel();
      }
      state = state.copyWith(remainingSeconds: _questionRemainingSeconds);
    });
  }

  void goToQuestion(int index) {
    final session = state.session;
    if (session == null) return;
    state = state.copyWith(currentIndex: index.clamp(0, session.questions.length - 1));
    _restartQuestionTimer();
  }

  void next() => goToQuestion(state.currentIndex + 1);
  void previous() => goToQuestion(state.currentIndex - 1);

  Future<void> answer(
    String questionId, {
    String? answerText,
    String? notes,
    int? selfRating,
    bool? usedStar,
    bool? gaveMeasurableResult,
    bool? answeredExactQuestion,
    bool? isSkipped,
    bool? isMarkedPracticed,
    bool? isSaved,
  }) async {
    _applyLocalAnswer(
      questionId, answerText: answerText, notes: notes, selfRating: selfRating, usedStar: usedStar,
      gaveMeasurableResult: gaveMeasurableResult, answeredExactQuestion: answeredExactQuestion,
      isSkipped: isSkipped, isMarkedPracticed: isMarkedPracticed, isSaved: isSaved,
    );
    await _cache.saveSession(state.session!);
    try {
      await _syncPending();
      final updated = await _repo.updateAnswer(
        sessionId: arg, questionId: questionId, answerText: answerText, notes: notes, selfRating: selfRating,
        usedStar: usedStar, gaveMeasurableResult: gaveMeasurableResult, answeredExactQuestion: answeredExactQuestion,
        isSkipped: isSkipped, isMarkedPracticed: isMarkedPracticed, isSaved: isSaved,
      );
      _updateQuestion(questionId, updated);
      await _cache.saveSession(state.session!);
      state = state.copyWith(hasUnsyncedChanges: _cache.pendingMutationsFor(arg).isNotEmpty);
    } on ApiException catch (e) {
      if (e.kind == ApiErrorKind.network) {
        await _cache.enqueueMutation(PendingInterviewMutation(
          sessionId: arg, questionId: questionId, answerText: answerText, notes: notes, selfRating: selfRating,
          usedStar: usedStar, gaveMeasurableResult: gaveMeasurableResult, answeredExactQuestion: answeredExactQuestion,
          isSkipped: isSkipped, isMarkedPracticed: isMarkedPracticed, isSaved: isSaved,
        ));
        state = state.copyWith(hasUnsyncedChanges: true);
      }
    }
  }

  void _applyLocalAnswer(
    String questionId, {
    String? answerText, String? notes, int? selfRating, bool? usedStar, bool? gaveMeasurableResult,
    bool? answeredExactQuestion, bool? isSkipped, bool? isMarkedPracticed, bool? isSaved,
  }) {
    final session = state.session;
    if (session == null) return;
    final question = session.questions.firstWhere((q) => q.id == questionId);
    final current = question.answerState;
    _updateQuestion(
      questionId,
      question.copyWith(
        answerState: SessionAnswerState(
          answerText: answerText ?? current?.answerText,
          notes: notes ?? current?.notes,
          audioPath: current?.audioPath,
          audioDurationSeconds: current?.audioDurationSeconds,
          selfRating: selfRating ?? current?.selfRating,
          usedStar: usedStar ?? current?.usedStar,
          gaveMeasurableResult: gaveMeasurableResult ?? current?.gaveMeasurableResult,
          answeredExactQuestion: answeredExactQuestion ?? current?.answeredExactQuestion,
          isSkipped: isSkipped ?? current?.isSkipped ?? false,
          isMarkedPracticed: isMarkedPracticed ?? current?.isMarkedPracticed ?? false,
          isSaved: isSaved ?? current?.isSaved ?? false,
        ),
      ),
    );
  }

  Future<void> _syncPending() async {
    final pending = _cache.pendingMutationsFor(arg);
    if (pending.isEmpty) return;
    for (final mutation in pending) {
      try {
        await _repo.updateAnswer(
          sessionId: mutation.sessionId, questionId: mutation.questionId, answerText: mutation.answerText,
          notes: mutation.notes, selfRating: mutation.selfRating, usedStar: mutation.usedStar,
          gaveMeasurableResult: mutation.gaveMeasurableResult, answeredExactQuestion: mutation.answeredExactQuestion,
          isSkipped: mutation.isSkipped, isMarkedPracticed: mutation.isMarkedPracticed, isSaved: mutation.isSaved,
        );
      } on ApiException catch (e) {
        if (e.kind == ApiErrorKind.network) return;
      }
    }
    await _cache.clearMutationsForSession(arg);
    state = state.copyWith(hasUnsyncedChanges: false);
  }

  void _updateQuestion(String questionId, SessionQuestion updated) {
    final session = state.session;
    if (session == null) return;
    final questions = [for (final q in session.questions) q.id == questionId ? updated : q];
    state = state.copyWith(session: session.copyWith(questions: questions));
  }

  Future<SessionCompletion?> complete() async {
    if (state.isCompleting || state.isCompleted) return state.completion;
    state = state.copyWith(isCompleting: true);
    _questionTicker?.cancel();
    try {
      await _syncPending();
      final completion = await _repo.completeSession(arg);
      final refreshed = await _repo.getSession(arg);
      await _cache.clearSession(arg);
      state = state.copyWith(session: refreshed, isCompleting: false, completion: completion, clearError: true);
      return completion;
    } catch (e) {
      state = state.copyWith(isCompleting: false, error: e);
      return null;
    }
  }
}

final interviewSessionControllerProvider =
    NotifierProvider.family<InterviewSessionController, InterviewSessionState, String>(InterviewSessionController.new);
