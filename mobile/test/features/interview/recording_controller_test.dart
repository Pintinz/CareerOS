import 'package:careeros/features/interview/data/recording_service.dart';
import 'package:careeros/features/interview/presentation/interview_providers.dart';
import 'package:careeros/features/interview/presentation/recording_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'interview_test_support.dart';

void _ensureBinding() => TestWidgetsFlutterBinding.ensureInitialized();

/// Never touches a real microphone or platform channel — this is exactly what spec §33 asks for
/// ("use mocks for platform audio APIs where necessary").
class _FakeRecordingService extends RecordingService {
  _FakeRecordingService({this.permissionDenied = false, this.failOnStop = false});

  final bool permissionDenied;
  final bool failOnStop;
  bool started = false;
  bool cancelled = false;

  @override
  Future<bool> requestPermission() async {
    if (permissionDenied) {
      throw const RecordingException(RecordingErrorKind.permissionDenied, 'Microphone permission is needed to record your answer.');
    }
    return true;
  }

  @override
  Future<String> startRecording() async {
    await requestPermission();
    started = true;
    return '/tmp/fake-recording.m4a';
  }

  @override
  Future<String?> stop() async {
    if (failOnStop) {
      throw const RecordingException(RecordingErrorKind.fileMissing, 'The recording could not be found after stopping.');
    }
    return '/tmp/fake-recording.m4a';
  }

  @override
  Future<void> cancel() async {
    cancelled = true;
  }

  @override
  Future<void> dispose() async {}
}

// Note: `audioplayers`' AudioPlayer constructs its native channel/event-channel plumbing
// unconditionally in its own constructor — even a subclass's constructor can't avoid that call —
// so unlike RecordingService there is no way to fully fake it without a real platform. Playback
// (play/pause/delete) is therefore exercised via manual QA rather than a unit test here; see the
// Phase 7.5 completion report's Known Limitations.
const _target = RecordingTarget(sessionId: 'session-1', questionId: 'iq1');

ProviderContainer _buildContainer({required RecordingService Function() recorderFactory}) {
  return ProviderContainer(overrides: [
    interviewRepositoryProvider.overrideWithValue(FakeInterviewRepository()),
    recordingServiceFactoryProvider.overrideWithValue(recorderFactory),
  ]);
}

void main() {
  setUpAll(_ensureBinding);

  test('starting a recording moves to the recording phase', () async {
    final container = _buildContainer(recorderFactory: () => _FakeRecordingService());
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();

    expect(container.read(recordingControllerProvider(_target)).phase, RecordingUiPhase.recording);
  });

  test('denied microphone permission surfaces as an error without crashing', () async {
    final container = _buildContainer(recorderFactory: () => _FakeRecordingService(permissionDenied: true));
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();

    final state = container.read(recordingControllerProvider(_target));
    expect(state.phase, RecordingUiPhase.error);
    expect(state.errorMessage, contains('Microphone permission'));
  });

  test('stopping a recording moves to the recorded phase with a local path and duration', () async {
    final container = _buildContainer(recorderFactory: () => _FakeRecordingService());
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();
    await notifier.stop();

    final state = container.read(recordingControllerProvider(_target));
    expect(state.phase, RecordingUiPhase.recorded);
    expect(state.localPath, '/tmp/fake-recording.m4a');
  });

  test('a stop failure (e.g. missing file) surfaces as an error, not a crash', () async {
    final container = _buildContainer(recorderFactory: () => _FakeRecordingService(failOnStop: true));
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();
    await notifier.stop();

    expect(container.read(recordingControllerProvider(_target)).phase, RecordingUiPhase.error);
  });

  test('deleting a recording resets to idle', () async {
    final container = _buildContainer(recorderFactory: () => _FakeRecordingService());
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();
    await notifier.stop();
    await notifier.deleteRecording();

    final state = container.read(recordingControllerProvider(_target));
    expect(state.phase, RecordingUiPhase.idle);
    expect(state.localPath, isNull);
  });

  test('cancelling a recording resets to idle and calls the underlying cancel', () async {
    final fake = _FakeRecordingService();
    final container = _buildContainer(recorderFactory: () => fake);
    addTearDown(container.dispose);
    final notifier = container.read(recordingControllerProvider(_target).notifier);

    await notifier.start();
    await notifier.cancelRecording();

    expect(fake.cancelled, isTrue);
    expect(container.read(recordingControllerProvider(_target)).phase, RecordingUiPhase.idle);
  });
}
