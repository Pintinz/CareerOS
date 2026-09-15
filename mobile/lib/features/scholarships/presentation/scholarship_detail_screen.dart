import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../data/scholarship_models.dart";
import "scholarship_providers.dart";

class ScholarshipDetailScreen extends ConsumerStatefulWidget {
  const ScholarshipDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  ConsumerState<ScholarshipDetailScreen> createState() => _ScholarshipDetailScreenState();
}

class _ScholarshipDetailScreenState extends ConsumerState<ScholarshipDetailScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(length: 3, vsync: this);

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(scholarshipDetailProvider(widget.idOrSlug));

    return detailAsync.when(
      loading: () => const DetailSkeleton(),
      error: (error, _) => DetailError(
        title: "We couldn't load this scholarship",
        message: error.userMessage,
        onRetry: () => ref.invalidate(scholarshipDetailProvider(widget.idOrSlug)),
      ),
      data: (scholarship) => _ScholarshipDetailView(scholarship: scholarship, tabController: _tabController),
    );
  }
}

/// Same double-tap guard as job detail's save button.
final _scholarshipSaveInFlightProvider = StateProvider.family<bool, String>((ref, id) => false);

class _ScholarshipDetailView extends ConsumerWidget {
  const _ScholarshipDetailView({required this.scholarship, required this.tabController});

  final ScholarshipDetail scholarship;
  final TabController tabController;

  Future<void> _toggleSave(WidgetRef ref) async {
    // Direct repository call — this screen can be reached without the scholarship being in
    // scholarshipListProvider's state (deep link, Saved Items), where a list-relative toggle
    // would silently no-op.
    ref.read(_scholarshipSaveInFlightProvider(scholarship.id).notifier).state = true;
    try {
      final repo = ref.read(scholarshipRepositoryProvider);
      if (scholarship.isSaved) {
        await repo.unsave(scholarship.id);
      } else {
        await repo.save(scholarship.id);
      }
      ref.invalidate(scholarshipDetailProvider(scholarship.slug));
    } finally {
      ref.read(_scholarshipSaveInFlightProvider(scholarship.id).notifier).state = false;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final saving = ref.watch(_scholarshipSaveInFlightProvider(scholarship.id));
    final hasLink = scholarship.officialUrl != null && scholarship.officialUrl!.isNotEmpty;
    final availability = OpportunityAvailability.fromApi(scholarship.availability);
    final sourceLink = scholarship.officialUrl ?? scholarship.sourceUrl;

    return DetailScaffold(
      title: scholarship.name,
      bannerUrl: scholarship.postImageUrl,
      logoUrl: scholarship.thumbnailUrl,
      logoFallbackText: scholarship.organization ?? scholarship.name,
      logoFallbackIcon: AppIcons.scholarship,
      logoTone: AppTone.purple,
      tabController: tabController,
      header: _ScholarshipHeader(scholarship: scholarship),
      tabs: const ["Overview", "Eligibility", "Documents"],
      tabViews: [
        _OverviewTab(scholarship: scholarship),
        _EligibilityTab(scholarship: scholarship),
        _DocumentsTab(scholarship: scholarship),
      ],
      bottomBar: BottomActionBar(
        secondary: AppOutlineButton(
          expand: false,
          label: scholarship.isSaved ? "Saved" : "Save",
          icon: scholarship.isSaved ? AppIcons.savedSelected : AppIcons.saved,
          isLoading: saving,
          onPressed: () => _toggleSave(ref),
        ),
        // Never "Apply Now" for an award that has closed, expired or left its source.
        primary: !availability.isActive
            ? (availability.sourceStillMeaningful && sourceLink != null
                ? AppOutlineButton(label: "View source", icon: AppIcons.external, onPressed: () => openExternalUrl(context, sourceLink))
                : const PrimaryButton(label: "No longer accepting applications", onPressed: null))
            : PrimaryButton(
                label: hasLink ? "Apply Now" : "No application link",
                icon: hasLink ? AppIcons.external : null,
                onPressed: hasLink ? () => openExternalUrl(context, scholarship.officialUrl) : null,
              ),
      ),
    );
  }
}

class _ScholarshipHeader extends StatelessWidget {
  const _ScholarshipHeader({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final deadline = scholarship.applicationDeadline;
    final availability = OpportunityAvailability.fromApi(scholarship.availability);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!availability.isActive) ...[AvailabilityNotice(availability: availability), Gap.sm],
        if (scholarship.organization != null) Text(scholarship.organization!, style: context.text.labelMedium),
        const SizedBox(height: 2),
        Text(scholarship.name, style: context.text.headlineSmall),
        Gap.sm,
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            if (scholarship.country != null) TagChip(label: scholarship.country!, icon: AppIcons.location),
            for (final level in scholarship.degreeLevels ?? const <String>[]) TagChip(label: humanizeEnum(level)),
            if (scholarship.awardType == "FELLOWSHIP") const TagChip(label: "Fellowship", tone: AppTone.purple),
            if (isStatedValue(scholarship.fundingType))
              TagChip(
                label: humanizeEnum(scholarship.fundingType),
                tone: scholarship.fundingType == "FULLY_FUNDED" ? AppTone.success : null,
              ),
            if (scholarship.isVerified) const TagChip(label: "Verified", icon: AppIcons.verified, tone: AppTone.success),
            if (scholarship.isDemo) const TagChip(label: "DEMO"),
          ],
        ),
        if (scholarship.isOfficialSource) ...[
          Gap.xs,
          SourceProvenance(isOfficialSource: scholarship.isOfficialSource, lastVerifiedAt: scholarship.lastVerifiedAt),
        ],
        if (deadline != null && availability.isActive) ...[
          Gap.sm,
          Row(
            children: [
              Icon(AppIcons.deadline, size: 16, color: DateLabels.deadlineTone(deadline).onTint(context)),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  DateLabels.daysUntil(deadline) <= 30 ? "${DateLabels.deadline(deadline)} · ${DateLabels.shortDate(deadline)}" : DateLabels.deadline(deadline),
                  style: context.text.titleSmall?.copyWith(color: DateLabels.deadlineTone(deadline).onTint(context)),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final coverage = <(String, String?)>[
      ("Tuition", scholarship.tuitionCoverage),
      ("Monthly stipend", scholarship.monthlyStipend),
      ("Travel", scholarship.travelSupport),
      ("Insurance", scholarship.insuranceSupport),
      ("Accommodation", scholarship.accommodationSupport),
    ].where((e) => e.$2 != null && e.$2!.isNotEmpty).toList();
    final about = scholarship.description ?? scholarship.summary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (coverage.isNotEmpty)
          DetailSection(
            title: "Funding Coverage",
            child: CareerCard(
              variant: CareerCardVariant.outlined,
              child: Column(
                children: [
                  for (final entry in coverage)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.check_circle_rounded, size: 20, color: AppColors.success),
                          Gap.sm,
                          Expanded(child: Text(entry.$1, style: context.text.titleSmall)),
                          Gap.sm,
                          Flexible(child: Text(entry.$2!, textAlign: TextAlign.end, style: context.text.bodyMedium)),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        if (scholarship.fieldsOfStudy?.isNotEmpty ?? false)
          DetailSection(
            title: "Fields of Study",
            child: Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: [for (final field in scholarship.fieldsOfStudy!) TagChip(label: field, tone: AppTone.purple)],
            ),
          ),
        if (about != null)
          DetailSection(title: "About This Scholarship", child: Text(about, style: context.text.bodyLarge))
        else if (coverage.isEmpty)
          const EmptyState(
            compact: true,
            icon: AppIcons.scholarship,
            title: "No description provided",
            message: "The provider hasn't shared more detail yet. Check the official page before applying.",
          ),
      ],
    );
  }
}

class _EligibilityTab extends StatelessWidget {
  const _EligibilityTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, IconData, List<String>?)>[
      ("Degree levels", Icons.school_outlined, scholarship.degreeLevels?.map(humanizeEnum).toList()),
      ("Eligible nationalities", Icons.public_rounded, scholarship.eligibleNationalities),
      ("Academic requirements", Icons.menu_book_rounded, scholarship.academicRequirements),
      ("Language requirements", Icons.translate_rounded, scholarship.languageRequirements),
    ].where((r) => r.$3?.isNotEmpty ?? false).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Spec §18: never a blanket "you are eligible" claim or an eligibility percentage — only the
        // provider's stated requirements. Profile-based eligibility matching isn't built yet.
        const InsightCard(
          icon: Icons.info_outline_rounded,
          tone: AppTone.info,
          title: "Requirements as stated by the provider",
          message: "CareerOS doesn't yet match these against your profile — confirm eligibility on the official page.",
        ),
        Gap.xl,
        for (final row in rows) DetailSection(title: row.$1, icon: row.$2, child: BulletList(items: row.$3!)),
        if (scholarship.ageRequirement != null)
          DetailSection(title: "Age Requirement", icon: Icons.cake_outlined, child: Text(scholarship.ageRequirement!, style: context.text.bodyLarge)),
        if (rows.isEmpty && scholarship.ageRequirement == null)
          const EmptyState(
            compact: true,
            icon: Icons.checklist_rounded,
            title: "No eligibility criteria listed",
            message: "Check the provider's official page for full eligibility details.",
          ),
      ],
    );
  }
}

class _DocumentsTab extends StatelessWidget {
  const _DocumentsTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final documents = scholarship.requiredDocuments ?? const <String>[];
    if (documents.isEmpty) {
      return const EmptyState(
        compact: true,
        icon: AppIcons.cv,
        title: "No document list provided",
        message: "The provider hasn't listed required documents. Check the official page before you apply.",
      );
    }
    return CareerListGroup(
      title: "Required Documents",
      children: [
        for (final doc in documents) CareerListRow(icon: AppIcons.cv, title: doc, tone: AppTone.purple),
      ],
    );
  }
}
