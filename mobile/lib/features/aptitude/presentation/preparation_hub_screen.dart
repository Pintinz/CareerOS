import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../theme/app_colors.dart";
import "../../interview/presentation/interview_providers.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

/// The Prepare tab body (spec §2/§6): "What are you preparing for?" with both a real Aptitude
/// Test path and a real Interview Preparation path (Phase 7).
class PreparationHubScreen extends ConsumerWidget {
  const PreparationHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(aptitudeAnalyticsProvider);
    final historyAsync = ref.watch(aptitudeSessionHistoryProvider);
    final interviewAnalyticsAsync = ref.watch(interviewAnalyticsProvider);
    final readinessAsync = ref.watch(interviewReadinessProvider(null));

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(aptitudeAnalyticsProvider);
        ref.invalidate(aptitudeSessionHistoryProvider);
        ref.invalidate(interviewAnalyticsProvider);
        ref.invalidate(interviewReadinessProvider);
      },
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text("What are you preparing for?", style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 20),
          _PrepCard(
            icon: Icons.fact_check_rounded,
            title: "Aptitude Test",
            description: "Numerical, verbal, abstract, logical, situational judgement, and technical practice.",
            color: AppColors.blue,
            action: ElevatedButton(
              onPressed: () => context.push("/prepare/aptitude/configure", extra: const AptitudeConfigureArgs()),
              child: const Text("Start Preparing"),
            ),
          ),
          const SizedBox(height: 16),
          _PrepCard(
            icon: Icons.groups_2_outlined,
            title: "Interview Preparation",
            description: "Company, job, technical, behavioral, and STAR interview practice.",
            color: AppColors.purple,
            action: ElevatedButton(
              onPressed: () => context.push("/prepare/interview"),
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.purple),
              child: const Text("Start Preparing"),
            ),
          ),
          const SizedBox(height: 32),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Interview Progress", style: Theme.of(context).textTheme.titleLarge),
              TextButton(onPressed: () => context.push("/prepare/interview/analytics"), child: const Text("View All")),
            ],
          ),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.6,
            children: [
              interviewAnalyticsAsync.when(
                loading: () => const _StatCard(label: "Interview Sessions", value: "—"),
                error: (_, __) => const _StatCard(label: "Interview Sessions", value: "—"),
                data: (a) => _StatCard(label: "Interview Sessions", value: "${a.sessionsCompleted}"),
              ),
              interviewAnalyticsAsync.when(
                loading: () => const _StatCard(label: "Questions Practiced", value: "—"),
                error: (_, __) => const _StatCard(label: "Questions Practiced", value: "—"),
                data: (a) => _StatCard(label: "Questions Practiced", value: "${a.questionsPracticed}"),
              ),
              interviewAnalyticsAsync.when(
                loading: () => const _StatCard(label: "STAR Stories Ready", value: "—"),
                error: (_, __) => const _StatCard(label: "STAR Stories Ready", value: "—"),
                data: (a) => _StatCard(label: "STAR Stories Ready", value: "${a.starStoriesReady}"),
              ),
              readinessAsync.when(
                loading: () => const _StatCard(label: "Interview Readiness", value: "—"),
                error: (_, __) => const _StatCard(label: "Interview Readiness", value: "—"),
                data: (r) => _StatCard(label: "Interview Readiness", value: r.insufficientData || r.overall == null ? "N/A" : "${r.overall!.round()}%"),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Your Progress", style: Theme.of(context).textTheme.titleLarge),
              TextButton(
                onPressed: () => context.push("/prepare/aptitude/analytics"),
                child: const Text("View All"),
              ),
            ],
          ),
          const SizedBox(height: 8),
          analyticsAsync.when(
            loading: () => const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: LinearProgressIndicator()),
            error: (_, __) => const Text("Unable to load your progress right now.", style: TextStyle(color: AppColors.muted)),
            data: (analytics) => GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.6,
              children: [
                _StatCard(label: "Tests Completed", value: "${analytics.testsCompleted}"),
                _StatCard(label: "Average Score", value: analytics.averageScore != null ? "${analytics.averageScore!.round()}%" : "—"),
                _StatCard(label: "Questions Practiced", value: "${analytics.questionsAnswered}"),
                _StatCard(label: "Best Score", value: analytics.bestScore != null ? "${analytics.bestScore!.round()}%" : "—"),
              ],
            ),
          ),
          const SizedBox(height: 28),
          Text("Recent Tests", style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          historyAsync.when(
            loading: () => const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: LinearProgressIndicator()),
            error: (_, __) => const Text("Unable to load recent tests.", style: TextStyle(color: AppColors.muted)),
            data: (sessions) {
              if (sessions.isEmpty) {
                return const Text("No tests yet — start one above.", style: TextStyle(color: AppColors.muted));
              }
              return Column(
                children: [
                  for (final session in sessions.take(5))
                    _RecentSessionTile(
                      session: session,
                      onTap: () => session.status.isSubmitted
                          ? context.push("/prepare/aptitude/sessions/${session.id}/results")
                          : context.push("/prepare/aptitude/sessions/${session.id}"),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _PrepCard extends StatelessWidget {
  const _PrepCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
    required this.action,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color color;
  final Widget action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
                  alignment: Alignment.center,
                  child: Icon(icon, color: color),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Row(
                    children: [
                      Flexible(child: Text(title, style: Theme.of(context).textTheme.titleLarge)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(description, style: const TextStyle(color: AppColors.muted)),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: action),
          ],
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
            Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}

class _RecentSessionTile extends StatelessWidget {
  const _RecentSessionTile({required this.session, required this.onTap});

  final TestSessionSummary session;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isSubmitted = session.status.isSubmitted;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: onTap,
        leading: Icon(
          isSubmitted ? Icons.check_circle_outline : Icons.hourglass_top_rounded,
          color: isSubmitted ? AppColors.success : AppColors.warning,
        ),
        title: Text("${session.mode.label} · ${session.questionCount} questions"),
        subtitle: Text(DateFormat.yMMMd().add_jm().format(session.createdAt)),
        trailing: isSubmitted && session.percentage != null
            ? Text("${session.percentage!.round()}%", style: const TextStyle(fontWeight: FontWeight.w600))
            : const Text("In progress", style: TextStyle(color: AppColors.warning, fontSize: 12)),
      ),
    );
  }
}
