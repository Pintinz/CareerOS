import "dart:async";

import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/app_providers.dart";
import "../../../core/network/api_client.dart";
import "../data/aptitude_models.dart";
import "../data/aptitude_offline_cache.dart";
import "../data/aptitude_repository.dart";

final aptitudeRepositoryProvider = Provider<AptitudeRepository>((ref) {
  return AptitudeRepository(apiClient: ref.watch(apiClientProvider));
});

final questionCategoriesProvider = FutureProvider.autoDispose<List<QuestionCategory>>((ref) {
  return ref.watch(aptitudeRepositoryProvider).listCategories();
});

final aptitudeAnalyticsProvider = FutureProvider.autoDispose<AptitudeAnalytics>((ref) {
  return ref.watch(aptitudeRepositoryProvider).getAnalytics();
});

final aptitudeRecommendationsProvider = FutureProvider.autoDispose<Recommendations>((ref) {
  return ref.watch(aptitudeRepositoryProvider).getRecommendations();
});

final aptitudeSessionHistoryProvider = FutureProvider.autoDispose<List<TestSessionSummary>>((ref) async {
  final result = await ref.watch(aptitudeRepositoryProvider).listSessions();
  return result.items;
});

/// Drives session creation from the configuration screen — kept separate from [ExamController]
/// so the "Start Test" button has its own loading/error state independent of the exam screen.
class SessionCreationController extends AsyncNotifier<TestSessionDetail?> {
  @override
  TestSessionDetail? build() => null;

  Future<TestSessionDetail?> create({
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
    state = const AsyncLoading();
    final result = await AsyncValue.guard(
      () => ref.read(aptitudeRepositoryProvider).createSession(
            mode: mode,
            sections: sections,
            difficulty: difficulty,
            questionCount: questionCount,
            timing: timing,
            timeLimitMinutes: timeLimitMinutes,
            applicationId: applicationId,
            jobId: jobId,
            topicSlugs: topicSlugs,
          ),
    );
    state = result;
    return result.valueOrNull;
  }
}

final sessionCreationControllerProvider =
    AsyncNotifierProvider<SessionCreationController, TestSessionDetail?>(SessionCreationController.new);

class ExamState {
  const ExamState({
    this.session,
    this.isLoading = true,
    this.error,
    this.currentIndex = 0,
    this.remainingSeconds,
    this.isSubmitting = false,
    this.hasUnsyncedChanges = false,
    this.result,
  });

  final TestSessionDetail? session;
  final bool isLoading;
  final Object? error;
  final int currentIndex;
  final int? remainingSeconds;
  final bool isSubmitting;
  final bool hasUnsyncedChanges;
  final TestResult? result;

  SessionQuestion? get currentQuestion {
    final s = session;
    if (s == null || s.questions.isEmpty) return null;
    return s.questions[currentIndex.clamp(0, s.questions.length - 1)];
  }

  bool get isTimed => session?.timeLimitSeconds != null;
  bool get isSubmitted => session?.status.isSubmitted ?? false;

  ExamState copyWith({
    TestSessionDetail? session,
    bool? isLoading,
    Object? error,
    bool clearError = false,
    int? currentIndex,
    int? remainingSeconds,
    bool? isSubmitting,
    bool? hasUnsyncedChanges,
    TestResult? result,
  }) =>
      ExamState(
        session: session ?? this.session,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        currentIndex: currentIndex ?? this.currentIndex,
        remainingSeconds: remainingSeconds ?? this.remainingSeconds,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        hasUnsyncedChanges: hasUnsyncedChanges ?? this.hasUnsyncedChanges,
        result: result ?? this.result,
      );
}

/// Owns one active test session end-to-end: loading (server-first, offline-cache fallback),
/// the authoritative-timestamp countdown timer (spec §19 — never a bare in-memory countdown),
/// answering/flagging with offline queueing, navigation between questions, and submission.
class ExamController extends FamilyNotifier<ExamState, String> {
  Timer? _ticker;
  /// device-clock -> server-clock offset, captured once per load so the countdown stays accurate
  /// even if the device clock is wrong, without needing to re-sync every tick.
  Duration _serverOffset = Duration.zero;

  @override
  ExamState build(String sessionId) {
    ref.onDispose(() => _ticker?.cancel());
    Future.microtask(_load);
    final cached = _cache.loadSession(sessionId);
    return ExamState(session: cached, isLoading: true);
  }

  AptitudeRepository get _repo => ref.read(aptitudeRepositoryProvider);
  AptitudeOfflineCache get _cache => ref.read(aptitudeOfflineCacheProvider);

  Future<void> _load() async {
    await _syncPending();
    try {
      final session = await _repo.getSession(arg);
      await _cache.saveSession(session);
      _serverOffset = session.serverTime.difference(DateTime.now());
      state = state.copyWith(session: session, isLoading: false, clearError: true);
      _restartTicker();
      if (session.status.isSubmitted && state.result == null) {
        final result = await _repo.getResults(arg);
        state = state.copyWith(result: result);
      }
    } catch (e) {
      // Offline and we already had a cached session from build() — keep working from it rather
      // than blocking the user with an error screen (spec §21).
      if (state.session != null) {
        state = state.copyWith(isLoading: false, hasUnsyncedChanges: true);
        _restartTicker();
      } else {
        state = state.copyWith(isLoading: false, error: e);
      }
    }
  }

  void _restartTicker() {
    _ticker?.cancel();
    final session = state.session;
    if (session == null || session.status.isSubmitted) return;
    _tick();
    if (session.expiresAt == null) return;
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
  }

  void _tick() {
    final session = state.session;
    if (session == null || session.expiresAt == null || session.status.isSubmitted) return;
    final now = DateTime.now().add(_serverOffset);
    final remaining = session.expiresAt!.difference(now).inSeconds;
    state = state.copyWith(remainingSeconds: remaining.clamp(0, 1 << 31));
    if (remaining <= 0) {
      _ticker?.cancel();
      submit();
    }
  }

  Future<void> answerOptions(String questionId, List<String> optionIds) async {
    _applyLocalAnswer(questionId, selectedOptionIds: optionIds);
    await _pushAnswer(questionId, selectedOptionIds: optionIds);
  }

  Future<void> answerNumeric(String questionId, double value) async {
    _applyLocalAnswer(questionId, answerNumericValue: value);
    await _pushAnswer(questionId, answerNumericValue: value);
  }

  Future<void> toggleFlag(String questionId) async {
    final session = state.session;
    if (session == null) return;
    final question = session.questions.firstWhere((q) => q.id == questionId);
    final current = question.answerState ?? const SessionAnswerState();
    _updateQuestion(
      questionId,
      question.copyWith(answerState: SessionAnswerState(
        selectedOptionIds: current.selectedOptionIds,
        answerNumericValue: current.answerNumericValue,
        isFlagged: !current.isFlagged,
      )),
    );
    await _cache.saveSession(state.session!);
    try {
      await _syncPending();
      final updated = await _repo.toggleFlag(sessionId: arg, questionId: questionId);
      _updateQuestion(questionId, updated);
      await _cache.saveSession(state.session!);
    } on ApiException catch (e) {
      if (e.kind == ApiErrorKind.network) {
        await _cache.enqueueMutation(PendingMutation(sessionId: arg, questionId: questionId, isFlag: true));
        state = state.copyWith(hasUnsyncedChanges: true);
      }
    }
  }

  void _applyLocalAnswer(String questionId, {List<String>? selectedOptionIds, double? answerNumericValue}) {
    final session = state.session;
    if (session == null) return;
    final question = session.questions.firstWhere((q) => q.id == questionId);
    final current = question.answerState;
    _updateQuestion(
      questionId,
      question.copyWith(
        answerState: SessionAnswerState(
          selectedOptionIds: selectedOptionIds ?? current?.selectedOptionIds,
          answerNumericValue: answerNumericValue ?? current?.answerNumericValue,
          isFlagged: current?.isFlagged ?? false,
        ),
      ),
    );
  }

  Future<void> _pushAnswer(String questionId, {List<String>? selectedOptionIds, double? answerNumericValue}) async {
    await _cache.saveSession(state.session!);
    try {
      await _syncPending();
      final updated = await _repo.updateAnswer(
        sessionId: arg,
        questionId: questionId,
        selectedOptionIds: selectedOptionIds,
        answerNumericValue: answerNumericValue,
      );
      _updateQuestion(questionId, updated);
      await _cache.saveSession(state.session!);
      state = state.copyWith(hasUnsyncedChanges: _cache.pendingMutationsFor(arg).isNotEmpty);
    } on ApiException catch (e) {
      if (e.kind == ApiErrorKind.network) {
        await _cache.enqueueMutation(PendingMutation(
          sessionId: arg,
          questionId: questionId,
          isFlag: false,
          selectedOptionIds: selectedOptionIds,
          answerNumericValue: answerNumericValue,
        ));
        state = state.copyWith(hasUnsyncedChanges: true);
      }
      // A non-network failure (e.g. 409 session no longer in progress) is left as-is locally;
      // the next _load()/_syncPending() reconciles with the server's authoritative state.
    }
  }

  /// Replays any answers/flags recorded while offline. Best-effort: called opportunistically
  /// before each new mutation and on session load, rather than depending on a connectivity
  /// listener package.
  Future<void> _syncPending() async {
    final pending = _cache.pendingMutationsFor(arg);
    if (pending.isEmpty) return;
    for (final mutation in pending) {
      try {
        if (mutation.isFlag) {
          await _repo.toggleFlag(sessionId: mutation.sessionId, questionId: mutation.questionId);
        } else {
          await _repo.updateAnswer(
            sessionId: mutation.sessionId,
            questionId: mutation.questionId,
            selectedOptionIds: mutation.selectedOptionIds,
            answerNumericValue: mutation.answerNumericValue,
          );
        }
      } on ApiException catch (e) {
        if (e.kind == ApiErrorKind.network) return; // still offline — try again next time
        // Any other failure (session ended, etc.) means this mutation is no longer applicable.
      }
    }
    await _cache.clearMutationsForSession(arg);
    state = state.copyWith(hasUnsyncedChanges: false);
  }

  void _updateQuestion(String questionId, SessionQuestion updated) {
    final session = state.session;
    if (session == null) return;
    final questions = [
      for (final q in session.questions) q.id == questionId ? updated : q,
    ];
    state = state.copyWith(session: session.copyWith(questions: questions));
  }

  void goToQuestion(int index) {
    final session = state.session;
    if (session == null) return;
    state = state.copyWith(currentIndex: index.clamp(0, session.questions.length - 1));
  }

  void next() => goToQuestion(state.currentIndex + 1);
  void previous() => goToQuestion(state.currentIndex - 1);

  Future<TestResult?> submit() async {
    if (state.isSubmitting || state.isSubmitted) return state.result;
    state = state.copyWith(isSubmitting: true);
    _ticker?.cancel();
    try {
      await _syncPending();
      final result = await _repo.submit(arg);
      final refreshed = await _repo.getSession(arg);
      await _cache.clearSession(arg);
      state = state.copyWith(session: refreshed, isSubmitting: false, result: result, clearError: true);
      return result;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, error: e);
      return null;
    }
  }
}

final examControllerProvider = NotifierProvider.family<ExamController, ExamState, String>(ExamController.new);

final sessionReviewProvider = FutureProvider.autoDispose.family<SessionReview, String>((ref, sessionId) {
  return ref.watch(aptitudeRepositoryProvider).getReview(sessionId);
});
