import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
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
      bottomNavigationBar: completion == null
          ? null
          : BottomActionBar(
              secondary: AppOutlineButton(expand: false, label: "Done", onPressed: () => context.go("/home?tab=prepare")),
              primary: PrimaryButton(
                label: "Practice Again",
                onPressed: () => context.push("/prepare/interview/configure", extra: const InterviewConfigureArgs()),
              ),
            ),
      body: completion == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: AppSpacing.page,
              children: [
                CareerCard(
                  variant: CareerCardVariant.feature,
                  child: Column(
                    children: [
                      const IconTile(icon: Icons.celebration_outlined, tone: AppTone.success, size: 56, circle: true),
                      Gap.sm,
                      Text("Nice work — session complete", style: context.text.titleLarge, textAlign: TextAlign.center),
                      const SizedBox(height: 2),
                      Text("Here's what you covered. Ratings are your own self-assessment.", style: context.text.bodySmall, textAlign: TextAlign.center),
                      Gap.lg,
                      Row(
                        children: [
                          Expanded(
                            child: MetricTile(
                              label: "Completed",
                              value: "${completion.questionsCompleted}",
                              tone: AppTone.success,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                          Expanded(
                            child: MetricTile(
                              label: "Skipped",
                              value: "${completion.questionsSkipped}",
                              tone: AppTone.neutral,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                          Expanded(
                            child: MetricTile(
                              label: "Avg. Self-Rating",
                              value: completion.averageSelfRating?.toStringAsFixed(1),
                              tone: AppTone.primary,
                              alignment: CrossAxisAlignment.center,
                            ),
                          ),
                        ],
                      ),
                      if (completion.averageAnswerLength != null || completion.starUsageRate != null) ...[
                        Gap.md,
                        Wrap(
                          spacing: AppSpacing.xs,
                          runSpacing: AppSpacing.xs,
                          alignment: WrapAlignment.center,
                          children: [
                            if (completion.averageAnswerLength != null)
                              TagChip(label: "Average answer length: ${completion.averageAnswerLength!.round()} words"),
                            if (completion.starUsageRate != null) TagChip(label: "STAR usage: ${completion.starUsageRate!.round()}%"),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                if (completion.categoryBreakdown.isNotEmpty) ...[
                  Gap.section,
                  const SectionHeader(title: "Category Breakdown"),
                  CareerCard(
                    variant: CareerCardVariant.outlined,
                    child: Column(
                      children: [
                        for (final entry in completion.categoryBreakdown.entries)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(child: Text(entry.key, style: context.text.titleSmall)),
                                    Text("${entry.value.completed}/${entry.value.total}", style: context.text.labelMedium),
                                  ],
                                ),
                                Gap.xs,
                                CareerProgressBar(
                                  value: entry.value.total == 0 ? 0 : entry.value.completed / entry.value.total,
                                  tone: AppTone.warning,
                                  semanticLabel: entry.key,
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
                if (completion.areasPracticed.isNotEmpty) ...[
                  Gap.xl,
                  DetailSection(
                    title: "Areas Practiced",
                    icon: Icons.check_circle_outline_rounded,
                    child: Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: AppSpacing.xs,
                      children: [for (final area in completion.areasPracticed) TagChip(label: area, tone: AppTone.success)],
                    ),
                  ),
                ],
                if (completion.areasStillUncovered.isNotEmpty)
                  DetailSection(
                    title: "Areas Still Uncovered",
                    icon: Icons.flag_outlined,
                    child: Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: AppSpacing.xs,
                      children: [for (final area in completion.areasStillUncovered) TagChip(label: area, tone: AppTone.warning)],
                    ),
                  ),
              ],
            ),
    );
  }
}
