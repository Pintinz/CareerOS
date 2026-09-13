import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "../data/interview_models.dart";
import "interview_configuration_screen.dart";
import "interview_providers.dart";

const _kMainCategories = [
  ("company_specific", "Company Specific", Icons.apartment_outlined, AppTone.primary),
  ("job_specific", "Job Specific", Icons.work_outline, AppTone.info),
  ("technical", "Technical", Icons.build_outlined, AppTone.purple),
  ("behavioral", "Behavioral", Icons.psychology_outlined, AppTone.success),
  ("hr_general", "HR / General", Icons.badge_outlined, AppTone.neutral),
  ("safety", "Safety", Icons.health_and_safety_outlined, AppTone.warning),
  ("leadership", "Leadership", Icons.emoji_events_outlined, AppTone.warning),
  ("management", "Management", Icons.groups_outlined, AppTone.primary),
];

/// Interview Preparation home: preparation readiness from real activity, quick starts, and
/// practice by category.
class InterviewHomeScreen extends ConsumerWidget {
  const InterviewHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text("Interview Preparation")),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          const _ReadinessCard(),
          Gap.section,
          const SectionHeader(title: "Quick Start"),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: _QuickAction(
                    icon: AppIcons.interview,
                    tone: AppTone.warning,
                    label: "Mock Interview",
                    caption: "Timed, mixed questions",
                    onTap: () => context.push(
                      "/prepare/interview/configure",
                      extra: const InterviewConfigureArgs(initialMode: InterviewSessionMode.mock),
                    ),
                  ),
                ),
                Gap.sm,
                Expanded(
                  child: _QuickAction(
                    icon: Icons.edit_note_outlined,
                    tone: AppTone.primary,
                    label: "Question Practice",
                    caption: "At your own pace",
                    onTap: () => context.push("/prepare/interview/configure", extra: const InterviewConfigureArgs()),
                  ),
                ),
              ],
            ),
          ),
          Gap.sm,
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: _QuickAction(
                    icon: AppIcons.starStory,
                    tone: AppTone.success,
                    label: "STAR Story Builder",
                    caption: "Situation · Task · Action · Result",
                    onTap: () => context.push("/prepare/interview/star-stories"),
                  ),
                ),
                Gap.sm,
                Expanded(
                  child: _QuickAction(
                    icon: AppIcons.analytics,
                    tone: AppTone.purple,
                    label: "Readiness & Analytics",
                    caption: "Where to focus next",
                    onTap: () => context.push("/prepare/interview/analytics"),
                  ),
                ),
              ],
            ),
          ),
          Gap.section,
          const SectionHeader(title: "Practice by Category"),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth > 520 ? 3 : 2;
              final width = (constraints.maxWidth - AppSpacing.sm * (columns - 1)) / columns;
              return Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  for (final (slug, label, icon, tone) in _kMainCategories)
                    SizedBox(
                      width: width,
                      child: CareerCard(
                        padding: const EdgeInsets.all(AppSpacing.sm),
                        onTap: () => context.push(
                          "/prepare/interview/configure",
                          extra: InterviewConfigureArgs(initialCategorySlug: slug),
                        ),
                        child: Row(
                          children: [
                            IconTile(icon: icon, tone: tone, size: 36),
                            Gap.xs,
                            Expanded(child: Text(label, style: context.text.titleSmall, maxLines: 2)),
                          ],
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
          Gap.sm,
          Text(
            "Situational and Career Motivation practice are available from the full category list in Configure.",
            style: context.text.bodySmall,
          ),
        ],
      ),
    );
  }
}

/// "Interview Preparation Readiness" — calculated from real practice, STAR and research activity.
/// Never phrased as a chance of passing.
class _ReadinessCard extends ConsumerWidget {
  const _ReadinessCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final readiness = ref.watch(interviewReadinessProvider(null)).valueOrNull;
    if (readiness == null) return const LoadingSkeleton(height: 132, radius: AppRadius.feature);

    if (readiness.insufficientData || readiness.overall == null) {
      return CareerCard(
        variant: CareerCardVariant.feature,
        child: Row(
          children: [
            const IconTile(icon: Icons.speed_rounded, tone: AppTone.warning, size: 52),
            Gap.md,
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Interview Preparation Readiness", style: context.text.titleMedium),
                  const SizedBox(height: 2),
                  Text("Practice a few questions and build a STAR story to see your readiness.", style: context.text.bodySmall),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final c = readiness.components;
    final rows = <(String, double?)>[
      ("Question practice", c.questionPractice),
      ("Technical preparation", c.technicalPrep),
      ("STAR stories", c.starCoverage),
      ("Company knowledge", c.companyPrep),
      ("Role understanding", c.jobSpecificPrep),
    ].where((r) => r.$2 != null).toList();

    return CareerCard(
      variant: CareerCardVariant.feature,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Interview Preparation Readiness", style: context.text.titleMedium),
                    const SizedBox(height: 2),
                    Text("From your practice, STAR stories and research", style: context.text.bodySmall),
                  ],
                ),
              ),
              CareerProgressRing(
                value: readiness.overall! / 100,
                size: 72,
                strokeWidth: 8,
                tone: AppTone.warning,
                semanticLabel: "Interview preparation readiness",
                child: Text("${readiness.overall!.round()}%", style: context.text.titleSmall),
              ),
            ],
          ),
          if (rows.isNotEmpty) ...[
            Gap.md,
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                child: Row(
                  children: [
                    SizedBox(width: 140, child: Text(row.$1, style: context.text.bodySmall)),
                    Expanded(
                      child: CareerProgressBar(value: row.$2! / 100, height: 6, tone: AppTone.warning, semanticLabel: row.$1),
                    ),
                    SizedBox(
                      width: 44,
                      child: Text("${row.$2!.round()}%", textAlign: TextAlign.end, style: context.text.labelMedium),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({required this.icon, required this.tone, required this.label, required this.caption, required this.onTap});

  final IconData icon;
  final AppTone tone;
  final String label;
  final String caption;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconTile(icon: icon, tone: tone, size: 40),
          Gap.sm,
          Text(label, style: context.text.titleSmall),
          const SizedBox(height: 2),
          Text(caption, style: context.text.bodySmall),
        ],
      ),
    );
  }
}
