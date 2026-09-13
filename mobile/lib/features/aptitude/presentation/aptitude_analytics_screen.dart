import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

class AptitudeAnalyticsScreen extends ConsumerWidget {
  const AptitudeAnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(aptitudeAnalyticsProvider);
    final recommendationsAsync = ref.watch(aptitudeRecommendationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Aptitude Performance")),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(aptitudeAnalyticsProvider);
          ref.invalidate(aptitudeRecommendationsProvider);
        },
        child: analyticsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text(e.userMessage)),
          data: (analytics) {
            if (analytics.testsCompleted == 0) {
              return ListView(
                padding: const EdgeInsets.all(32),
                children: const [
                  SizedBox(height: 80),
                  Icon(Icons.insights_outlined, size: 48, color: AppColors.muted),
                  SizedBox(height: 16),
                  Text(
                    "No tests completed yet. Once you finish a test, your performance shows up here.",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.muted),
                  ),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.all(20),
              children: [
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.6,
                  children: [
                    _StatCard(label: "Tests Completed", value: "${analytics.testsCompleted}"),
                    _StatCard(
                      label: "Average Score",
                      value: analytics.averageScore != null ? "${analytics.averageScore!.round()}%" : "—",
                    ),
                    _StatCard(label: "Questions Answered", value: "${analytics.questionsAnswered}"),
                    _StatCard(
                      label: "Best Score",
                      value: analytics.bestScore != null ? "${analytics.bestScore!.round()}%" : "—",
                    ),
                  ],
                ),
                const SizedBox(height: 28),
                if (analytics.byCategory.isNotEmpty) ...[
                  Text("By Section", style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final entry in analytics.byCategory.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(entry.key),
                              Text(
                                "${entry.value.correct}/${entry.value.attempted} (${entry.value.percentage.round()}%)",
                                style: const TextStyle(color: AppColors.muted, fontSize: 12),
                              ),
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
                  const SizedBox(height: 24),
                ],
                recommendationsAsync.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (recommendations) {
                    if (recommendations.weakTopics.isEmpty) return const SizedBox.shrink();
                    final practiceableSlugs =
                        recommendations.weakTopics.map((t) => t.topicSlug).whereType<String>().toList();
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Recommended Practice", style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 4),
                        Text(
                          "Based on topics with at least ${recommendations.minAttemptsRequired} attempted questions.",
                          style: const TextStyle(color: AppColors.muted, fontSize: 12),
                        ),
                        const SizedBox(height: 12),
                        for (final topic in recommendations.weakTopics)
                          Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              title: Text(topic.topicName),
                              subtitle: Text("${topic.categoryName} · ${topic.attempted} attempted"),
                              trailing: Text(
                                "${topic.accuracy.round()}%",
                                style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600),
                              ),
                            ),
                          ),
                        const SizedBox(height: 8),
                        if (practiceableSlugs.isNotEmpty)
                          ElevatedButton(
                            onPressed: () => context.push(
                              "/prepare/aptitude/configure",
                              extra: AptitudeConfigureArgs(topicSlugs: practiceableSlugs),
                            ),
                            child: const Text("Practice Weak Areas"),
                          ),
                      ],
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

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
