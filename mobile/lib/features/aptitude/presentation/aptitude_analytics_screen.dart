import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

class AptitudeAnalyticsScreen extends ConsumerWidget {
  const AptitudeAnalyticsScreen({super.key});

  static AppTone _tone(double percentage) => percentage >= 70
      ? AppTone.success
      : percentage >= 50
          ? AppTone.warning
          : AppTone.danger;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(aptitudeAnalyticsProvider);
    final recommendationsAsync = ref.watch(aptitudeRecommendationsProvider);

    Widget pair(Widget a, Widget b) => IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Expanded(child: a), Gap.sm, Expanded(child: b)]),
        );

    return Scaffold(
      appBar: AppBar(title: const Text("Aptitude Performance")),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(aptitudeAnalyticsProvider);
          ref.invalidate(aptitudeRecommendationsProvider);
        },
        child: analyticsAsync.when(
          loading: () => const SkeletonList(itemCount: 3),
          error: (e, _) => ErrorState(
            title: "We couldn't load your performance",
            message: e.userMessage,
            onRetry: () => ref.invalidate(aptitudeAnalyticsProvider),
          ),
          data: (analytics) {
            if (analytics.testsCompleted == 0) {
              return ListView(
                children: [
                  EmptyState(
                    icon: AppIcons.analytics,
                    title: "No results yet",
                    message: "No tests completed yet. Once you finish a test, your performance shows up here.",
                    actionLabel: "Start a Practice Test",
                    onAction: () => context.push("/prepare/aptitude/configure", extra: const AptitudeConfigureArgs()),
                  ),
                ],
              );
            }
            return ListView(
              padding: AppSpacing.page,
              children: [
                pair(
                  StatCard(label: "Tests Completed", value: "${analytics.testsCompleted}", icon: Icons.task_alt_rounded),
                  StatCard(
                    label: "Average Score",
                    value: analytics.averageScore != null ? "${analytics.averageScore!.round()}%" : "—",
                    progress: analytics.averageScore == null ? null : analytics.averageScore! / 100,
                    icon: Icons.insights_rounded,
                    tone: AppTone.success,
                  ),
                ),
                Gap.sm,
                pair(
                  StatCard(label: "Questions Answered", value: "${analytics.questionsAnswered}", icon: AppIcons.aptitude, tone: AppTone.purple),
                  StatCard(
                    label: "Best Score",
                    value: analytics.bestScore != null ? "${analytics.bestScore!.round()}%" : "—",
                    progress: analytics.bestScore == null ? null : analytics.bestScore! / 100,
                    icon: Icons.emoji_events_outlined,
                    tone: AppTone.warning,
                  ),
                ),
                if (analytics.byCategory.isNotEmpty) ...[
                  Gap.section,
                  const SectionHeader(title: "By Section"),
                  CareerCard(
                    variant: CareerCardVariant.outlined,
                    child: Column(
                      children: [
                        for (final entry in analytics.byCategory.entries)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(child: Text(entry.key, style: context.text.titleSmall)),
                                    Text(
                                      "${entry.value.correct}/${entry.value.attempted} (${entry.value.percentage.round()}%)",
                                      style: context.text.labelMedium,
                                    ),
                                  ],
                                ),
                                Gap.xs,
                                CareerProgressBar(
                                  value: entry.value.percentage / 100,
                                  tone: _tone(entry.value.percentage),
                                  semanticLabel: entry.key,
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
                recommendationsAsync.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (recommendations) {
                    if (recommendations.weakTopics.isEmpty) return const SizedBox.shrink();
                    final practiceableSlugs = recommendations.weakTopics.map((t) => t.topicSlug).whereType<String>().toList();
                    return Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.section),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          SectionHeader(
                            title: "Recommended Practice",
                            subtitle: "Based on topics with at least ${recommendations.minAttemptsRequired} attempted questions.",
                          ),
                          CareerListGroup(
                            children: [
                              for (final topic in recommendations.weakTopics)
                                CareerListRow(
                                  icon: Icons.track_changes_rounded,
                                  tone: AppTone.danger,
                                  title: topic.topicName,
                                  subtitle: "${topic.categoryName} · ${topic.attempted} attempted",
                                  trailing: StatusChip(label: "${topic.accuracy.round()}% accuracy", tone: AppTone.danger, dense: true),
                                ),
                            ],
                          ),
                          if (practiceableSlugs.isNotEmpty) ...[
                            Gap.md,
                            PrimaryButton(
                              label: "Practice Weak Areas",
                              icon: Icons.track_changes_rounded,
                              onPressed: () => context.push(
                                "/prepare/aptitude/configure",
                                extra: AptitudeConfigureArgs(topicSlugs: practiceableSlugs),
                              ),
                            ),
                          ],
                        ],
                      ),
                    );
                  },
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
