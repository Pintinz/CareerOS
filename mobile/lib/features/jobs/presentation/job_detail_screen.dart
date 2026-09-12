import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../theme/app_colors.dart";
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
    final detailAsync = ref.watch(jobDetailProvider(widget.idOrSlug));

    return Scaffold(
      appBar: AppBar(title: const Text("Job Details")),
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
                  onPressed: () => ref.invalidate(jobDetailProvider(widget.idOrSlug)),
                  child: const Text("Retry"),
                ),
              ],
            ),
          ),
        ),
        data: (job) => _JobDetailBody(job: job, tabController: _tabController),
      ),
    );
  }
}

class _JobDetailBody extends ConsumerWidget {
  const _JobDetailBody({required this.job, required this.tabController});

  final JobDetail job;
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
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(job.title, style: Theme.of(context).textTheme.headlineMedium),
                          const SizedBox(height: 4),
                          Text(job.company.name, style: Theme.of(context).textTheme.titleLarge),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => _toggleSave(context, ref),
                      icon: Icon(
                        job.isSaved ? Icons.bookmark : Icons.bookmark_border,
                        color: job.isSaved ? AppColors.blue : AppColors.muted,
                        size: 28,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (job.location != null) _InfoPill(icon: Icons.location_on_outlined, label: job.location!),
                    _InfoPill(icon: Icons.work_outline, label: job.employmentType.replaceAll("_", "-")),
                    _InfoPill(icon: Icons.home_work_outlined, label: job.workMode.replaceAll("_", " ")),
                    if (job.isVerified)
                      const _InfoPill(icon: Icons.verified, label: "Verified source", color: AppColors.success),
                  ],
                ),
                if (job.applicationDeadline != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    "Deadline: ${DateFormat.yMMMd().format(job.applicationDeadline!)}",
                    style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600),
                  ),
                ],
                const SizedBox(height: 20),
                TabBar(
                  controller: tabController,
                  labelColor: AppColors.blue,
                  unselectedLabelColor: AppColors.muted,
                  indicatorColor: AppColors.blue,
                  tabs: const [Tab(text: "Overview"), Tab(text: "Requirements"), Tab(text: "Company")],
                ),
                SizedBox(
                  height: 400,
                  child: TabBarView(
                    controller: tabController,
                    children: [
                      _OverviewTab(job: job),
                      _RequirementsTab(job: job),
                      _CompanyTab(job: job),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        _ActionBar(job: job),
      ],
    );
  }

  Future<void> _toggleSave(BuildContext context, WidgetRef ref) async {
    // Called directly on the repository — this screen can be reached without the job ever
    // having been loaded into jobListProvider's state (e.g. from a company's Jobs tab, Saved
    // Items, or a deep link), where a list-relative toggle would silently no-op.
    final repo = ref.read(jobRepositoryProvider);
    if (job.isSaved) {
      await repo.unsave(job.id);
    } else {
      await repo.save(job.id);
    }
    ref.invalidate(jobDetailProvider(job.slug));
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (job.shortSummary != null) ...[
            Text(job.shortSummary!, style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 16),
          ],
          if (job.description != null) Text(job.description!, style: Theme.of(context).textTheme.bodyLarge),
          if (job.shortSummary == null && job.description == null)
            const Text("No description provided.", style: TextStyle(color: AppColors.muted)),
        ],
      ),
    );
  }
}

class _RequirementsTab extends StatelessWidget {
  const _RequirementsTab({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    final hasContent = (job.requirements?.isNotEmpty ?? false) ||
        (job.preferredSkills?.isNotEmpty ?? false) ||
        (job.benefits?.isNotEmpty ?? false);

    if (!hasContent) {
      return const Center(child: Text("No requirements listed.", style: TextStyle(color: AppColors.muted)));
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (job.requirements?.isNotEmpty ?? false) _BulletSection(title: "Requirements", items: job.requirements!),
          if (job.preferredSkills?.isNotEmpty ?? false)
            _BulletSection(title: "Preferred Skills", items: job.preferredSkills!),
          if (job.benefits?.isNotEmpty ?? false) _BulletSection(title: "Benefits", items: job.benefits!),
        ],
      ),
    );
  }
}

class _CompanyTab extends StatelessWidget {
  const _CompanyTab({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(job.company.name, style: Theme.of(context).textTheme.titleLarge),
          if (job.company.industry != null) ...[
            const SizedBox(height: 4),
            Text(job.company.industry!, style: const TextStyle(color: AppColors.muted)),
          ],
          if (job.company.description != null) ...[
            const SizedBox(height: 12),
            Text(job.company.description!),
          ],
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => context.push("/companies/${job.company.slug}"),
            icon: const Icon(Icons.business_outlined),
            label: const Text("View Company Profile"),
          ),
          if (job.company.websiteUrl != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => openExternalUrl(context, job.company.websiteUrl),
              icon: const Icon(Icons.language),
              label: const Text("Visit website"),
            ),
          ],
        ],
      ),
    );
  }
}

class _BulletSection extends StatelessWidget {
  const _BulletSection({required this.title, required this.items});

  final String title;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("•  "),
                  Expanded(child: Text(item)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({required this.icon, required this.label, this.color = AppColors.muted});

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _ActionBar extends StatelessWidget {
  const _ActionBar({required this.job});

  final JobDetail job;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: AppColors.card,
        border: Border(top: BorderSide(color: Color(0x1A000000))),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => context.push(
                  "/ats/analyze",
                  extra: AtsAnalyzeArgs(jobId: job.id, jobTitle: job.title),
                ),
                child: const Text("Analyze CV"),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: ElevatedButton(
                onPressed: job.applicationUrl != null ? () => openExternalUrl(context, job.applicationUrl) : null,
                child: Text(job.applicationUrl != null ? "Apply" : "No application link"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
