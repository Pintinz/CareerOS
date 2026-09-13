import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "interview_providers.dart";

/// Combined Interview Readiness dashboard (spec §25) and Interview Analytics (spec §24). Every
/// percentage here is system-calculated from real stored activity — see PROJECT_STATUS.md /
/// ARCHITECTURE.md for exactly which metrics are system-calculated vs. user self-rated.
class InterviewAnalyticsScreen extends ConsumerWidget {
  const InterviewAnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readinessAsync = ref.watch(interviewReadinessProvider(null));
    final analyticsAsync = ref.watch(interviewAnalyticsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Interview Readiness")),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(interviewReadinessProvider);
          ref.invalidate(interviewAnalyticsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            readinessAsync.when(
              loading: () => const Padding(padding: EdgeInsets.symmetric(vertical: 24), child: LinearProgressIndicator()),
              error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
              data: (readiness) {
                if (readiness.insufficientData) {
                  return Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(16)),
                    child: const Column(
                      children: [
                        Icon(Icons.insights_outlined, size: 40, color: AppColors.muted),
                        SizedBox(height: 12),
                        Text("Start practicing to build your readiness score.", textAlign: TextAlign.center, style: TextStyle(color: AppColors.muted)),
                      ],
                    ),
                  );
                }
                final c = readiness.components;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Column(
                        children: [
                          Text("${readiness.overall!.round()}%", style: Theme.of(context).textTheme.displayMedium?.copyWith(fontWeight: FontWeight.bold, color: AppColors.blue)),
                          const Text("Interview Readiness", style: TextStyle(color: AppColors.muted)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _ReadinessRow(label: "Question Practice", value: c.questionPractice),
                    _ReadinessRow(label: "STAR Coverage", value: c.starCoverage),
                    _ReadinessRow(label: "Technical Prep", value: c.technicalPrep),
                    _ReadinessRow(label: "Company Prep", value: c.companyPrep),
                    _ReadinessRow(label: "Job-Specific Prep", value: c.jobSpecificPrep),
                    _ReadinessRow(label: "Recent Consistency", value: c.recentConsistency),
                  ],
                );
              },
            ),
            const SizedBox(height: 28),
            Text("Activity", style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            analyticsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
              data: (analytics) => Column(
                children: [
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 1.6,
                    children: [
                      _StatCard(label: "Sessions Completed", value: "${analytics.sessionsCompleted}"),
                      _StatCard(label: "Questions Practiced", value: "${analytics.questionsPracticed}"),
                      _StatCard(label: "STAR Stories Ready", value: "${analytics.starStoriesReady} / ${analytics.starStoriesCreated}"),
                      _StatCard(
                        label: "Avg. Self-Rating",
                        value: analytics.averageSelfRating != null ? analytics.averageSelfRating!.toStringAsFixed(1) : "—",
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  if (analytics.byCategory.isNotEmpty) ...[
                    Align(alignment: Alignment.centerLeft, child: Text("By Category", style: Theme.of(context).textTheme.titleMedium)),
                    const SizedBox(height: 8),
                    for (final entry in analytics.byCategory.entries)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [Text(entry.key), Text("${entry.value.completed}/${entry.value.total}")],
                        ),
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
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label),
              Text(value != null ? "${value!.round()}%" : "N/A", style: const TextStyle(color: AppColors.muted)),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(value: (value ?? 0) / 100, minHeight: 6),
          ),
        ],
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
            Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
