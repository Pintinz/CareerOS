import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/widgets/widgets.dart";
import "../../applications/data/application_models.dart";
import "../../applications/presentation/application_providers.dart";
import "../../applications/presentation/stage_badge.dart";
import "../../aptitude/data/aptitude_models.dart";
import "../../aptitude/presentation/aptitude_providers.dart";
import "../../aptitude/presentation/test_configuration_screen.dart";
import "../../ats/presentation/ats_providers.dart";
import "../../email_tracking/presentation/email_tracking_providers.dart";
import "../../intelligence/data/intelligence_models.dart";
import "../../intelligence/presentation/intelligence_card.dart";
import "../../intelligence/presentation/intelligence_providers.dart";
import "../../interview/data/interview_models.dart";
import "../../interview/presentation/interview_configuration_screen.dart";
import "../../interview/presentation/interview_providers.dart";
import "../../jobs/data/job_models.dart";
import "../../jobs/presentation/job_card.dart";
import "../../jobs/presentation/job_providers.dart";
import "../../profile/presentation/profile_providers.dart";
import "../../scholarships/data/scholarship_models.dart";
import "../../scholarships/presentation/scholarship_card.dart";
import "../../scholarships/presentation/scholarship_providers.dart";

/// Indexes of the bottom-navigation tabs in [HomeShell], so Home can jump to a sibling tab
/// instead of pushing a duplicate route.
abstract final class HomeTabIndex {
  static const home = 0;
  static const opportunities = 1;
  static const prepare = 2;
  static const intelligence = 3;
  static const profile = 4;
}

// Home fetches its own first page rather than reading the Opportunities/Intelligence list
// controllers, so filters a user applied on those tabs never leak into the dashboard.
final _latestJobsProvider = FutureProvider.autoDispose<List<JobCard>>((ref) async {
  return (await ref.watch(jobRepositoryProvider).list()).items;
});

final _scholarshipsProvider = FutureProvider.autoDispose<({List<ScholarshipCard> items, int total})>((ref) {
  return ref.watch(scholarshipRepositoryProvider).list();
});

final _latestIntelligenceProvider = FutureProvider.autoDispose<List<IntelligenceCard>>((ref) async {
  return (await ref.watch(intelligenceRepositoryProvider).list()).items;
});

const _interviewStages = {
  ApplicationStage.interview,
  ApplicationStage.finalInterview,
  ApplicationStage.recruiterScreen,
  ApplicationStage.assessmentCentre,
};

/// Home dashboard — "What matters to me today?". Every number and list here comes from the user's
/// real data or live content; sections without data hide themselves rather than showing chrome.
class HomeTab extends ConsumerWidget {
  const HomeTab({super.key, this.onSelectTab});

  /// Switches the enclosing [HomeShell] tab; null when Home is shown outside the shell.
  final ValueChanged<int>? onSelectTab;

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(userProfileProvider);
    ref.invalidate(activeApplicationsCountProvider);
    ref.invalidate(aptitudeAnalyticsProvider);
    ref.invalidate(interviewAnalyticsProvider);
    ref.invalidate(cvListProvider);
    ref.invalidate(recruitmentEventsProvider);
    ref.invalidate(_latestJobsProvider);
    ref.invalidate(_scholarshipsProvider);
    ref.invalidate(_latestIntelligenceProvider);
    await ref.read(applicationListProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    void selectTab(int index) => onSelectTab?.call(index);

    return RefreshIndicator(
      onRefresh: () => _refresh(ref),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.sm, AppSpacing.pageH, AppSpacing.xxl),
        children: [
          _GreetingRow(onSelectTab: selectTab),
          _CareerProgressCard(onSelectTab: selectTab),
          _StatGrid(onSelectTab: selectTab),
          const _RecruitmentActivity(),
          _NextStepCard(onSelectTab: selectTab),
          Gap.xl,
          _QuickActions(onSelectTab: selectTab),
          _LatestJobsSection(onSeeAll: () => selectTab(HomeTabIndex.opportunities)),
          const _RecentApplicationsSection(),
          _ScholarshipsSection(onSeeAll: () => selectTab(HomeTabIndex.opportunities)),
          _IntelligenceSection(onSeeAll: () => selectTab(HomeTabIndex.intelligence)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Career setup — derived entirely from the user's real account state.
// ---------------------------------------------------------------------------

enum _SetupStepKind { profile, cv, application, aptitude, interview }

class _SetupStep {
  const _SetupStep({required this.kind, required this.title, required this.subtitle, required this.icon, required this.done});

  final _SetupStepKind kind;
  final String title;
  final String subtitle;
  final IconData icon;
  final bool done;
}

void _runSetupStep(BuildContext context, _SetupStepKind kind, ValueChanged<int> selectTab) {
  switch (kind) {
    case _SetupStepKind.profile:
      selectTab(HomeTabIndex.profile);
    case _SetupStepKind.cv:
      context.push("/ats/analyze");
    case _SetupStepKind.application:
      context.push("/applications/new");
    case _SetupStepKind.aptitude:
      context.push("/prepare/aptitude/configure");
    case _SetupStepKind.interview:
      context.push("/prepare/interview");
  }
}

/// Null until every signal has loaded, so steps never flash as "not done" while loading.
final _setupStepsProvider = Provider.autoDispose<List<_SetupStep>?>((ref) {
  final profile = ref.watch(userProfileProvider).valueOrNull;
  final cvs = ref.watch(cvListProvider).valueOrNull;
  final activeCount = ref.watch(activeApplicationsCountProvider).valueOrNull;
  final applications = ref.watch(applicationListProvider);
  final aptitude = ref.watch(aptitudeAnalyticsProvider).valueOrNull;
  final interview = ref.watch(interviewAnalyticsProvider).valueOrNull;
  if (profile == null || cvs == null || activeCount == null || applications.isLoading || aptitude == null || interview == null) {
    return null;
  }
  return [
    _SetupStep(
      kind: _SetupStepKind.profile,
      title: "Complete your profile",
      subtitle: "Add your name and professional title",
      icon: AppIcons.profile,
      done: (profile.fullName?.trim().isNotEmpty ?? false) && (profile.professionalTitle?.trim().isNotEmpty ?? false),
    ),
    _SetupStep(
      kind: _SetupStepKind.cv,
      title: "Upload your CV",
      subtitle: "See how it reads against applicant tracking systems",
      icon: AppIcons.cv,
      done: cvs.isNotEmpty,
    ),
    _SetupStep(
      kind: _SetupStepKind.application,
      title: "Track an application",
      subtitle: "Keep every stage and deadline in one place",
      icon: AppIcons.application,
      done: activeCount > 0 || applications.total > 0,
    ),
    _SetupStep(
      kind: _SetupStepKind.aptitude,
      title: "Take a practice test",
      subtitle: "Numerical, verbal, logical and technical questions",
      icon: AppIcons.aptitude,
      done: aptitude.testsCompleted > 0,
    ),
    _SetupStep(
      kind: _SetupStepKind.interview,
      title: "Practise for interviews",
      subtitle: "Answer common questions and build STAR stories",
      icon: AppIcons.interview,
      done: interview.sessionsCompleted > 0,
    ),
  ];
});

void _showSetupSheet(BuildContext context, List<_SetupStep> steps, ValueChanged<int> selectTab) {
  final done = steps.where((s) => s.done).length;
  showCareerBottomSheet<void>(
    context: context,
    title: "Career setup",
    builder: (sheetContext) => SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text("$done of ${steps.length} complete", style: sheetContext.text.bodyMedium),
          Gap.sm,
          CareerProgressBar(
            value: done / steps.length,
            semanticLabel: "Career setup",
            semanticValue: "$done of ${steps.length} complete",
          ),
          Gap.md,
          for (final step in steps)
            _SetupStepRow(
              step: step,
              onTap: step.done
                  ? null
                  : () {
                      Navigator.of(sheetContext).pop();
                      _runSetupStep(context, step.kind, selectTab);
                    },
            ),
        ],
      ),
    ),
  );
}

class _SetupStepRow extends StatelessWidget {
  const _SetupStepRow({required this.step, required this.onTap});

  final _SetupStep step;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return InkWell(
      borderRadius: AppRadius.mdAll,
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
          child: Row(
            children: [
              Semantics(
                label: step.done ? "Done" : "Not done",
                child: AnimatedContainer(
                  duration: AppMotion.of(context),
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: step.done ? AppColors.success : Colors.transparent,
                    border: Border.all(color: step.done ? AppColors.success : colors.border, width: 2),
                  ),
                  child: step.done ? const Icon(AppIcons.check, size: 16, color: Colors.white) : null,
                ),
              ),
              Gap.md,
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      step.title,
                      style: context.text.titleSmall?.copyWith(
                        color: step.done ? colors.textSecondary : colors.textPrimary,
                        decoration: step.done ? TextDecoration.lineThrough : null,
                      ),
                    ),
                    if (!step.done) Text(step.subtitle, style: context.text.bodySmall),
                  ],
                ),
              ),
              if (!step.done) Icon(AppIcons.chevron, color: colors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Greeting · career progress · stats
// ---------------------------------------------------------------------------

String _greetingFor(DateTime now) {
  if (now.hour < 12) return "Good morning";
  if (now.hour < 17) return "Good afternoon";
  return "Good evening";
}

class _GreetingRow extends ConsumerWidget {
  const _GreetingRow({required this.onSelectTab});

  final ValueChanged<int> onSelectTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.colors;
    final now = DateTime.now();
    final fullName = ref.watch(userProfileProvider).valueOrNull?.fullName?.trim() ?? "";
    final nameParts = fullName.split(RegExp(r"\s+")).where((p) => p.isNotEmpty).toList();
    final firstName = nameParts.isEmpty ? null : nameParts.first;
    final initials = nameParts.take(2).map((p) => p[0].toUpperCase()).join();

    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: Text(
                  firstName == null ? "${_greetingFor(now)} 👋" : "${_greetingFor(now)}, $firstName 👋",
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.text.headlineSmall,
                ),
              ),
              const SizedBox(height: 2),
              Text("Let's move your career forward.", style: context.text.bodyMedium),
            ],
          ),
        ),
        IconButton(
          tooltip: "Settings",
          onPressed: () => context.push("/settings"),
          icon: Icon(AppIcons.settings, color: colors.textSecondary),
        ),
        Semantics(
          button: true,
          label: "Open profile",
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: () => onSelectTab(HomeTabIndex.profile),
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(colors: [AppColors.blue, AppColors.cyan]),
                border: Border.all(color: colors.surface, width: 2),
                boxShadow: AppShadows.card(context),
              ),
              alignment: Alignment.center,
              child: ExcludeSemantics(
                child: initials.isEmpty
                    ? const Icon(AppIcons.profileSelected, color: Colors.white, size: 22)
                    : Text(initials, style: context.text.titleSmall?.copyWith(color: Colors.white)),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Career setup progress from real account state. Hidden while loading and once complete — the
/// mockup's "Career Score" is not shown because CareerOS does not compute one yet.
class _CareerProgressCard extends ConsumerWidget {
  const _CareerProgressCard({required this.onSelectTab});

  final ValueChanged<int> onSelectTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final steps = ref.watch(_setupStepsProvider);
    if (steps == null) return const SizedBox.shrink();
    final done = steps.where((s) => s.done).length;
    if (done == steps.length) return const SizedBox.shrink();
    final (status, tone) = switch (done) {
      0 || 1 => ("Getting started", AppTone.primary),
      2 || 3 => ("Good progress", AppTone.success),
      _ => ("Almost there", AppTone.success),
    };

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.lg),
      child: CareerCard(
        variant: CareerCardVariant.feature,
        onTap: () => _showSetupSheet(context, steps, onSelectTab),
        semanticLabel: "Career setup, $done of ${steps.length} steps complete. Opens the checklist.",
        child: ExcludeSemantics(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Career Setup", style: context.text.titleMedium),
                    Gap.xs,
                    Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(text: "$done", style: context.text.displaySmall),
                          TextSpan(
                            text: " / ${steps.length}",
                            style: context.text.titleLarge?.copyWith(color: context.colors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    Gap.xs,
                    StatusChip(label: status, tone: tone, dense: true),
                  ],
                ),
              ),
              CareerProgressRing(
                value: done / steps.length,
                size: 92,
                strokeWidth: 10,
                semanticLabel: "Career setup",
                child: Text("${(done / steps.length * 100).round()}%", style: context.text.titleMedium),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatGrid extends ConsumerWidget {
  const _StatGrid({required this.onSelectTab});

  final ValueChanged<int> onSelectTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeCount = ref.watch(activeApplicationsCountProvider).valueOrNull;
    final applications = ref.watch(applicationListProvider);
    final interviewCount =
        applications.isLoading ? null : applications.items.where((a) => _interviewStages.contains(a.currentStage)).length;
    final aptitudeTests = ref.watch(aptitudeAnalyticsProvider).valueOrNull?.testsCompleted;
    final interviewSessions = ref.watch(interviewAnalyticsProvider).valueOrNull?.sessionsCompleted;
    final practiceSessions = aptitudeTests == null || interviewSessions == null ? null : aptitudeTests + interviewSessions;
    final scholarshipTotal = ref.watch(_scholarshipsProvider).valueOrNull?.total;

    Widget pair(Widget a, Widget b) => IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [Expanded(child: a), Gap.sm, Expanded(child: b)],
          ),
        );

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: Column(
        children: [
          pair(
            StatCard(
              label: "Active applications",
              value: activeCount?.toString(),
              icon: AppIcons.application,
              onTap: () => context.push("/applications"),
            ),
            StatCard(
              label: "At interview stage",
              value: interviewCount?.toString(),
              icon: AppIcons.interview,
              tone: AppTone.warning,
              onTap: () => context.push("/applications"),
            ),
          ),
          Gap.sm,
          pair(
            StatCard(
              label: "Practice sessions",
              value: practiceSessions?.toString(),
              icon: AppIcons.prepare,
              tone: AppTone.success,
              onTap: () => onSelectTab(HomeTabIndex.prepare),
            ),
            StatCard(
              label: "Scholarships open",
              value: scholarshipTotal?.toString(),
              icon: AppIcons.scholarship,
              tone: AppTone.purple,
              onTap: () => onSelectTab(HomeTabIndex.opportunities),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Recruitment activity (only when something needs attention)
// ---------------------------------------------------------------------------

class _RecruitmentActivity extends ConsumerWidget {
  const _RecruitmentActivity();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cards = <Widget>[
      const _ApplicationUpdatesCard(),
      const _UpcomingAptitudeStageCard(),
      const _UpcomingInterviewStageCard(),
    ];
    return Column(children: [for (final card in cards) card]);
  }
}

class _Spaced extends StatelessWidget {
  const _Spaced({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: AppSpacing.sm), child: child);
}

/// "Application Updates" (spec §31) — a count of recruitment-email suggestions awaiting review,
/// plus (only when a real application is already matched) the company name and possible stage.
/// Never shows the email's raw subject/body — that lives behind Review on
/// [RecruitmentEventDetailScreen], which is the only place a stage can actually be confirmed.
class _ApplicationUpdatesCard extends ConsumerWidget {
  const _ApplicationUpdatesCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(recruitmentEventsProvider);
    return eventsAsync.maybeWhen(
      data: (events) {
        final needsReview = events.where((e) => e.needsReview).toList();
        if (needsReview.isEmpty) return const SizedBox.shrink();
        final top = needsReview.first;
        return _Spaced(
          child: InsightCard(
            icon: AppIcons.email,
            tone: AppTone.primary,
            title: needsReview.length == 1 ? "1 Recruitment Update" : "${needsReview.length} Recruitment Updates",
            message: top.matchedApplicationId == null ? "Review to see details" : null,
            messageWidget: top.matchedApplicationId != null
                ? _ApplicationUpdateSubtitle(applicationId: top.matchedApplicationId!, stage: top.detectedStage)
                : null,
            actionLabel: "Review",
            onAction: () => context.push("/settings/tracking/events"),
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

class _ApplicationUpdateSubtitle extends ConsumerWidget {
  const _ApplicationUpdateSubtitle({required this.applicationId, required this.stage});

  final String applicationId;
  final ApplicationStage? stage;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applicationAsync = ref.watch(applicationDetailProvider(applicationId));
    return applicationAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (application) => Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(
          stage != null ? "${application.companyName} · Possible ${stage!.label}" : application.companyName,
          style: context.text.bodySmall,
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
    final application = upcoming;

    return _Spaced(
      child: InsightCard(
        icon: AppIcons.aptitude,
        tone: AppTone.purple,
        title: "Upcoming Recruitment Stage",
        message: "Aptitude Test · ${application.roleTitle} at ${application.companyName}",
        actionLabel: "Prepare Now",
        onAction: () => context.push(
          "/prepare/aptitude/configure",
          extra: AptitudeConfigureArgs(initialMode: TestMode.jobSpecific, applicationId: application.id),
        ),
      ),
    );
  }
}

/// Shown only when a tracked application is at an interview-related stage (spec §30) — a real
/// readiness percentage from that application's own prep activity, never an inferred date.
class _UpcomingInterviewStageCard extends ConsumerWidget {
  const _UpcomingInterviewStageCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applications = ref.watch(applicationListProvider).items;
    Application? upcoming;
    for (final application in applications) {
      if (_interviewStages.contains(application.currentStage)) {
        upcoming = application;
        break;
      }
    }
    if (upcoming == null) return const SizedBox.shrink();
    final application = upcoming;

    final readinessAsync = ref.watch(interviewReadinessProvider(application.id));

    return _Spaced(
      child: InsightCard(
        icon: AppIcons.interview,
        tone: AppTone.warning,
        title: "Upcoming Interview Preparation",
        message: "${application.roleTitle} at ${application.companyName}",
        messageWidget: readinessAsync.maybeWhen(
          data: (r) => r.insufficientData || r.overall == null
              ? null
              : Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    "Preparation readiness: ${r.overall!.round()}%",
                    style: context.text.labelMedium?.copyWith(color: AppTone.warning.onTint(context)),
                  ),
                ),
          orElse: () => null,
        ),
        actionLabel: "Prepare Now",
        onAction: () => context.push(
          "/prepare/interview/configure",
          extra: InterviewConfigureArgs(initialMode: InterviewSessionMode.practice, applicationId: application.id),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Recommended next action
// ---------------------------------------------------------------------------

class _NextStepCard extends ConsumerWidget {
  const _NextStepCard({required this.onSelectTab});

  final ValueChanged<int> onSelectTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final steps = ref.watch(_setupStepsProvider);
    if (steps == null) return const SizedBox.shrink();
    final next = steps.where((s) => !s.done).firstOrNull;
    if (next == null) return const SizedBox.shrink();
    return _Spaced(
      child: InsightCard(
        icon: next.icon,
        tone: AppTone.success,
        title: "Next step: ${next.title}",
        message: next.subtitle,
        actionLabel: "Start",
        onAction: () => _runSetupStep(context, next.kind, onSelectTab),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quick actions (max four)
// ---------------------------------------------------------------------------

class _QuickActions extends StatelessWidget {
  const _QuickActions({required this.onSelectTab});

  final ValueChanged<int> onSelectTab;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _QuickAction(
          icon: AppIcons.opportunities,
          label: "Find\nOpportunities",
          tone: AppTone.primary,
          onTap: () => onSelectTab(HomeTabIndex.opportunities),
        ),
        _QuickAction(icon: AppIcons.cv, label: "Analyze\nCV", tone: AppTone.purple, onTap: () => context.push("/ats/analyze")),
        _QuickAction(
          icon: AppIcons.prepare,
          label: "Prepare",
          tone: AppTone.success,
          onTap: () => onSelectTab(HomeTabIndex.prepare),
        ),
        _QuickAction(
          icon: AppIcons.application,
          label: "Track\nApplication",
          tone: AppTone.warning,
          onTap: () => context.push("/applications/new"),
        ),
      ],
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({required this.icon, required this.label, required this.tone, required this.onTap});

  final IconData icon;
  final String label;
  final AppTone tone;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Expanded(
      child: Semantics(
        button: true,
        label: label.replaceAll("\n", " "),
        child: InkWell(
          borderRadius: AppRadius.cardAll,
          onTap: onTap,
          child: ExcludeSemantics(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
              child: Column(
                children: [
                  Container(
                    width: 60,
                    height: 60,
                    decoration: BoxDecoration(
                      color: colors.surface,
                      borderRadius: AppRadius.featureAll,
                      border: Border.all(color: colors.border),
                      boxShadow: AppShadows.card(context),
                    ),
                    alignment: Alignment.center,
                    child: IconTile(icon: icon, tone: tone, size: 40),
                  ),
                  Gap.xs,
                  Text(
                    label,
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    style: context.text.labelMedium?.copyWith(color: colors.textPrimary, height: 1.25),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Live content sections
// ---------------------------------------------------------------------------

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child, this.onSeeAll});

  final String title;
  final Widget child;
  final VoidCallback? onSeeAll;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.section),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionHeader(title: title, actionLabel: onSeeAll == null ? null : "See all", onAction: onSeeAll),
          child,
        ],
      ),
    );
  }
}

class _LatestJobsSection extends ConsumerWidget {
  const _LatestJobsSection({required this.onSeeAll});

  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_latestJobsProvider);
    if (async.isLoading && !async.hasValue) {
      return const _Section(title: "Latest opportunities", child: Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]));
    }
    final jobs = async.valueOrNull ?? const <JobCard>[];
    if (jobs.isEmpty) return const SizedBox.shrink();

    return _Section(
      title: "Latest opportunities",
      onSeeAll: onSeeAll,
      child: Column(
        children: [
          for (final (i, job) in jobs.take(3).indexed) ...[
            if (i > 0) Gap.sm,
            JobCardTile(job: job, onTap: () => context.push("/jobs/${job.slug}")),
          ],
        ],
      ),
    );
  }
}

class _RecentApplicationsSection extends ConsumerWidget {
  const _RecentApplicationsSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applications = ref.watch(applicationListProvider).items;
    if (applications.isEmpty) return const SizedBox.shrink();
    final recent = applications.take(3).toList();
    final colors = context.colors;

    return _Section(
      title: "Recent applications",
      onSeeAll: () => context.push("/applications"),
      child: Material(
        color: colors.surface,
        shape: RoundedRectangleBorder(borderRadius: AppRadius.cardAll, side: BorderSide(color: colors.border)),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            for (var i = 0; i < recent.length; i++) ...[
              if (i > 0) Divider(height: 1, indent: 72, color: colors.border),
              InkWell(
                onTap: () => context.push("/applications/${recent[i].id}"),
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Row(
                    children: [
                      NetworkImageWithFallback(url: null, fallbackText: recent[i].companyName, size: 40),
                      Gap.md,
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(recent[i].roleTitle, style: context.text.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                            Text(recent[i].companyName, style: context.text.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                          ],
                        ),
                      ),
                      Gap.xs,
                      StageBadge(stage: recent[i].currentStage, dense: true),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ScholarshipsSection extends ConsumerWidget {
  const _ScholarshipsSection({required this.onSeeAll});

  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final all = ref.watch(_scholarshipsProvider).valueOrNull?.items ?? const <ScholarshipCard>[];
    // Soonest real upcoming deadline first; scholarships without a deadline follow; closed ones hide.
    final open = all.where((s) => s.applicationDeadline == null || DateLabels.daysUntil(s.applicationDeadline!) >= 0).toList()
      ..sort((a, b) {
        final da = a.applicationDeadline, db = b.applicationDeadline;
        if (da == null && db == null) return 0;
        if (da == null) return 1;
        if (db == null) return -1;
        return da.compareTo(db);
      });
    if (open.isEmpty) return const SizedBox.shrink();

    return _Section(
      title: "Scholarships closing soon",
      onSeeAll: onSeeAll,
      child: Column(
        children: [
          for (var i = 0; i < open.length && i < 2; i++) ...[
            if (i > 0) Gap.sm,
            ScholarshipCardTile(
              scholarship: open[i],
              onTap: () => context.push("/scholarships/${open[i].slug}"),
            ),
          ],
        ],
      ),
    );
  }
}

class _IntelligenceSection extends ConsumerWidget {
  const _IntelligenceSection({required this.onSeeAll});

  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posts = ref.watch(_latestIntelligenceProvider).valueOrNull ?? const <IntelligenceCard>[];
    if (posts.isEmpty) return const SizedBox.shrink();

    return _Section(
      title: "Company intelligence",
      onSeeAll: onSeeAll,
      child: Column(
        children: [
          for (final (i, post) in posts.take(3).indexed) ...[
            if (i > 0) Gap.sm,
            IntelligenceCardTile(post: post, showSummary: false),
          ],
        ],
      ),
    );
  }
}
