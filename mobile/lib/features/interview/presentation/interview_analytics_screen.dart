import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "interview_providers.dart";

/// Combined Interview Preparation Readiness dashboard (spec §25) and Interview Analytics (spec §24).
/// Every percentage here is system-calculated from real stored activity — see PROJECT_STATUS.md /
/// ARCHITECTURE.md for exactly which metrics are system-calculated vs. user self-rated.
class InterviewAnalyticsScreen extends ConsumerWidget {
  const InterviewAnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readinessAsync = ref.watch(interviewReadinessProvider(null));
    final analyticsAsync = ref.watch(interviewAnalyticsProvider);

    Widget pair(Widget a, Widget b) => IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Expanded(child: a), Gap.sm, Expanded(child: b)]),
        );

    return Scaffold(
      appBar: AppBar(title: const Text("Interview Readiness")),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(interviewReadinessProvider);
          ref.invalidate(interviewAnalyticsProvider);
        },
        child: ListView(
          padding: AppSpacing.page,
          children: [
            readinessAsync.when(
              loading: () => const LoadingSkeleton(height: 200, radius: AppRadius.feature),
              error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(interviewReadinessProvider)),
              data: (readiness) {
                if (readiness.insufficientData) {
                  return const CareerCard(
                    variant: CareerCardVariant.muted,
                    child: EmptyState(
                      compact: true,
                      icon: Icons.speed_rounded,
                      title: "Not enough practice yet",
                      message: "Start practicing to build your readiness score.",
                    ),
                  );
                }
                final c = readiness.components;
                return CareerCard(
                  variant: CareerCardVariant.feature,
                  child: Column(
                    children: [
                      CareerProgressRing(
                        value: readiness.overall! / 100,
                        size: 132,
                        strokeWidth: 12,
                        tone: AppTone.warning,
                        semanticLabel: "Interview preparation readiness",
                        child: Text("${readiness.overall!.round()}%", style: context.text.headlineMedium),
                      ),
                      Gap.sm,
                      Text("Interview Preparation Readiness", style: context.text.titleMedium),
                      const SizedBox(height: 2),
                      Text("Calculated from your practice, STAR stories and research — not a prediction.", style: context.text.bodySmall, textAlign: TextAlign.center),
                      Gap.lg,
                      _ReadinessRow(label: "Question Practice", value: c.questionPractice),
                      _ReadinessRow(label: "STAR Coverage", value: c.starCoverage),
                      _ReadinessRow(label: "Technical Prep", value: c.technicalPrep),
                      _ReadinessRow(label: "Company Prep", value: c.companyPrep),
                      _ReadinessRow(label: "Job-Specific Prep", value: c.jobSpecificPrep),
                      _ReadinessRow(label: "Recent Consistency", value: c.recentConsistency),
                    ],
                  ),
                );
              },
            ),
            Gap.section,
            const SectionHeader(title: "Activity"),
            analyticsAsync.when(
              loading: () => const LoadingSkeleton(height: 160, radius: AppRadius.card),
              error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(interviewAnalyticsProvider)),
              data: (analytics) => Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  pair(
                    StatCard(label: "Sessions Completed", value: "${analytics.sessionsCompleted}", icon: AppIcons.interview, tone: AppTone.warning),
                    StatCard(label: "Questions Practiced", value: "${analytics.questionsPracticed}", icon: Icons.forum_outlined),
                  ),
                  Gap.sm,
                  pair(
                    StatCard(
                      label: "STAR Stories Ready",
                      value: "${analytics.starStoriesReady} / ${analytics.starStoriesCreated}",
                      caption: "Complete / written",
                      progress: analytics.starStoriesCreated == 0 ? null : analytics.starStoriesReady / analytics.starStoriesCreated,
                      icon: AppIcons.starStory,
                      tone: AppTone.success,
                    ),
                    StatCard(
                      label: "Avg. Self-Rating",
                      value: analytics.averageSelfRating?.toStringAsFixed(1),
                      caption: analytics.averageSelfRating == null ? "No ratings yet" : "Your own rating, out of 5",
                      progress: analytics.averageSelfRating == null ? null : analytics.averageSelfRating! / 5,
                      icon: Icons.star_outline_rounded,
                      tone: AppTone.purple,
                    ),
                  ),
                  if (analytics.byCategory.isNotEmpty) ...[
                    Gap.xl,
                    const SectionHeader(title: "By Category", subtitle: "Questions practised in each area"),
                    CareerListGroup(
                      children: [
                        for (final entry in analytics.byCategory.entries)
                          CareerListRow(
                            icon: Icons.category_outlined,
                            tone: AppTone.warning,
                            title: entry.key,
                            trailing: Text("${entry.value.completed}/${entry.value.total}", style: context.text.titleSmall),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReadinessRow extends StatelessWidget {
  const _ReadinessRow({required this.label, required this.value});

  final String label;
  final double? value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(label, style: context.text.bodyMedium?.copyWith(color: context.colors.textPrimary))),
              Text(value != null ? "${value!.round()}%" : "—", style: context.text.labelMedium),
            ],
          ),
          Gap.xxs,
          CareerProgressBar(value: (value ?? 0) / 100, height: 6, tone: AppTone.warning, semanticLabel: label),
        ],
      ),
    );
  }
}
