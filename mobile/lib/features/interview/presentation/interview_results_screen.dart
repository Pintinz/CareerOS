import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "interview_configuration_screen.dart";
import "interview_providers.dart";

class InterviewResultsScreen extends ConsumerWidget {
  const InterviewResultsScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(interviewSessionControllerProvider(sessionId));
    final completion = state.completion;

    return Scaffold(
      appBar: AppBar(title: const Text("Interview Practice Complete"), automaticallyImplyLeading: false),
      body: completion == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Row(
                  children: [
                    Expanded(child: _StatTile(label: "Completed", value: "${completion.questionsCompleted}", color: AppColors.success)),
                    Expanded(child: _StatTile(label: "Skipped", value: "${completion.questionsSkipped}", color: AppColors.muted)),
                    Expanded(
                      child: _StatTile(
                        label: "Avg. Self-Rating",
                        value: completion.averageSelfRating != null ? completion.averageSelfRating!.toStringAsFixed(1) : "—",
                        color: AppColors.blue,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (completion.averageAnswerLength != null)
                  Text("Average answer length: ${completion.averageAnswerLength!.round()} words", style: const TextStyle(color: AppColors.muted)),
                if (completion.starUsageRate != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text("STAR usage: ${completion.starUsageRate!.round()}%", style: const TextStyle(color: AppColors.muted)),
                  ),
                const SizedBox(height: 24),
                Text("Category Breakdown", style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                for (final entry in completion.categoryBreakdown.entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [Text(entry.key), Text("${entry.value.completed}/${entry.value.total}")],
                        ),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: entry.value.total == 0 ? 0 : entry.value.completed / entry.value.total,
                            minHeight: 6,
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                if (completion.areasPracticed.isNotEmpty) ...[
                  const Text("Areas Practiced", style: TextStyle(fontWeight: FontWeight.w600)),
                  Text(completion.areasPracticed.join(", "), style: const TextStyle(color: AppColors.muted)),
                  const SizedBox(height: 12),
                ],
                if (completion.areasStillUncovered.isNotEmpty) ...[
                  const Text("Areas Still Uncovered", style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.warning)),
                  Text(completion.areasStillUncovered.join(", "), style: const TextStyle(color: AppColors.muted)),
                ],
                const SizedBox(height: 28),
                OutlinedButton(
                  onPressed: () => context.push("/prepare/interview/configure", extra: const InterviewConfigureArgs()),
                  child: const Text("Practice Again"),
                ),
                const SizedBox(height: 12),
                TextButton(onPressed: () => context.go("/home"), child: const Text("Done")),
              ],
            ),
    );
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
        Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color)),
        Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 11), textAlign: TextAlign.center),
      ],
    );
  }
}
