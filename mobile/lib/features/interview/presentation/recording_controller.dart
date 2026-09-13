import "dart:async";

import "package:audioplayers/audioplayers.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../data/interview_repository.dart";
import "../data/recording_service.dart";
import "interview_providers.dart";

/// Where a single question's recording UI currently sits (spec §1/§5/§6). Every failure path
/// lands on [error] with a human-readable message — it never throws out of the controller, so the
/// typed-answer/notes fields on the same screen stay usable no matter what went wrong.
enum RecordingUiPhase { idle, recording, recorded, playing, error }

class RecordingUiState {
  const RecordingUiState({
    this.phase = RecordingUiPhase.idle,
    this.elapsedSeconds = 0,
    this.localPath,
    this.durationSeconds,
    this.errorMessage,
  });

  final RecordingUiPhase phase;
  final int elapsedSeconds;
  final String? localPath;
  final int? durationSeconds;
  final String? errorMessage;

  RecordingUiState copyWith({
    RecordingUiPhase? phase, int? elapsedSeconds, String? localPath, int? durationSeconds, String? errorMessage,
  }) =>
      RecordingUiState(
        phase: phase ?? this.phase,
        elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
        localPath: localPath ?? this.localPath,
        durationSeconds: durationSeconds ?? this.durationSeconds,
        errorMessage: errorMessage,
      );
}

/// Identifies one question's recording slot: a session plus the session-scoped question id (the
/// same id already used for `PUT /answers/{questionId}` and now also for `POST /recordings`).
class RecordingTarget {
  const RecordingTarget({required this.sessionId, required this.questionId});
  final String sessionId;
  final String questionId;

  @override
  bool operator ==(Object other) => other is RecordingTarget && other.sessionId == sessionId && other.questionId == questionId;

  @override
  int get hashCode => Object.hash(sessionId, questionId);
}

/// Factories (rather than singleton providers) so each [RecordingController] instance gets its
/// own recorder/player, but tests can still override them with fakes wrapping no real platform
/// channel — see spec §33 ("use mocks for platform audio APIs").
final recordingServiceFactoryProvider = Provider<RecordingService Function()>((ref) => RecordingService.new);
final audioPlayerFactoryProvider = Provider<AudioPlayer Function()>((ref) => AudioPlayer.new);

/// Owns record/playback for exactly one interview question. Recording is done by
/// [RecordingService] (wraps the `record` package); playback by `audioplayers`. Neither ever
/// crashes the session — every failure is captured as [RecordingUiPhase.error] with a message
/// from [RecordingException].
class RecordingController extends FamilyNotifier<RecordingUiState, RecordingTarget> {
  late final RecordingService _recordingService;
  AudioPlayer? _playerOrNull;
  Timer? _ticker;

  @override
  RecordingUiState build(RecordingTarget arg) {
    _recordingService = ref.read(recordingServiceFactoryProvider)();
    ref.onDispose(() {
      _ticker?.cancel();
      _recordingService.dispose();
      _playerOrNull?.dispose();
    });
    return const RecordingUiState();
  }

  // Constructed lazily, only once playback is actually needed — building it eagerly would touch
  // real platform channels for every question on screen, even ones never played back.
  AudioPlayer get _player => _playerOrNull ??= ref.read(audioPlayerFactoryProvider)();

  InterviewRepository get _repo => ref.read(interviewRepositoryProvider);

  Future<void> start() async {
    try {
      await _recordingService.startRecording();
      state = state.copyWith(phase: RecordingUiPhase.recording, elapsedSeconds: 0, errorMessage: "");
      _ticker?.cancel();
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
        state = state.copyWith(elapsedSeconds: state.elapsedSeconds + 1);
      });
    } on RecordingException catch (e) {
      state = state.copyWith(phase: RecordingUiPhase.error, errorMessage: e.message);
    }
  }

  Future<void> stop() async {
    _ticker?.cancel();
    try {
      final path = await _recordingService.stop();
      if (path == null) {
        state = state.copyWith(phase: RecordingUiPhase.error, errorMessage: "The recording could not be saved.");
        return;
      }
      final duration = state.elapsedSeconds;
      state = state.copyWith(phase: RecordingUiPhase.recorded, localPath: path, durationSeconds: duration);
      try {
        await _repo.createRecording(
          sessionId: arg.sessionId, sessionQuestionId: arg.questionId, localPath: path, durationSeconds: duration,
        );
      } catch (_) {
        // Metadata sync failure is non-fatal — the local file and the in-session answer state
        // (updated by the caller via InterviewSessionController.answer) are unaffected; the
        // Recordings Manager just won't list it remotely until a later sync.
      }
    } on RecordingException catch (e) {
      state = state.copyWith(phase: RecordingUiPhase.error, errorMessage: e.message);
    }
  }

  Future<void> cancelRecording() async {
    _ticker?.cancel();
    await _recordingService.cancel();
    state = const RecordingUiState();
  }

  Future<void> playPause() async {
    final path = state.localPath;
    if (path == null) return;
    try {
      if (state.phase == RecordingUiPhase.playing) {
        await _player.pause();
        state = state.copyWith(phase: RecordingUiPhase.recorded);
        return;
      }
      await _player.play(DeviceFileSource(path));
      state = state.copyWith(phase: RecordingUiPhase.playing);
      _player.onPlayerComplete.first.then((_) {
        if (state.phase == RecordingUiPhase.playing) {
          state = state.copyWith(phase: RecordingUiPhase.recorded);
        }
      }).catchError((_) {});
    } catch (_) {
      state = state.copyWith(
        phase: RecordingUiPhase.error,
        errorMessage: "This recording could not be played back. It may be missing or corrupted.",
      );
    }
  }

  Future<void> deleteRecording() async {
    final path = state.localPath;
    if (path != null) await RecordingService.deleteFile(path);
    await _playerOrNull?.stop();
    state = const RecordingUiState();
  }
}

final recordingControllerProvider =
    NotifierProvider.family<RecordingController, RecordingUiState, RecordingTarget>(RecordingController.new);
