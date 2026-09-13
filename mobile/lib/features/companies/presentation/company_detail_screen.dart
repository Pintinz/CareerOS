import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/design/design.dart";
import "../../intelligence/data/intelligence_models.dart";
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
  late final TabController _tabController;
  bool? _optimisticFollowing;

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

    return Scaffold(
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
                  onPressed: () => ref.invalidate(companyDetailProvider(widget.idOrSlug)),
                  child: const Text("Retry"),
                ),
              ],
            ),
          ),
        ),
        data: (company) {
          final isFollowing = _optimisticFollowing ?? company.isFollowing;
          return Column(
            children: [
              AppBar(title: Text(company.name)),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    _CompanyLogo(logoUrl: company.logoUrl, name: company.name),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(company.name, style: Theme.of(context).textTheme.titleLarge),
                          if (company.industry != null) Text(company.industry!, style: const TextStyle(color: AppColors.muted)),
                        ],
                      ),
                    ),
                    OutlinedButton(
                      onPressed: () => _toggleFollow(company),
                      style: isFollowing ? OutlinedButton.styleFrom(foregroundColor: AppColors.muted) : null,
                      child: Text(isFollowing ? "Following" : "Follow"),
                    ),
                  ],
                ),
              ),
              TabBar(
                controller: _tabController,
                labelColor: AppColors.blue,
                unselectedLabelColor: AppColors.muted,
                indicatorColor: AppColors.blue,
                tabs: const [Tab(text: "Overview"), Tab(text: "Jobs"), Tab(text: "News")],
              ),
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _OverviewTab(company: company),
                    _CompanyJobsTab(companyId: company.id),
                    _CompanyNewsTab(companyId: company.id),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _CompanyLogo extends StatelessWidget {
  const _CompanyLogo({required this.logoUrl, required this.name});

  final String? logoUrl;
  final String name;

  @override
  Widget build(BuildContext context) {
    final fallback = Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(color: AppColors.blue.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
      alignment: Alignment.center,
      child: Text(
        name.isNotEmpty ? name[0].toUpperCase() : "?",
        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.blue),
      ),
    );
    if (logoUrl == null || logoUrl!.isEmpty) return fallback;
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: CachedNetworkImage(
        imageUrl: logoUrl!,
        width: 56,
        height: 56,
        fit: BoxFit.cover,
        placeholder: (context, url) => fallback,
        errorWidget: (context, url, error) => fallback,
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.company});

  final Company company;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (company.description != null) ...[
            Text(company.description!, style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 16),
          ],
          if (company.headquarters != null) _InfoRow(label: "Headquarters", value: company.headquarters!),
          if (company.country != null) _InfoRow(label: "Country", value: company.country!),
          if (company.industry != null) _InfoRow(label: "Industry", value: company.industry!),
          if (company.websiteUrl != null) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => openExternalUrl(context, company.websiteUrl),
              icon: const Icon(Icons.language),
              label: const Text("Visit website"),
            ),
          ],
          if (company.careerUrl != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => openExternalUrl(context, company.careerUrl),
              icon: const Icon(Icons.work_outline),
              label: const Text("Careers page"),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(width: 110, child: Text(label, style: const TextStyle(color: AppColors.muted))),
          Expanded(child: Text(value)),
        ],
      ),
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
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text(e.userMessage)),
      data: (jobs) {
        if (jobs.isEmpty) {
          return const Center(child: Text("No open jobs right now.", style: TextStyle(color: AppColors.muted)));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: jobs.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final job = jobs[index];
            return JobCardTile(
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
            );
          },
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
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text(e.userMessage)),
      data: (posts) {
        if (posts.isEmpty) {
          return const Center(child: Text("No news yet.", style: TextStyle(color: AppColors.muted)));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: posts.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final post = posts[index];
            return Card(
              child: ListTile(
                title: Text(post.headline),
                subtitle: Text(post.category.replaceAll("_", " ")),
                onTap: () => context.push("/intelligence/${post.slug}"),
              ),
            );
          },
        );
      },
    );
  }
}

final _companyJobsProvider = FutureProvider.autoDispose.family<List<JobCard>, String>((ref, companyId) async {
  final result = await ref.watch(jobRepositoryProvider).listByCompany(companyId);
  return result.items;
});

final _companyNewsProvider = FutureProvider.autoDispose.family<List<IntelligenceCard>, String>((ref, companyId) async {
  final result = await ref.watch(intelligenceRepositoryProvider).listByCompany(companyId);
  return result.items;
});
