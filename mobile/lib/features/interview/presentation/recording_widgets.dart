import "package:flutter/material.dart";
import "package:flutter/semantics.dart";
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
      icon: const Icon(Icons.mic_none_rounded),
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
/// answer and notes fields already on the screen — never a requirement. The recording state is
/// unmistakable: red surface, pulsing dot, "Recording" text and elapsed time, announced to screen
/// readers.
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
    final colors = context.colors;

    ref.listen(recordingControllerProvider(target), (previous, next) {
      if (next.phase == RecordingUiPhase.recorded && next.localPath != null && previous?.phase != RecordingUiPhase.recorded) {
        onRecordingReady(next.localPath!, next.durationSeconds ?? 0);
      }
      if (previous?.phase != next.phase) {
        final announcement = switch (next.phase) {
          RecordingUiPhase.recording => "Recording started",
          RecordingUiPhase.recorded => "Recording stopped",
          _ => null,
        };
        if (announcement != null) {
          SemanticsService.sendAnnouncement(View.of(context), announcement, Directionality.of(context));
        }
      }
    });

    final isRecording = state.phase == RecordingUiPhase.recording;

    return AnimatedContainer(
      duration: AppMotion.of(context),
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: isRecording ? AppTone.danger.tint(context) : colors.surfaceMuted,
        borderRadius: AppRadius.cardAll,
        border: Border.all(color: isRecording ? AppColors.error : Colors.transparent, width: 1.4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.mic_none_rounded, size: 18, color: colors.textSecondary),
              const SizedBox(width: 6),
              Text("Record Answer (optional)", style: context.text.titleSmall),
            ],
          ),
          Gap.xs,
          if (state.phase == RecordingUiPhase.error && (state.errorMessage?.isNotEmpty ?? false))
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Text(state.errorMessage!, style: context.text.bodySmall?.copyWith(color: AppColors.error)),
            ),
          switch (state.phase) {
            RecordingUiPhase.idle || RecordingUiPhase.error => OutlinedButton.icon(
                onPressed: () async {
                  final consented = await ensureRecordingConsent(context);
                  if (consented) await controller.start();
                },
                icon: const Icon(Icons.fiber_manual_record, color: AppColors.error),
                label: const Text("Start Recording"),
              ),
            RecordingUiPhase.recording => Row(
                children: [
                  const _PulsingDot(),
                  const SizedBox(width: 8),
                  Text(
                    "Recording · ${_formatDuration(state.elapsedSeconds)}",
                    style: context.text.titleSmall?.copyWith(color: AppColors.error, fontFeatures: const [FontFeature.tabularFigures()]),
                  ),
                  const Spacer(),
                  TextButton(onPressed: controller.cancelRecording, child: const Text("Cancel")),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(backgroundColor: AppColors.error, minimumSize: const Size(64, 44)),
                    onPressed: controller.stop,
                    icon: const Icon(Icons.stop_rounded, size: 18),
                    label: const Text("Stop"),
                  ),
                ],
              ),
            RecordingUiPhase.recorded || RecordingUiPhase.playing => Row(
                children: [
                  IconButton(
                    tooltip: state.phase == RecordingUiPhase.playing ? "Pause" : "Play recording",
                    icon: Icon(state.phase == RecordingUiPhase.playing ? Icons.pause_circle_filled : Icons.play_circle_fill),
                    iconSize: 32,
                    color: colors.primary,
                    onPressed: controller.playPause,
                  ),
                  Text("▶ ${_formatDuration(state.durationSeconds ?? 0)}", style: context.text.titleSmall),
                  const Spacer(),
                  IconButton(
                    tooltip: "Delete recording",
                    icon: const Icon(AppIcons.delete, color: AppColors.error),
                    onPressed: controller.deleteRecording,
                  ),
                ],
              ),
          },
        ],
      ),
    );
  }
}

class _PulsingDot extends StatefulWidget {
  const _PulsingDot();

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _controller.value = 1;
    } else if (!_controller.isAnimating) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.35, end: 1).animate(_controller),
      child: const Icon(Icons.fiber_manual_record, color: AppColors.error, size: 16),
    );
  }
}
