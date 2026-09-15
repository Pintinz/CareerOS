import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../../applications/presentation/application_providers.dart";
import "../../ats/presentation/ats_providers.dart";
import "../../auth/presentation/auth_controller.dart";
import "../../interview/presentation/interview_providers.dart";
import "../data/profile_repository.dart";
import "edit_profile_sheet.dart";
import "profile_providers.dart";

/// Profile hub — the user's career passport. Shows only fields and counts that really exist.
class ProfileTab extends ConsumerWidget {
  const ProfileTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(userProfileProvider);
    final email = ref.watch(currentUserProvider).valueOrNull?.email;

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(userProfileProvider);
        ref.invalidate(currentUserProvider);
        ref.invalidate(activeApplicationsCountProvider);
        ref.invalidate(cvListProvider);
        ref.invalidate(interviewAnalyticsProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, AppSpacing.xxl),
        children: [
          profileAsync.when(
            loading: () => const LoadingSkeleton(height: 200, radius: AppRadius.hero),
            error: (e, _) => ErrorState(
              compact: true,
              title: "We couldn't load your profile",
              message: e.userMessage,
              onRetry: () => ref.invalidate(userProfileProvider),
            ),
            data: (profile) => _PassportHero(profile: profile, email: email),
          ),
          Gap.md,
          const _PassportStats(),
          if (profileAsync.valueOrNull != null) ...[
            Gap.section,
            _ProfessionalDetails(profile: profileAsync.value!),
          ],
          Gap.section,
          CareerListGroup(
            title: "Career toolkit",
            children: [
              CareerListRow(
                icon: AppIcons.application,
                title: "My Applications",
                subtitle: "Track every stage",
                onTap: () => context.push("/applications"),
              ),
              CareerListRow(
                icon: AppIcons.saved,
                tone: AppTone.info,
                title: "Saved Opportunities",
                subtitle: "Jobs and scholarships you bookmarked",
                onTap: () => context.push("/saved"),
              ),
              CareerListRow(
                icon: AppIcons.cv,
                tone: AppTone.purple,
                title: "CV & Career Tools",
                subtitle: "Analyze your CV against a role",
                onTap: () => context.push("/ats/analyze"),
              ),
              CareerListRow(
                icon: AppIcons.aptitude,
                tone: AppTone.success,
                title: "Aptitude Performance",
                onTap: () => context.push("/prepare/aptitude/analytics"),
              ),
              CareerListRow(
                icon: AppIcons.interview,
                tone: AppTone.warning,
                title: "Interview Readiness",
                onTap: () => context.push("/prepare/interview/analytics"),
              ),
              CareerListRow(
                icon: AppIcons.starStory,
                tone: AppTone.success,
                title: "STAR Stories",
                onTap: () => context.push("/prepare/interview/star-stories"),
              ),
            ],
          ),
          Gap.lg,
          CareerListGroup(
            children: [
              CareerListRow(icon: AppIcons.settings, tone: AppTone.neutral, title: "Settings", onTap: () => context.push("/settings")),
            ],
          ),
          Gap.lg,
          AppOutlineButton(
            label: "Log Out",
            icon: AppIcons.logout,
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}

class _PassportHero extends StatelessWidget {
  const _PassportHero({required this.profile, required this.email});

  final UserProfile profile;
  final String? email;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final name = profile.fullName?.trim() ?? "";
    final initials = name.split(RegExp(r"\s+")).where((p) => p.isNotEmpty).take(2).map((p) => p[0].toUpperCase()).join();
    final subtitle = [
      if (profile.professionalTitle?.isNotEmpty ?? false) profile.professionalTitle!,
      if (profile.location?.isNotEmpty ?? false) profile.location!,
    ];

    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        borderRadius: AppRadius.heroAll,
        gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colors.heroGradient),
        border: colors.isDark ? Border.all(color: colors.border) : null,
        boxShadow: AppShadows.hero(context),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 72,
                height: 72,
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white.withValues(alpha: 0.2)),
                child: ClipOval(
                  child: profile.profilePictureUrl != null
                      ? NetworkImageWithFallback(url: profile.profilePictureUrl, fallbackText: name, size: 66, radius: 33)
                      : Container(
                          color: Colors.white.withValues(alpha: 0.14),
                          alignment: Alignment.center,
                          child: initials.isEmpty
                              ? const Icon(AppIcons.profileSelected, color: Colors.white, size: 34)
                              : Text(initials, style: context.text.headlineSmall?.copyWith(color: Colors.white)),
                        ),
                ),
              ),
              const Spacer(),
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: Colors.white, backgroundColor: Colors.white.withValues(alpha: 0.12)),
                onPressed: () => showEditProfileSheet(context, profile),
                icon: const Icon(Icons.edit_outlined, size: 18),
                label: const Text("Edit"),
              ),
            ],
          ),
          Gap.md,
          Semantics(
            header: true,
            child: Text(
              name.isEmpty ? "Add your name" : name,
              style: context.text.headlineSmall?.copyWith(color: Colors.white),
            ),
          ),
          if (subtitle.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(subtitle.join(" · "), style: context.text.bodyMedium?.copyWith(color: Colors.white.withValues(alpha: 0.82))),
          ] else ...[
            const SizedBox(height: 2),
            Text("Add your professional title and location", style: context.text.bodyMedium?.copyWith(color: Colors.white.withValues(alpha: 0.7))),
          ],
          if (email != null) ...[
            Gap.xs,
            Row(
              children: [
                Icon(Icons.alternate_email_rounded, size: 14, color: Colors.white.withValues(alpha: 0.7)),
                const SizedBox(width: 4),
                Flexible(child: Text(email!, style: context.text.bodySmall?.copyWith(color: Colors.white.withValues(alpha: 0.7)))),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _PassportStats extends ConsumerWidget {
  const _PassportStats();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final active = ref.watch(activeApplicationsCountProvider).valueOrNull;
    final cvs = ref.watch(cvListProvider).valueOrNull?.length;
    final star = ref.watch(interviewAnalyticsProvider).valueOrNull?.starStoriesCreated;

    return CareerCard(
      child: Row(
        // Top-aligned so the numbers share a baseline when one label wraps.
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: MetricTile(label: "Active applications", value: active?.toString(), alignment: CrossAxisAlignment.center)),
          Expanded(child: MetricTile(label: "CVs uploaded", value: cvs?.toString(), alignment: CrossAxisAlignment.center)),
          Expanded(child: MetricTile(label: "STAR stories", value: star?.toString(), alignment: CrossAxisAlignment.center)),
        ],
      ),
    );
  }
}

class _ProfessionalDetails extends StatelessWidget {
  const _ProfessionalDetails({required this.profile});

  final UserProfile profile;

  @override
  Widget build(BuildContext context) {
    final facts = <(IconData, String, String)>[
      if (profile.yearsOfExperience != null)
        (Icons.timelapse_rounded, "Experience", profile.yearsOfExperience == 1 ? "1 year" : "${profile.yearsOfExperience} years"),
      if (profile.highestEducation?.isNotEmpty ?? false) (AppIcons.scholarship, "Education", profile.highestEducation!),
      if (profile.fieldOfStudy?.isNotEmpty ?? false) (Icons.menu_book_rounded, "Field of study", profile.fieldOfStudy!),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(title: "Professional details", actionLabel: "Edit", onAction: () => showEditProfileSheet(context, profile)),
        if (facts.isEmpty)
          CareerCard(
            variant: CareerCardVariant.muted,
            onTap: () => showEditProfileSheet(context, profile),
            child: Row(
              children: [
                const IconTile(icon: Icons.edit_note_rounded, size: 40),
                Gap.sm,
                Expanded(
                  child: Text("Add your experience, education and field of study to complete your passport.", style: context.text.bodyMedium),
                ),
              ],
            ),
          )
        else
          CareerCard(
            variant: CareerCardVariant.outlined,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
            child: Column(children: [for (final f in facts) FactRow(icon: f.$1, label: f.$2, value: f.$3)]),
          ),
      ],
    );
  }
}
