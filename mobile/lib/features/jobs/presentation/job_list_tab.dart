import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/monetization/ad_placement.dart";
import "../../../core/monetization/feed_ad_interval.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/monetization/widgets/banner_ad_slot.dart";
import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
import "../data/job_models.dart";
import "job_card.dart";
import "job_providers.dart";

const _employmentTypes = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"];
const _workModes = ["ON_SITE", "REMOTE", "HYBRID"];

class JobListTab extends ConsumerStatefulWidget {
  const JobListTab({super.key});

  @override
  ConsumerState<JobListTab> createState() => _JobListTabState();
}

class _JobListTabState extends ConsumerState<JobListTab> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels > _scrollController.position.maxScrollExtent - 200) {
        ref.read(jobListProvider.notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _submitSearch(String value) {
    final filters = ref.read(jobListProvider).filters;
    ref.read(jobListProvider.notifier).updateFilters(filters.copyWith(search: value));
  }

  void _toggleFilter({String? employmentType, String? workMode}) {
    final current = ref.read(jobListProvider).filters;
    final controller = ref.read(jobListProvider.notifier);
    if (employmentType != null) {
      controller.updateFilters(
        current.copyWith(employmentType: current.employmentType == employmentType ? "" : employmentType),
      );
    } else if (workMode != null) {
      controller.updateFilters(current.copyWith(workMode: current.workMode == workMode ? "" : workMode));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(jobListProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _searchController,
            onSubmitted: _submitSearch,
            decoration: InputDecoration(
              hintText: "Search roles, companies or skills",
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () {
                        _searchController.clear();
                        _submitSearch("");
                      },
                    )
                  : null,
            ),
          ),
        ),
        SizedBox(
          height: 40,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              for (final type in _employmentTypes)
                _FilterChip(
                  label: type.replaceAll("_", " "),
                  selected: state.filters.employmentType == type,
                  onTap: () => _toggleFilter(employmentType: type),
                ),
              for (final mode in _workModes)
                _FilterChip(
                  label: mode.replaceAll("_", " "),
                  selected: state.filters.workMode == mode,
                  onTap: () => _toggleFilter(workMode: mode),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(child: _JobListBody(state: state, scrollController: _scrollController)),
      ],
    );
  }
}

class _JobListBody extends ConsumerWidget {
  const _JobListBody({required this.state, required this.scrollController});

  final JobListState state;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (state.isLoading && state.items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.wifi_off_rounded, size: 48, color: AppColors.muted),
              const SizedBox(height: 12),
              Text(state.error!.userMessage, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.read(jobListProvider.notifier).refresh(),
                child: const Text("Retry"),
              ),
            ],
          ),
        ),
      );
    }

    if (state.items.isEmpty) {
      return const PhasePendingPlaceholder(
        icon: Icons.work_outline_rounded,
        title: "No jobs found",
        message: "Try adjusting your search or filters.",
      );
    }

    // Ad slots (spec §12): inserted at a configurable interval, never before Pro users, never
    // when ads/banners are globally disabled. Failure of any single slot to load is handled
    // entirely inside BannerAdSlot (collapses to nothing) — this list never has to know.
    final config = ref.watch(monetizationConfigProvider).valueOrNull;
    final isPro = ref.watch(entitlementProvider).valueOrNull?.isPro ?? false;
    final showAds = config != null && config.adsEnabled && config.bannerAdsEnabled && !isPro;
    final adAfterPositions = showAds
        ? adSlotPositionsForFeed(itemCount: state.items.length, interval: config.feedAdInterval).toSet()
        : const <int>{};

    final rows = <_FeedRow>[];
    for (var i = 0; i < state.items.length; i++) {
      rows.add(_FeedRow.item(state.items[i]));
      if (adAfterPositions.contains(i + 1)) rows.add(const _FeedRow.ad());
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(jobListProvider.notifier).refresh(),
      child: ListView.separated(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        itemCount: rows.length + (state.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index >= rows.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          final row = rows[index];
          if (row.isAd) return const BannerAdSlot(placement: AdPlacement.jobsFeed);
          final job = row.job!;
          return JobCardTile(
            job: job,
            onTap: () => context.push("/jobs/${job.slug}"),
            onToggleSave: () => ref.read(jobListProvider.notifier).toggleSave(job.id),
          );
        },
      ),
    );
  }
}

class _FeedRow {
  const _FeedRow.item(this.job) : isAd = false;
  const _FeedRow.ad()
      : job = null,
        isAd = true;

  final JobCard? job;
  final bool isAd;
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label, style: const TextStyle(fontSize: 12)),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: AppColors.blue.withValues(alpha: 0.15),
        labelStyle: TextStyle(color: selected ? AppColors.blue : AppColors.text),
        side: BorderSide(color: selected ? AppColors.blue : AppColors.muted.withValues(alpha: 0.3)),
      ),
    );
  }
}
