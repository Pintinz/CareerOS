import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

class TestResultsScreen extends ConsumerWidget {
  const TestResultsScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final examState = ref.watch(examControllerProvider(sessionId));
    final result = examState.result;

    return Scaffold(
      appBar: AppBar(title: const Text("Results"), automaticallyImplyLeading: false),
      body: result == null
          ? examState.error != null
              ? Center(child: Text(examState.error!.userMessage))
              : const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Center(
                  child: Column(
                    children: [
                      Text(
                        "${result.percentage.round()}%",
                        style: Theme.of(context).textTheme.displayMedium?.copyWith(fontWeight: FontWeight.bold, color: AppColors.blue),
                      ),
                      const SizedBox(height: 4),
                      Text(result.performanceLabel, style: Theme.of(context).textTheme.titleMedium),
                      if (result.autoSubmitted) ...[
                        const SizedBox(height: 4),
                        const Text("Auto-submitted when time expired", style: TextStyle(color: AppColors.warning, fontSize: 12)),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(child: _StatTile(label: "Correct", value: "${result.correctCount}", color: AppColors.success)),
                    Expanded(child: _StatTile(label: "Incorrect", value: "${result.incorrectCount}", color: AppColors.danger)),
                    Expanded(child: _StatTile(label: "Unanswered", value: "${result.unansweredCount}", color: AppColors.muted)),
                  ],
                ),
                if (result.timeUsedSeconds != null) ...[
                  const SizedBox(height: 12),
                  Text("Time used: ${_formatDuration(result.timeUsedSeconds!)}", style: const TextStyle(color: AppColors.muted)),
                ],
                const SizedBox(height: 24),
                if (result.sectionBreakdown.isNotEmpty) ...[
                  Text("Section Breakdown", style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final entry in result.sectionsSortedByPercentage)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(entry.key),
                              Text("${entry.value.percentage.round()}%", style: const TextStyle(fontWeight: FontWeight.w600)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(value: entry.value.percentage / 100, minHeight: 6),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 12),
                  if (result.sectionsSortedByPercentage.isNotEmpty) ...[
                    _StrongestWeakest(sections: result.sectionsSortedByPercentage),
                    const SizedBox(height: 24),
                  ],
                ],
                ElevatedButton(
                  onPressed: () => context.pushReplacement("/prepare/aptitude/sessions/$sessionId/review"),
                  child: const Text("Review Answers"),
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => context.push(
                    "/prepare/aptitude/configure",
                    extra: const AptitudeConfigureArgs(),
                  ),
                  child: const Text("Retake / Practice Similar"),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context.go("/home"),
                  child: const Text("Done"),
                ),
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

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color)),
        Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
      ],
    );
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
    return Row(
      children: [
        Expanded(
          child: _AreaCard(label: "Strongest Area", name: strongest.key, color: AppColors.success),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _AreaCard(label: "Weakest Area", name: weakest.key, color: AppColors.warning),
        ),
      ],
    );
  }
}

class _AreaCard extends StatelessWidget {
  const _AreaCard({required this.label, required this.name, required this.color});

  final String label;
  final String name;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.muted)),
          const SizedBox(height: 4),
          Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
