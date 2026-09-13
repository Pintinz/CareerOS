import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../../applications/presentation/application_providers.dart";
import "../../ats/presentation/ats_analyze_screen.dart";
import "../data/job_models.dart";
import "job_providers.dart";

class JobDetailScreen extends ConsumerStatefulWidget {
  const JobDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  ConsumerState<JobDetailScreen> createState() => _JobDetailScreenState();
}

class _JobDetailScreenState extends ConsumerState<JobDetailScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 3, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(jobDetailProvider(widget.idOrSlug));

    return detailAsync.when(
      loading: () => const DetailSkeleton(),
      error: (error, _) => DetailError(
        title: "We couldn't load this job",
        message: error.userMessage,
        onRetry: () => ref.invalidate(jobDetailProvider(widget.idOrSlug)),
      ),
      data: (job) => _JobDetailView(job: job, tabController: _tabController),
    );
  }
}

/// Guards the Save/Unsave button against a rapid double-tap firing two conflicting requests
/// before the first one's response invalidates [jobDetailProvider] (Phase 9.5 audit finding).
final _jobSaveInFlightProvider = StateProvider.family<bool, String>((ref, jobId) => false);

class _JobDetailView extends ConsumerWidget {
  const _JobDetailView({required this.job, required this.tabController});

  final JobDetail job;
  final TabController tabController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final saving = ref.watch(_jobSaveInFlightProvider(job.id));
    final hasApplyLink = job.applicationUrl != null && job.applicationUrl!.isNotEmpty;

    return DetailScaffold(
      title: job.title,
      bannerUrl: job.postImageUrl ?? job.company.bannerUrl,
      logoUrl: job.company.logoUrl,
      logoFallbackText: job.company.name,
      tabController: tabController,
      actions: [
        IconButton(
          tooltip: "Company profile",
          onPressed: () => context.push("/companies/${job.company.slug}"),
          icon: const Icon(AppIcons.company),
        ),
      ],
      header: _JobHeader(job: job, onTrack: () => _trackApplication(context, ref)),
      tabs: const ["Overview", "Requirements", "Company"],
      tabViews: [
        _OverviewTab(job: job),
        _RequirementsTab(job: job),
        _CompanyTab(job: job),
      ],
      bottomBar: BottomActionBar(
        secondary: AppOutlineButton(
          expand: false,
          label: job.isSaved ? "Saved" : "Save",
          icon: job.isSaved ? AppIcons.savedSelected : AppIcons.saved,
          isLoading: saving,
          onPressed: () => _toggleSave(ref),
        ),
        primary: hasApplyLink
            ? PrimaryButton(label: "Apply", icon: AppIcons.external, onPressed: () => openExternalUrl(context, job.applicationUrl))
            : PrimaryButton(label: "How to Apply", onPressed: () => tabController.animateTo(0)),
      ),
    );
  }

  Future<void> _toggleSave(WidgetRef ref) async {
    // Called directly on the repository — this screen can be reached without the job ever
    // having been loaded into jobListProvider's state (e.g. from a company's Jobs tab, Saved
    // Items, or a deep link), where a list-relative toggle would silently no-op.
    ref.read(_jobSaveInFlightProvider(job.id).notifier).state = true;
    try {
      final repo = ref.read(jobRepositoryProvider);
      if (job.isSaved) {
        await repo.unsave(job.id);
      } else {
        await repo.save(job.id);
      }
      ref.invalidate(jobDetailProvider(job.slug));
    } finally {
      ref.read(_jobSaveInFlightProvider(job.id).notifier).state = false;
    }
  }

  Future<void> _trackApplication(BuildContext context, WidgetRef ref) async {
    try {
      final application = await ref.read(applicationRepositoryProvider).createFromJob(job.id);
      if (context.mounted) context.push("/applications/${application.id}");
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
      }
    }
  }
}

class _JobHeader extends StatelessWidget {
  const _JobHeader({required this.job, required this.onTrack});

  final JobDetail job;
  final VoidCallback onTrack;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final deadline = job.applicationDeadline;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(job.title, style: context.text.headlineSmall),
        const SizedBox(height: 2),
        Row(
          children: [
            Flexible(child: Text(job.company.name, style: context.text.bodyLarge?.copyWith(color: colors.textSecondary))),
            if (job.isVerified) ...[
              Gap.xxs,
              Semantics(label: "Verified", child: const Icon(AppIcons.verified, size: 16, color: AppColors.success)),
            ],
          ],
        ),
        Gap.sm,
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            if (job.location != null) TagChip(label: job.location!, icon: AppIcons.location),
            TagChip(label: humanizeEnum(job.employmentType)),
            TagChip(label: humanizeEnum(job.workMode)),
            if (job.experienceLevel != null) TagChip(label: humanizeEnum(job.experienceLevel!)),
            if (job.isDemo) const TagChip(label: "DEMO"),
          ],
        ),
        Gap.sm,
        Wrap(
          spacing: AppSpacing.md,
          runSpacing: AppSpacing.xxs,
          children: [
            if (job.publishedAt != null)
              _MetaText(icon: AppIcons.time, text: "Posted ${DateLabels.published(job.publishedAt!).toLowerCase()}"),
            if (deadline != null)
              _MetaText(
                icon: AppIcons.deadline,
                text: DateLabels.deadline(deadline),
                color: DateLabels.deadlineTone(deadline).onTint(context),
              ),
          ],
        ),
        Gap.md,
        Row(
          children: [
            Expanded(
              child: SecondaryButton(
                label: "Analyze & Tailor CV",
                icon: AppIcons.cv,
                onPressed: () => context.push("/ats/analyze", extra: AtsAnalyzeArgs(jobId: job.id, jobTitle: job.title)),
              ),
            ),
            Gap.xs,
            IconButton.outlined(
              tooltip: "Track this application",
              onPressed: onTrack,
              icon: const Icon(Icons.playlist_add_check_rounded),
              style: IconButton.styleFrom(
                side: BorderSide(color: colors.border),
                shape: const RoundedRectangleBorder(borderRadius: AppRadius.buttonAll),
                minimumSize: const Size(52, 48),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _MetaText extends StatelessWidget {
  const _MetaText({required this.icon, required this.text, this.color});

  final IconData icon;
  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? context.colors.textSecondary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: c),
        const SizedBox(width: 4),
        Text(text, style: context.text.bodySmall?.copyWith(color: c, fontWeight: color != null ? FontWeight.w600 : null)),
      ],
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.job});

  final JobDetail job;

  String? get _salary {
    if (job.salaryMin == null && job.salaryMax == null) return null;
    final format = NumberFormat.decimalPattern();
    final currency = job.salaryCurrency ?? "";
    final range = job.salaryMin != null && job.salaryMax != null
        ? "${format.format(job.salaryMin)} – ${format.format(job.salaryMax)}"
        : format.format(job.salaryMin ?? job.salaryMax);
    final period = job.salaryPeriod != null ? " / ${humanizeEnum(job.salaryPeriod!).toLowerCase()}" : "";
    return "$currency $range$period".trim();
  }

  @override
  Widget build(BuildContext context) {
    final hasHowToApply = job.applicationInstructions != null || job.applicationEmail != null;
    final salary = _salary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (salary != null || job.industry != null || job.country != null)
          DetailSection(
            title: "Key details",
            child: Column(
              children: [
                if (salary != null) FactRow(icon: Icons.payments_outlined, label: "Salary", value: salary),
                if (job.industry != null) FactRow(icon: AppIcons.company, label: "Industry", value: job.industry!),
                if (job.country != null) FactRow(icon: Icons.public_rounded, label: "Country", value: job.country!),
              ],
            ),
          ),
        if (job.shortSummary != null || job.description != null)
          DetailSection(
            title: "About the role",
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (job.shortSummary != null) Text(job.shortSummary!, style: context.text.bodyLarge?.copyWith(fontWeight: FontWeight.w500)),
                if (job.shortSummary != null && job.description != null) Gap.sm,
                if (job.description != null) Text(job.description!, style: context.text.bodyLarge),
              ],
            ),
          ),
        if (job.responsibilities?.isNotEmpty ?? false)
          DetailSection(title: "Responsibilities", child: BulletList(items: job.responsibilities!)),
        if (hasHowToApply)
          DetailSection(
            title: "How to apply",
            icon: Icons.assignment_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (job.applicationInstructions != null) Text(job.applicationInstructions!, style: context.text.bodyLarge),
                if (job.applicationEmail != null) ...[
                  Gap.xs,
                  SelectableText(job.applicationEmail!, style: context.text.titleSmall?.copyWith(color: context.colors.primary)),
                ],
              ],
            ),
          ),
        if (job.shortSummary == null && job.description == null && !hasHowToApply)
          const EmptyState(
            compact: true,
            icon: AppIcons.job,
            title: "No description provided",
            message: "The employer hasn't shared more detail yet. Check the official listing when you apply.",
          ),
        if (job.sourceUrl != null)
          TextButton.icon(
            onPressed: () => openExternalUrl(context, job.sourceUrl),
            icon: const Icon(AppIcons.external, size: 18),
            label: const Text("View original listing"),
          ),
      ],
    );
  }
}

class _RequirementsTab extends StatelessWidget {
  const _RequirementsTab({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    final hasContent =
        (job.requirements?.isNotEmpty ?? false) || (job.preferredSkills?.isNotEmpty ?? false) || (job.benefits?.isNotEmpty ?? false);

    if (!hasContent) {
      return const EmptyState(
        compact: true,
        icon: Icons.checklist_rounded,
        title: "No requirements listed",
        message: "This listing doesn't specify requirements. Review the official posting before applying.",
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (job.requirements?.isNotEmpty ?? false) DetailSection(title: "Requirements", child: BulletList(items: job.requirements!)),
        if (job.preferredSkills?.isNotEmpty ?? false)
          DetailSection(
            title: "Preferred skills",
            child: Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: [for (final skill in job.preferredSkills!) TagChip(label: skill, tone: AppTone.primary)],
            ),
          ),
        if (job.benefits?.isNotEmpty ?? false) DetailSection(title: "Benefits", child: BulletList(items: job.benefits!, checked: true)),
      ],
    );
  }
}

class _CompanyTab extends StatelessWidget {
  const _CompanyTab({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    final company = job.company;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CareerCard(
          onTap: () => context.push("/companies/${company.slug}"),
          child: Row(
            children: [
              NetworkImageWithFallback(url: company.logoUrl, fallbackText: company.name, size: 48),
              Gap.sm,
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(company.name, style: context.text.titleMedium),
                    if (company.industry != null || company.headquarters != null)
                      Text(
                        [if (company.industry != null) company.industry!, if (company.headquarters != null) company.headquarters!].join(" · "),
                        style: context.text.bodySmall,
                      ),
                  ],
                ),
              ),
              Icon(AppIcons.chevron, color: context.colors.textSecondary),
            ],
          ),
        ),
        Gap.lg,
        if (company.description != null) DetailSection(title: "About", child: Text(company.description!, style: context.text.bodyLarge)),
        if (company.websiteUrl != null)
          AppOutlineButton(
            label: "Visit website",
            icon: Icons.language_rounded,
            onPressed: () => openExternalUrl(context, company.websiteUrl),
          ),
      ],
    );
  }
}
