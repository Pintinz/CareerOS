import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../../interview/presentation/interview_providers.dart";
import "../data/aptitude_models.dart";
import "aptitude_providers.dart";
import "test_configuration_screen.dart";

/// Prepare hub — "How do I become more competitive?". Aptitude testing, interview preparation and
/// CV tools as the three primary areas; resume, progress and history below. Every figure is real.
class PreparationHubScreen extends ConsumerWidget {
  const PreparationHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(aptitudeSessionHistoryProvider);
    final inProgress = historyAsync.valueOrNull?.where((s) => !s.status.isSubmitted).firstOrNull;

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(aptitudeAnalyticsProvider);
        ref.invalidate(aptitudeSessionHistoryProvider);
        ref.invalidate(interviewAnalyticsProvider);
        ref.invalidate(interviewReadinessProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, AppSpacing.xxl),
        children: [
          const HubHeader(title: "Prepare", subtitle: "Become more competitive for every application"),
          Gap.lg,
          const _PrepareHero(),
          if (inProgress != null) ...[
            Gap.md,
            InsightCard(
              icon: Icons.play_circle_outline_rounded,
              tone: AppTone.warning,
              title: "Resume your practice test",
              message: "${inProgress.mode.label} · ${inProgress.questionCount} questions · started ${DateLabels.published(inProgress.createdAt).toLowerCase()}",
              actionLabel: "Resume",
              onAction: () => context.push("/prepare/aptitude/sessions/${inProgress.id}"),
            ),
          ],
          Gap.section,
          const SectionHeader(title: "What are you preparing for?"),
          _AreaCard(
            icon: AppIcons.aptitude,
            tone: AppTone.primary,
            title: "Aptitude Test",
            description: "Numerical, verbal, abstract, logical, situational judgement, and technical practice.",
            actionLabel: "Start Preparing",
            onTap: () => context.push("/prepare/aptitude/configure", extra: const AptitudeConfigureArgs()),
          ),
          Gap.sm,
          _AreaCard(
            icon: AppIcons.interview,
            tone: AppTone.warning,
            title: "Interview Preparation",
            description: "Company, job, technical, behavioral, and STAR interview practice.",
            actionLabel: "Start Preparing",
            onTap: () => context.push("/prepare/interview"),
          ),
          Gap.sm,
          _AreaCard(
            icon: AppIcons.cv,
            tone: AppTone.purple,
            title: "CV & Career Tools",
            description: "Check how your CV reads to applicant tracking systems and how well it matches a role.",
            actionLabel: "Analyze CV",
            onTap: () => context.push("/ats/analyze"),
          ),
          const _AptitudeProgress(),
          const _InterviewProgress(),
          _RecentTests(historyAsync: historyAsync),
          Gap.section,
          CareerListGroup(
            title: "More preparation",
            children: [
              CareerListRow(
                icon: AppIcons.starStory,
                tone: AppTone.success,
                title: "STAR Stories",
                subtitle: "Build answers that show real impact",
                onTap: () => context.push("/prepare/interview/star-stories"),
              ),
              CareerListRow(
                icon: AppIcons.analytics,
                title: "Aptitude Analytics",
                subtitle: "Section and topic performance",
                onTap: () => context.push("/prepare/aptitude/analytics"),
              ),
              CareerListRow(
                icon: AppIcons.history,
                tone: AppTone.warning,
                title: "Interview Analytics",
                subtitle: "Practice history and readiness by area",
                onTap: () => context.push("/prepare/interview/analytics"),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PrepareHero extends StatelessWidget {
  const _PrepareHero();

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        borderRadius: AppRadius.heroAll,
        gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colors.heroGradient),
        border: colors.isDark ? Border.all(color: colors.border) : null,
        boxShadow: AppShadows.hero(context),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Prepare with confidence", style: context.text.titleLarge?.copyWith(color: Colors.white)),
                Gap.xs,
                Text(
                  "Practice tests, rehearse interviews and sharpen your CV — with progress tracked from real sessions.",
                  style: context.text.bodyMedium?.copyWith(color: Colors.white.withValues(alpha: 0.8)),
                ),
              ],
            ),
          ),
          Gap.md,
          ExcludeSemantics(
            child: Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.12), borderRadius: AppRadius.featureAll),
              alignment: Alignment.center,
              child: const Icon(AppIcons.prepareSelected, color: Colors.white, size: 34),
            ),
          ),
        ],
      ),
    );
  }
}

/// A whole-card entry point into one preparation area. The action reads as a link rather than a
/// filled button, so three areas don't compete as three primary CTAs on one screen.
class _AreaCard extends StatelessWidget {
  const _AreaCard({
    required this.icon,
    required this.tone,
    required this.title,
    required this.description,
    required this.actionLabel,
    required this.onTap,
  });

  final IconData icon;
  final AppTone tone;
  final String title;
  final String description;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return CareerCard(
      variant: CareerCardVariant.feature,
      onTap: onTap,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconTile(icon: icon, tone: tone, size: 52),
          Gap.md,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(header: true, child: Text(title, style: context.text.titleLarge)),
                const SizedBox(height: 2),
                Text(description, style: context.text.bodyMedium),
                Gap.sm,
                Semantics(
                  button: true,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(child: Text(actionLabel, style: context.text.labelLarge?.copyWith(color: colors.primary))),
                      Gap.xxs,
                      Icon(Icons.arrow_forward_rounded, size: 18, color: colors.primary),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

Widget _statPair(Widget a, Widget b) => IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Expanded(child: a), Gap.sm, Expanded(child: b)]),
    );

class _AptitudeProgress extends ConsumerWidget {
  const _AptitudeProgress();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(aptitudeAnalyticsProvider);
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.section),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionHeader(
            title: "Aptitude Progress",
            subtitle: "From your completed practice tests",
            actionLabel: "View all",
            onAction: () => context.push("/prepare/aptitude/analytics"),
          ),
          analyticsAsync.when(
            loading: () => const Column(children: [LoadingSkeleton(height: 88, radius: AppRadius.card), Gap.sm, LoadingSkeleton(height: 88, radius: AppRadius.card)]),
            error: (_, __) => const ErrorState(compact: true, message: "We couldn't load your aptitude progress right now."),
            data: (analytics) => Column(
              children: [
                _statPair(
                  StatCard(label: "Tests Completed", value: "${analytics.testsCompleted}", icon: Icons.task_alt_rounded),
                  StatCard(
                    label: "Average Score",
                    value: analytics.averageScore != null ? "${analytics.averageScore!.round()}%" : "—",
                    caption: analytics.averageScore == null ? "No scored tests yet" : null,
                    progress: analytics.averageScore == null ? null : analytics.averageScore! / 100,
                    icon: Icons.insights_rounded,
                    tone: AppTone.success,
                  ),
                ),
                Gap.sm,
                _statPair(
                  StatCard(
                    label: "Questions Practiced",
                    value: "${analytics.questionsAnswered}",
                    caption: "Across every section",
                    icon: AppIcons.aptitude,
                    tone: AppTone.purple,
                  ),
                  StatCard(
                    label: "Best Score",
                    value: analytics.bestScore != null ? "${analytics.bestScore!.round()}%" : "—",
                    caption: analytics.bestScore == null ? "No scored tests yet" : null,
                    progress: analytics.bestScore == null ? null : analytics.bestScore! / 100,
                    icon: Icons.emoji_events_outlined,
                    tone: AppTone.warning,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InterviewProgress extends ConsumerWidget {
  const _InterviewProgress();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(interviewAnalyticsProvider);
    final readiness = ref.watch(interviewReadinessProvider(null));
    final a = analytics.valueOrNull;
    final r = readiness.valueOrNull;
    final hasReadiness = r != null && !r.insufficientData && r.overall != null;
    final readinessLabel = r == null ? null : (hasReadiness ? "${r.overall!.round()}%" : "—");

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.section),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionHeader(
            title: "Interview Progress",
            subtitle: "From practice sessions and STAR stories",
            actionLabel: "View all",
            onAction: () => context.push("/prepare/interview/analytics"),
          ),
          _statPair(
            StatCard(label: "Practice Sessions", value: a?.sessionsCompleted.toString(), icon: AppIcons.interview, tone: AppTone.warning),
            StatCard(
              label: "Interview Readiness",
              value: readinessLabel,
              caption: r != null && !hasReadiness ? "Not enough data yet" : null,
              progress: hasReadiness ? r.overall! / 100 : null,
              icon: Icons.speed_rounded,
              tone: AppTone.success,
            ),
          ),
          Gap.sm,
          _statPair(
            StatCard(label: "Questions Practiced", value: a?.questionsPracticed.toString(), caption: "In interview practice", icon: Icons.forum_outlined),
            StatCard(
              label: "STAR Stories Ready",
              value: a?.starStoriesReady.toString(),
              caption: a == null ? null : "of ${a.starStoriesCreated} written",
              icon: AppIcons.starStory,
              tone: AppTone.purple,
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentTests extends StatelessWidget {
  const _RecentTests({required this.historyAsync});

  final AsyncValue<List<TestSessionSummary>> historyAsync;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.section),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SectionHeader(title: "Recent Tests"),
          historyAsync.when(
            loading: () => const SkeletonCard(),
            error: (_, __) => const ErrorState(compact: true, message: "We couldn't load your recent tests."),
            data: (sessions) {
              if (sessions.isEmpty) {
                return CareerCard(
                  variant: CareerCardVariant.muted,
                  child: Row(
                    children: [
                      const IconTile(icon: AppIcons.history, size: 40),
                      Gap.sm,
                      Expanded(child: Text("No practice tests yet. Your completed tests will appear here.", style: context.text.bodyMedium)),
                    ],
                  ),
                );
              }
              return CareerListGroup(
                children: [
                  for (final session in sessions.take(5))
                    CareerListRow(
                      icon: session.status.isSubmitted ? Icons.check_circle_outline_rounded : Icons.hourglass_top_rounded,
                      tone: session.status.isSubmitted ? AppTone.success : AppTone.warning,
                      title: "${session.mode.label} · ${session.questionCount} questions",
                      subtitle: DateLabels.published(session.createdAt),
                      trailing: session.status.isSubmitted && session.percentage != null
                          ? StatusChip(label: "${session.percentage!.round()}%", tone: AppTone.primary)
                          : const StatusChip(label: "In progress", tone: AppTone.warning),
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
