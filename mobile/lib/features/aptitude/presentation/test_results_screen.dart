import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

/// Results (spec §30): score hero → correct/incorrect/unanswered → section performance → strongest
/// and weakest areas → Review Answers (primary). No ads on this screen.
class TestResultsScreen extends ConsumerWidget {
  const TestResultsScreen({super.key, required this.sessionId});

  final String sessionId;

  static AppTone _scoreTone(double percentage) => percentage >= 70
      ? AppTone.success
      : percentage >= 50
          ? AppTone.warning
          : AppTone.danger;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final examState = ref.watch(examControllerProvider(sessionId));
    final result = examState.result;

    return Scaffold(
      appBar: AppBar(title: const Text("Results"), automaticallyImplyLeading: false),
      bottomNavigationBar: result == null
          ? null
          : BottomActionBar(
              secondary: AppOutlineButton(
                expand: false,
                label: "Practice Again",
                onPressed: () => context.push("/prepare/aptitude/configure", extra: const AptitudeConfigureArgs()),
              ),
              primary: PrimaryButton(
                label: "Review Answers",
                onPressed: () => context.pushReplacement("/prepare/aptitude/sessions/$sessionId/review"),
              ),
            ),
      body: result == null
          ? examState.error != null
              ? ErrorState(title: "We couldn't load your results", message: examState.error!.userMessage)
              : const Center(child: CircularProgressIndicator())
          : ListView(
              padding: AppSpacing.page,
              children: [
                CareerCard(
                  variant: CareerCardVariant.feature,
                  child: Column(
                    children: [
                      CareerProgressRing(
                        value: result.percentage / 100,
                        size: 148,
                        strokeWidth: 14,
                        tone: _scoreTone(result.percentage),
                        semanticLabel: "Score",
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text("${result.percentage.round()}%", style: context.text.displaySmall),
                            Text("score", style: context.text.bodySmall),
                          ],
                        ),
                      ),
                      Gap.md,
                      Text(result.performanceLabel, style: context.text.titleLarge),
                      if (result.autoSubmitted) ...[
                        Gap.xs,
                        const StatusChip(label: "Auto-submitted when time expired", tone: AppTone.warning, icon: AppIcons.timer),
                      ],
                      Gap.lg,
                      Divider(color: context.colors.border),
                      Gap.md,
                      Row(
                        children: [
                          Expanded(
                            child: MetricTile(
                              label: "Correct",
                              value: "${result.correctCount}",
                              tone: AppTone.success,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                          Expanded(
                            child: MetricTile(
                              label: "Incorrect",
                              value: "${result.incorrectCount}",
                              tone: AppTone.danger,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                          Expanded(
                            child: MetricTile(
                              label: "Unanswered",
                              value: "${result.unansweredCount}",
                              tone: AppTone.neutral,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                        ],
                      ),
                      if (result.timeUsedSeconds != null) ...[
                        Gap.md,
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(AppIcons.time, size: 16, color: context.colors.textSecondary),
                            Gap.xxs,
                            Text("Time used: ${_formatDuration(result.timeUsedSeconds!)}", style: context.text.bodySmall),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                if (result.sectionBreakdown.isNotEmpty) ...[
                  Gap.section,
                  const SectionHeader(title: "Section Performance"),
                  CareerCard(
                    variant: CareerCardVariant.outlined,
                    child: Column(
                      children: [
                        for (final entry in result.sectionsSortedByPercentage)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(child: Text(entry.key, style: context.text.titleSmall)),
                                    Text(
                                      "${entry.value.correct}/${entry.value.total} · ${entry.value.percentage.round()}%",
                                      style: context.text.labelMedium,
                                    ),
                                  ],
                                ),
                                Gap.xs,
                                CareerProgressBar(
                                  value: entry.value.percentage / 100,
                                  tone: _scoreTone(entry.value.percentage),
                                  semanticLabel: entry.key,
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (result.sectionsSortedByPercentage.isNotEmpty) ...[
                    Gap.md,
                    _StrongestWeakest(sections: result.sectionsSortedByPercentage),
                  ],
                ],
                Gap.lg,
                Center(child: TextButton(onPressed: () => context.go("/home?tab=prepare"), child: const Text("Done"))),
              ],
            ),
    );
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return "${minutes}m ${secs}s";
  }
}

class _StrongestWeakest extends StatelessWidget {
  const _StrongestWeakest({required this.sections});

  final List<MapEntry<String, dynamic>> sections;

  @override
  Widget build(BuildContext context) {
    if (sections.isEmpty) return const SizedBox.shrink();
    final strongest = sections.first;
    final weakest = sections.last;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(child: _AreaCard(label: "Strongest Area", name: strongest.key, tone: AppTone.success, icon: Icons.trending_up_rounded)),
          Gap.sm,
          Expanded(child: _AreaCard(label: "Weakest Area", name: weakest.key, tone: AppTone.warning, icon: Icons.track_changes_rounded)),
        ],
      ),
    );
  }
}

class _AreaCard extends StatelessWidget {
  const _AreaCard({required this.label, required this.name, required this.tone, required this.icon});

  final String label;
  final String name;
  final AppTone tone;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      color: tone.tint(context),
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: tone.onTint(context)),
              Gap.xxs,
              Flexible(child: Text(label, style: context.text.labelSmall?.copyWith(color: tone.onTint(context)))),
            ],
          ),
          Gap.xs,
          Text(name, style: context.text.titleSmall),
        ],
      ),
    );
  }
}
