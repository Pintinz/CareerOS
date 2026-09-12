import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../theme/app_colors.dart";
import "../../applications/data/application_models.dart";
import "../../applications/presentation/application_providers.dart";
import "../../aptitude/data/aptitude_models.dart";
import "../../aptitude/presentation/aptitude_providers.dart";
import "../../aptitude/presentation/test_configuration_screen.dart";
import "../../profile/presentation/profile_providers.dart";

/// Home dashboard (master spec §11). Only the greeting header is wired to real data in this
/// phase — Career Readiness Score, match cards, and the daily career brief depend on the
/// jobs/scholarships/ATS/application data models built in Phases 2-5 and are not faked here.
class HomeTab extends ConsumerWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(userProfileProvider);

    return RefreshIndicator(
      onRefresh: () => ref.refresh(userProfileProvider.future),
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          profileAsync.when(
            loading: () => const _GreetingSkeleton(),
            error: (error, _) => Text(
              "Good day.",
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            data: (profile) {
              final firstName = (profile.fullName ?? "").split(" ").firstOrNull;
              return Text(
                firstName == null || firstName.isEmpty ? "Good day." : "Good day, $firstName",
                style: Theme.of(context).textTheme.headlineMedium,
              );
            },
          ),
          const SizedBox(height: 4),
          Text(
            "Let's make progress today.",
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 32),
          _ActiveApplicationsCard(activeCountAsync: ref.watch(activeApplicationsCountProvider)),
          const SizedBox(height: 16),
          const _UpcomingAptitudeStageCard(),
          const _PreparationProgressCard(),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Career Readiness Score", style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  Text(
                    "Available once your profile, CV and preferences are complete "
                    "(Phases 1-3).",
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ActiveApplicationsCard extends StatelessWidget {
  const _ActiveApplicationsCard({required this.activeCountAsync});

  final AsyncValue<int> activeCountAsync;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push("/applications"),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
                alignment: Alignment.center,
                child: const Icon(Icons.timeline_outlined, color: AppColors.blue),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    activeCountAsync.when(
                      loading: () => const Text("—", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                      error: (_, __) => const Text("—", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                      data: (count) => Text("$count", style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    ),
                    const Text("Active Applications", style: TextStyle(color: AppColors.muted)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.muted),
            ],
          ),
        ),
      ),
    );
  }
}

/// Shown only when a tracked application's current stage is Aptitude Test (spec §29) — a real
/// link into prep, preselected with that application's context, not a generic reminder.
class _UpcomingAptitudeStageCard extends ConsumerWidget {
  const _UpcomingAptitudeStageCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applications = ref.watch(applicationListProvider).items;
    Application? upcoming;
    for (final application in applications) {
      if (application.currentStage == ApplicationStage.aptitudeTest) {
        upcoming = application;
        break;
      }
    }
    if (upcoming == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Card(
        color: AppColors.blue.withValues(alpha: 0.06),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(Icons.fact_check_outlined, color: AppColors.blue),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Upcoming Recruitment Stage", style: TextStyle(fontWeight: FontWeight.w600)),
                    Text(
                      "Aptitude Test · ${upcoming.roleTitle} at ${upcoming.companyName}",
                      style: const TextStyle(color: AppColors.muted, fontSize: 12),
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed: () => context.push(
                  "/prepare/aptitude/configure",
                  extra: AptitudeConfigureArgs(initialMode: TestMode.jobSpecific, applicationId: upcoming!.id),
                ),
                child: const Text("Prepare Now"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Real preparation stats from actual submitted sessions (spec §29) — no placeholder numbers.
class _PreparationProgressCard extends ConsumerWidget {
  const _PreparationProgressCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(aptitudeAnalyticsProvider);
    return analyticsAsync.maybeWhen(
      data: (analytics) {
        if (analytics.testsCompleted == 0) return const SizedBox.shrink();
        final weakest = analytics.byCategory.entries.isEmpty
            ? null
            : (analytics.byCategory.entries.toList()..sort((a, b) => a.value.percentage.compareTo(b.value.percentage)))
                .first;
        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: Card(
            child: InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => context.push("/prepare/aptitude/analytics"),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("Preparation Progress", style: Theme.of(context).textTheme.titleLarge),
                        const Icon(Icons.chevron_right, color: AppColors.muted),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _MiniStat(label: "Tests Completed", value: "${analytics.testsCompleted}"),
                        _MiniStat(
                          label: "Average Score",
                          value: analytics.averageScore != null ? "${analytics.averageScore!.round()}%" : "—",
                        ),
                        if (weakest != null) _MiniStat(label: "Weakest Area", value: weakest.key),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 11)),
        ],
      ),
    );
  }
}

class _GreetingSkeleton extends StatelessWidget {
  const _GreetingSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 180,
      height: 28,
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}

extension _FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
