import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:shared_preferences/shared_preferences.dart";

import "../../../core/design/design.dart";
import "recording_controller.dart";

const _consentSeenKey = "interview_recording_consent_seen";

/// Shows the local-storage privacy notice (spec §2) exactly once, before the very first recording
/// attempt — never repeated once the user has dismissed it either way. Returns true if recording
/// should proceed.
Future<bool> ensureRecordingConsent(BuildContext context) async {
  final prefs = await SharedPreferences.getInstance();
  if (prefs.getBool(_consentSeenKey) == true) return true;
  if (!context.mounted) return false;
  final proceed = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (context) => AlertDialog(
      title: const Text("Recording Your Answer"),
      content: const Text(
        "Interview recordings are stored locally on this device unless you explicitly choose to upload or share them.",
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Not Now")),
        FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Continue")),
      ],
    ),
  );
  await prefs.setBool(_consentSeenKey, true);
  return proceed ?? false;
}

/// Record / stop / play / delete controls for one interview question, plus a duration readout in
/// `▶ 01:42` style (spec §5/§7). Offered as an alternative to (and combinable with) the typed
/// answer and notes fields already on the screen — never a requirement.
class RecordingControls extends ConsumerWidget {
  const RecordingControls({super.key, required this.target, required this.onRecordingReady});

  final RecordingTarget target;
  final void Function(String path, int durationSeconds) onRecordingReady;

  String _formatDuration(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return "${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(recordingControllerProvider(target));
    final controller = ref.read(recordingControllerProvider(target).notifier);

    ref.listen(recordingControllerProvider(target), (previous, next) {
      if (next.phase == RecordingUiPhase.recorded && next.localPath != null && previous?.phase != RecordingUiPhase.recorded) {
        onRecordingReady(next.localPath!, next.durationSeconds ?? 0);
      }
    });

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.mic_none_outlined, size: 18, color: AppColors.muted),
              const SizedBox(width: 6),
              Text("Record Answer (optional)", style: Theme.of(context).textTheme.titleSmall),
            ],
          ),
          const SizedBox(height: 10),
          if (state.phase == RecordingUiPhase.error && (state.errorMessage?.isNotEmpty ?? false))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(state.errorMessage!, style: const TextStyle(color: AppColors.danger, fontSize: 12)),
            ),
          switch (state.phase) {
            RecordingUiPhase.idle || RecordingUiPhase.error => OutlinedButton.icon(
                onPressed: () async {
                  final consented = await ensureRecordingConsent(context);
                  if (consented) await controller.start();
                },
                icon: const Icon(Icons.fiber_manual_record, color: AppColors.danger),
                label: const Text("Start Recording"),
              ),
            RecordingUiPhase.recording => Row(
                children: [
                  const Icon(Icons.fiber_manual_record, color: AppColors.danger, size: 14),
                  const SizedBox(width: 6),
                  Text("Recording · ${_formatDuration(state.elapsedSeconds)}"),
                  const Spacer(),
                  TextButton(onPressed: controller.cancelRecording, child: const Text("Cancel")),
                  FilledButton(onPressed: controller.stop, child: const Text("Stop")),
                ],
              ),
            RecordingUiPhase.recorded || RecordingUiPhase.playing => Row(
                children: [
                  IconButton(
                    icon: Icon(state.phase == RecordingUiPhase.playing ? Icons.pause_circle_filled : Icons.play_circle_fill),
                    color: AppColors.blue,
                    onPressed: controller.playPause,
                  ),
                  Text("▶ ${_formatDuration(state.durationSeconds ?? 0)}"),
                  const Spacer(),
                  IconButton(icon: const Icon(Icons.delete_outline, color: AppColors.danger), onPressed: controller.deleteRecording),
                ],
              ),
          },
        ],
      ),
    );
  }
}
