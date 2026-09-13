import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/design/design.dart";
import "../data/scholarship_models.dart";
import "scholarship_providers.dart";

class ScholarshipDetailScreen extends ConsumerStatefulWidget {
  const ScholarshipDetailScreen({super.key, required this.idOrSlug});

  final String idOrSlug;

  @override
  ConsumerState<ScholarshipDetailScreen> createState() => _ScholarshipDetailScreenState();
}

class _ScholarshipDetailScreenState extends ConsumerState<ScholarshipDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(scholarshipDetailProvider(widget.idOrSlug));

    return Scaffold(
      appBar: AppBar(title: const Text("Scholarship Details")),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(error.userMessage, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => ref.invalidate(scholarshipDetailProvider(widget.idOrSlug)),
                  child: const Text("Retry"),
                ),
              ],
            ),
          ),
        ),
        data: (scholarship) => _ScholarshipDetailBody(scholarship: scholarship, tabController: _tabController),
      ),
    );
  }
}

class _ScholarshipDetailBody extends ConsumerWidget {
  const _ScholarshipDetailBody({required this.scholarship, required this.tabController});

  final ScholarshipDetail scholarship;
  final TabController tabController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(child: Text(scholarship.name, style: Theme.of(context).textTheme.headlineMedium)),
                    IconButton(
                      onPressed: () async {
                        // Direct repository call — this screen can be reached without the
                        // scholarship being in scholarshipListProvider's state (deep link,
                        // Saved Items), where a list-relative toggle would silently no-op.
                        final repo = ref.read(scholarshipRepositoryProvider);
                        if (scholarship.isSaved) {
                          await repo.unsave(scholarship.id);
                        } else {
                          await repo.save(scholarship.id);
                        }
                        ref.invalidate(scholarshipDetailProvider(scholarship.slug));
                      },
                      icon: Icon(
                        scholarship.isSaved ? Icons.bookmark : Icons.bookmark_border,
                        color: scholarship.isSaved ? AppColors.blue : AppColors.muted,
                        size: 28,
                      ),
                    ),
                  ],
                ),
                if (scholarship.organization != null)
                  Text(scholarship.organization!, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                if (scholarship.applicationDeadline != null)
                  Text(
                    "Deadline: ${DateFormat.yMMMd().format(scholarship.applicationDeadline!)}",
                    style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600),
                  ),
                const SizedBox(height: 16),
                _FundingCards(scholarship: scholarship),
                const SizedBox(height: 20),
                TabBar(
                  controller: tabController,
                  labelColor: AppColors.blue,
                  unselectedLabelColor: AppColors.muted,
                  indicatorColor: AppColors.blue,
                  tabs: const [Tab(text: "Overview"), Tab(text: "Eligibility"), Tab(text: "Documents")],
                ),
                SizedBox(
                  height: 350,
                  child: TabBarView(
                    controller: tabController,
                    children: [
                      _OverviewTab(scholarship: scholarship),
                      _EligibilityTab(scholarship: scholarship),
                      _DocumentsTab(scholarship: scholarship),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: const BoxDecoration(color: AppColors.card, border: Border(top: BorderSide(color: Color(0x1A000000)))),
          child: SafeArea(
            top: false,
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: scholarship.officialUrl != null ? () => openExternalUrl(context, scholarship.officialUrl) : null,
                child: Text(scholarship.officialUrl != null ? "Apply" : "No application link provided"),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _FundingCards extends StatelessWidget {
  const _FundingCards({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final entries = <(String, String?)>[
      ("Tuition", scholarship.tuitionCoverage),
      ("Monthly stipend", scholarship.monthlyStipend),
      ("Travel", scholarship.travelSupport),
      ("Insurance", scholarship.insuranceSupport),
      ("Accommodation", scholarship.accommodationSupport),
    ].where((e) => e.$2 != null).toList();

    if (entries.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final entry in entries)
          Container(
            width: 140,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(12)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(entry.$1, style: const TextStyle(fontSize: 11, color: AppColors.muted)),
                const SizedBox(height: 4),
                Text(entry.$2!, style: const TextStyle(fontWeight: FontWeight.w600), maxLines: 2, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
      ],
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Text(
        scholarship.description ?? scholarship.summary ?? "No description provided.",
        style: Theme.of(context).textTheme.bodyLarge,
      ),
    );
  }
}

class _EligibilityTab extends StatelessWidget {
  const _EligibilityTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, List<String>?)>[
      ("Degree levels", scholarship.degreeLevels),
      ("Eligible nationalities", scholarship.eligibleNationalities),
      ("Academic requirements", scholarship.academicRequirements),
      ("Language requirements", scholarship.languageRequirements),
    ];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Spec §18: never a blanket "you are eligible" claim — just show the stated
          // requirements factually. Real eligibility scoring needs a user profile (later phase).
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Text(
              "Requirements as stated by the provider. Full eligibility matching against your "
              "profile isn't available yet.",
              style: TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ),
          for (final row in rows)
            if (row.$2?.isNotEmpty ?? false)
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(row.$1, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(row.$2!.join(", ")),
                  ],
                ),
              ),
          if (scholarship.ageRequirement != null)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Age requirement", style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(scholarship.ageRequirement!),
              ],
            ),
        ],
      ),
    );
  }
}

class _DocumentsTab extends StatelessWidget {
  const _DocumentsTab({required this.scholarship});

  final ScholarshipDetail scholarship;

  @override
  Widget build(BuildContext context) {
    final documents = scholarship.requiredDocuments ?? [];
    if (documents.isEmpty) {
      return const Center(child: Text("No document list provided.", style: TextStyle(color: AppColors.muted)));
    }
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final doc in documents)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  const Icon(Icons.description_outlined, size: 18, color: AppColors.muted),
                  const SizedBox(width: 8),
                  Expanded(child: Text(doc)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
