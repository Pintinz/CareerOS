import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../../intelligence/data/intelligence_models.dart";
import "../../intelligence/presentation/intelligence_card.dart";
import "../../intelligence/presentation/intelligence_providers.dart";
import "../../jobs/data/job_models.dart";
import "../../jobs/presentation/job_card.dart";
import "../../jobs/presentation/job_providers.dart";
import "../data/company_models.dart";
import "company_providers.dart";

class CompanyDetailScreen extends ConsumerStatefulWidget {
  const CompanyDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  ConsumerState<CompanyDetailScreen> createState() => _CompanyDetailScreenState();
}

class _CompanyDetailScreenState extends ConsumerState<CompanyDetailScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 3, vsync: this);
  bool? _optimisticFollowing;

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _toggleFollow(Company company) async {
    final newValue = !(_optimisticFollowing ?? company.isFollowing);
    setState(() => _optimisticFollowing = newValue);
    try {
      await ref.read(companyFollowControllerProvider.notifier).toggle(company.id, !newValue);
    } catch (_) {
      setState(() => _optimisticFollowing = !newValue);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(companyDetailProvider(widget.idOrSlug));

    return detailAsync.when(
      loading: () => const DetailSkeleton(),
      error: (error, _) => DetailError(
        title: "We couldn't load this company",
        message: error.userMessage,
        onRetry: () => ref.invalidate(companyDetailProvider(widget.idOrSlug)),
      ),
      data: (company) {
        final isFollowing = _optimisticFollowing ?? company.isFollowing;
        return DetailScaffold(
          title: company.name,
          bannerUrl: company.bannerUrl,
          logoUrl: company.logoUrl,
          logoFallbackText: company.name,
          tabController: _tabController,
          header: _CompanyHeader(
            company: company,
            isFollowing: isFollowing,
            onToggleFollow: () => _toggleFollow(company),
            onOpenTab: _tabController.animateTo,
          ),
          tabs: const ["Overview", "Jobs", "Intelligence"],
          tabViews: [
            _OverviewTab(company: company),
            _CompanyJobsTab(companyId: company.id),
            _CompanyNewsTab(companyId: company.id),
          ],
        );
      },
    );
  }
}

class _CompanyHeader extends ConsumerWidget {
  const _CompanyHeader({required this.company, required this.isFollowing, required this.onToggleFollow, required this.onOpenTab});

  final Company company;
  final bool isFollowing;
  final VoidCallback onToggleFollow;
  final ValueChanged<int> onOpenTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobsTotal = ref.watch(_companyJobsProvider(company.id)).valueOrNull?.total;
    final newsTotal = ref.watch(_companyNewsProvider(company.id)).valueOrNull?.total;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(company.name, style: context.text.headlineSmall),
                  if (company.industry != null || company.headquarters != null)
                    Text(
                      [if (company.industry != null) company.industry!, if (company.headquarters != null) company.headquarters!].join(" · "),
                      style: context.text.bodyMedium,
                    ),
                ],
              ),
            ),
            Gap.sm,
            isFollowing
                ? AppOutlineButton(label: "Following", icon: AppIcons.check, expand: false, onPressed: onToggleFollow)
                : PrimaryButton(label: "Follow", icon: AppIcons.add, expand: false, onPressed: onToggleFollow),
          ],
        ),
        // Verification sits with the other labels rather than beside the name, where a long name
        // squeezed by the Follow button left the mark stranded on its own line.
        if (company.isVerified || company.isDemo) ...[
          Gap.xs,
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              if (company.isVerified) const StatusChip(label: "Verified", tone: AppTone.success, icon: AppIcons.verified),
              if (company.isDemo) const TagChip(label: "DEMO"),
            ],
          ),
        ],
        Gap.md,
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: StatCard(label: "Open jobs", value: jobsTotal?.toString(), icon: AppIcons.job, onTap: () => onOpenTab(1)),
              ),
              Gap.sm,
              Expanded(
                child: StatCard(
                  label: "Intelligence updates",
                  value: newsTotal?.toString(),
                  icon: AppIcons.intelligence,
                  tone: AppTone.info,
                  onTap: () => onOpenTab(2),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.company});

  final Company company;

  @override
  Widget build(BuildContext context) {
    final hasFacts = company.headquarters != null || company.country != null || company.industry != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (company.description != null) DetailSection(title: "About", child: Text(company.description!, style: context.text.bodyLarge)),
        if (hasFacts)
          DetailSection(
            title: "Company Facts",
            child: Column(
              children: [
                if (company.industry != null) FactRow(icon: AppIcons.company, label: "Industry", value: company.industry!),
                if (company.headquarters != null) FactRow(icon: AppIcons.location, label: "Headquarters", value: company.headquarters!),
                if (company.country != null) FactRow(icon: Icons.public_rounded, label: "Country", value: company.country!),
              ],
            ),
          ),
        if (company.careerUrl != null) ...[
          SecondaryButton(label: "Careers page", icon: AppIcons.job, onPressed: () => openExternalUrl(context, company.careerUrl)),
          Gap.sm,
        ],
        if (company.websiteUrl != null)
          AppOutlineButton(label: "Visit website", icon: Icons.language_rounded, onPressed: () => openExternalUrl(context, company.websiteUrl)),
        if (company.description == null && !hasFacts && company.websiteUrl == null && company.careerUrl == null)
          const EmptyState(
            compact: true,
            icon: AppIcons.company,
            title: "No company profile yet",
            message: "Details for this company haven't been added. Their jobs and updates still appear in the other tabs.",
          ),
      ],
    );
  }
}

class _CompanyJobsTab extends ConsumerWidget {
  const _CompanyJobsTab({required this.companyId});

  final String companyId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobsAsync = ref.watch(_companyJobsProvider(companyId));
    return jobsAsync.when(
      loading: () => const Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]),
      error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(_companyJobsProvider(companyId))),
      data: (result) {
        final jobs = result.items;
        if (jobs.isEmpty) {
          return const EmptyState(
            compact: true,
            icon: AppIcons.job,
            title: "No open jobs right now",
            message: "Follow this company to hear about new roles and hiring news.",
          );
        }
        return Column(
          children: [
            for (final (i, job) in jobs.indexed) ...[
              if (i > 0) Gap.sm,
              JobCardTile(
                job: job,
                onTap: () => context.push("/jobs/${job.slug}"),
                onToggleSave: () async {
                  // Direct repository call — these jobs aren't in jobListProvider's state, where
                  // a list-relative toggle would silently no-op.
                  if (job.isSaved) {
                    await ref.read(jobRepositoryProvider).unsave(job.id);
                  } else {
                    await ref.read(jobRepositoryProvider).save(job.id);
                  }
                  ref.invalidate(_companyJobsProvider(companyId));
                },
              ),
            ],
          ],
        );
      },
    );
  }
}

class _CompanyNewsTab extends ConsumerWidget {
  const _CompanyNewsTab({required this.companyId});

  final String companyId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final newsAsync = ref.watch(_companyNewsProvider(companyId));
    return newsAsync.when(
      loading: () => const Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]),
      error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(_companyNewsProvider(companyId))),
      data: (result) {
        final posts = result.items;
        if (posts.isEmpty) {
          return const EmptyState(
            compact: true,
            icon: AppIcons.intelligence,
            title: "No intelligence updates yet",
            message: "Hiring, leadership and project news about this company will appear here.",
          );
        }
        return Column(
          children: [
            for (final (i, post) in posts.indexed) ...[
              if (i > 0) Gap.sm,
              IntelligenceCardTile(post: post),
            ],
          ],
        );
      },
    );
  }
}

final _companyJobsProvider = FutureProvider.autoDispose.family<({List<JobCard> items, int total}), String>((ref, companyId) {
  return ref.watch(jobRepositoryProvider).listByCompany(companyId);
});

final _companyNewsProvider = FutureProvider.autoDispose.family<({List<IntelligenceCard> items, int total}), String>((ref, companyId) {
  return ref.watch(intelligenceRepositoryProvider).listByCompany(companyId);
});
