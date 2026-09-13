import "dart:io";

import "package:path_provider/path_provider.dart";
import "package:permission_handler/permission_handler.dart";
import "package:record/record.dart";

/// What went wrong with a recording/playback attempt (spec §6) — every case must leave the
/// screen usable (typed answer/notes still work) rather than crashing the session.
enum RecordingErrorKind {
  permissionDenied,
  permissionPermanentlyDenied,
  microphoneUnavailable,
  recordingInterrupted,
  storageFailure,
  fileMissing,
  playbackFailure,
}

class RecordingException implements Exception {
  const RecordingException(this.kind, this.message);

  final RecordingErrorKind kind;
  final String message;

  @override
  String toString() => message;
}

/// Thin wrapper around the `record` package (recording) — playback is handled separately by
/// `audioplayers` in the presentation layer, since it has a very different lifecycle. Recordings
/// are written under the app's private documents directory, never a public/shared location, and
/// are never uploaded anywhere automatically (spec §1/§4).
class RecordingService {
  RecordingService({AudioRecorder? recorder}) : _recorderOrNull = recorder;

  AudioRecorder? _recorderOrNull;

  // Constructed lazily so a test subclass that overrides every method touching the recorder never
  // has to pay for (or stub out) the real platform channel that `AudioRecorder()` opens.
  AudioRecorder get _recorder => _recorderOrNull ??= AudioRecorder();

  /// Requests microphone permission — only ever called at the moment the user taps Record, never
  /// at app startup (spec §3).
  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    if (status.isGranted) return true;
    if (status.isPermanentlyDenied) {
      throw const RecordingException(
        RecordingErrorKind.permissionPermanentlyDenied,
        "Microphone access is turned off for CareerOS. Enable it in your device Settings to record an answer.",
      );
    }
    throw const RecordingException(
      RecordingErrorKind.permissionDenied,
      "Microphone permission is needed to record your answer. You can still type an answer or notes instead.",
    );
  }

  Future<String> _newRecordingPath() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final recordingsDir = Directory("${dir.path}/interview_recordings");
      if (!await recordingsDir.exists()) {
        await recordingsDir.create(recursive: true);
      }
      final uniqueName = "${DateTime.now().microsecondsSinceEpoch}-${identityHashCode(recordingsDir)}";
      return "${recordingsDir.path}/$uniqueName.m4a";
    } catch (e) {
      throw const RecordingException(RecordingErrorKind.storageFailure, "Could not prepare local storage for the recording.");
    }
  }

  Future<String> startRecording() async {
    await requestPermission();
    try {
      if (!await _recorder.hasPermission()) {
        throw const RecordingException(RecordingErrorKind.permissionDenied, "Microphone permission was not granted.");
      }
      final path = await _newRecordingPath();
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
      return path;
    } on RecordingException {
      rethrow;
    } catch (e) {
      throw RecordingException(RecordingErrorKind.microphoneUnavailable, "The microphone is unavailable right now: $e");
    }
  }

  Future<void> pause() async {
    try {
      await _recorder.pause();
    } catch (e) {
      throw const RecordingException(RecordingErrorKind.recordingInterrupted, "Recording was interrupted.");
    }
  }

  Future<void> resume() async {
    try {
      await _recorder.resume();
    } catch (e) {
      throw const RecordingException(RecordingErrorKind.recordingInterrupted, "Could not resume recording.");
    }
  }

  Future<String?> stop() async {
    try {
      final path = await _recorder.stop();
      if (path == null || !await File(path).exists()) {
        throw const RecordingException(RecordingErrorKind.fileMissing, "The recording could not be found after stopping.");
      }
      return path;
    } on RecordingException {
      rethrow;
    } catch (e) {
      throw const RecordingException(RecordingErrorKind.storageFailure, "Could not save the recording to local storage.");
    }
  }

  Future<void> cancel() async {
    try {
      final path = await _recorder.stop();
      if (path != null) {
        final file = File(path);
        if (await file.exists()) await file.delete();
      }
    } catch (_) {
      // Best-effort cleanup — never surfaced as a hard failure.
    }
  }

  Future<void> dispose() => _recorderOrNull?.dispose() ?? Future.value();

  static Future<void> deleteFile(String path) async {
    try {
      final file = File(path);
      if (await file.exists()) await file.delete();
    } catch (_) {
      // A failed local delete isn't fatal — the metadata row is still removed server-side.
    }
  }

  static Future<bool> fileExists(String path) => File(path).exists();
}
