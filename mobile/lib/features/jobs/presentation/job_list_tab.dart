import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/monetization/ad_placement.dart";
import "../../../core/monetization/feed_ad_interval.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/monetization/widgets/banner_ad_slot.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/job_models.dart";
import "../data/job_repository.dart";
import "job_card.dart";
import "job_providers.dart";

const _employmentTypes = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP", "TEMPORARY"];
const _workModes = ["REMOTE", "HYBRID", "ON_SITE"];
const _experienceLevels = ["ENTRY", "JUNIOR", "MID", "SENIOR", "LEAD", "EXECUTIVE"];

/// A job-backed Opportunities feed (Jobs, Internships or Entry Level — see [JobFeed]).
class JobListTab extends ConsumerStatefulWidget {
  const JobListTab({super.key, this.feed = JobFeed.all});

  final JobFeed feed;

  @override
  ConsumerState<JobListTab> createState() => _JobListTabState();
}

class _JobListTabState extends ConsumerState<JobListTab> with AutomaticKeepAliveClientMixin {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels > _scrollController.position.maxScrollExtent - 200) {
        ref.read(jobFeedProvider(widget.feed).notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  JobListController get _controller => ref.read(jobFeedProvider(widget.feed).notifier);
  JobFilters get _filters => ref.read(jobFeedProvider(widget.feed)).filters;

  void _submitSearch(String value) => _controller.updateFilters(_filters.copyWith(search: value));

  String get _searchHint => switch (widget.feed) {
        JobFeed.all => "Search roles, companies or skills",
        JobFeed.internships => "Search internships",
        JobFeed.entryLevel => "Search entry-level roles",
      };

  void _openFilters() {
    showCareerBottomSheet<void>(
      context: context,
      title: "Filters",
      builder: (sheetContext) => Consumer(
        builder: (context, ref, _) {
          final filters = ref.watch(jobFeedProvider(widget.feed)).filters;
          void update(JobFilters next) => _controller.updateFilters(next);
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                FilterOptionGroup(
                  title: "Sort by",
                  options: const ["newest", "deadline"],
                  selected: filters.sort,
                  labelFor: (v) => v == "newest" ? "Latest" : "Closing soon",
                  onChanged: (v) => update(filters.copyWith(sort: v.isEmpty ? "newest" : v)),
                ),
                FilterOptionGroup(
                  title: "Work mode",
                  options: _workModes,
                  selected: filters.workMode,
                  labelFor: humanizeEnum,
                  onChanged: (v) => update(filters.copyWith(workMode: v)),
                ),
                if (widget.feed != JobFeed.internships)
                  FilterOptionGroup(
                    title: "Employment type",
                    options: _employmentTypes,
                    selected: filters.employmentType,
                    labelFor: humanizeEnum,
                    onChanged: (v) => update(filters.copyWith(employmentType: v)),
                  ),
                if (widget.feed != JobFeed.entryLevel)
                  FilterOptionGroup(
                    title: "Experience level",
                    options: _experienceLevels,
                    selected: filters.experienceLevel,
                    labelFor: humanizeEnum,
                    onChanged: (v) => update(filters.copyWith(experienceLevel: v)),
                  ),
                Row(
                  children: [
                    Expanded(
                      child: AppOutlineButton(
                        label: "Clear all",
                        onPressed: () => update(JobFilters(search: filters.search)),
                      ),
                    ),
                    Gap.sm,
                    Expanded(child: PrimaryButton(label: "Show results", onPressed: () => Navigator.of(sheetContext).pop())),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final state = ref.watch(jobFeedProvider(widget.feed));
    final filters = state.filters;

    return Column(
      children: [
        FeedToolbar(
          searchHint: _searchHint,
          searchController: _searchController,
          onSearchSubmitted: _submitSearch,
          onOpenFilters: _openFilters,
          activeFilterCount: filters.activeRefinementCount,
          quickFilters: [
            AppFilterChip(
              label: "Closing soon",
              selected: filters.sort == "deadline",
              onSelected: (on) => _controller.updateFilters(filters.copyWith(sort: on ? "deadline" : "newest")),
            ),
            for (final mode in _workModes)
              AppFilterChip(
                label: humanizeEnum(mode),
                selected: filters.workMode == mode,
                onSelected: (on) => _controller.updateFilters(filters.copyWith(workMode: on ? mode : "")),
              ),
          ],
        ),
        Expanded(
          child: _JobListBody(
            feed: widget.feed,
            state: state,
            scrollController: _scrollController,
            onClearFilters: () {
              _searchController.clear();
              _controller.updateFilters(const JobFilters());
            },
          ),
        ),
      ],
    );
  }
}

class _JobListBody extends ConsumerWidget {
  const _JobListBody({required this.feed, required this.state, required this.scrollController, required this.onClearFilters});

  final JobFeed feed;
  final JobListState state;
  final ScrollController scrollController;
  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(jobFeedProvider(feed).notifier);

    if (state.isLoading && state.items.isEmpty) {
      return const SkeletonList(padding: EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl));
    }

    if (state.error != null && state.items.isEmpty) {
      return ErrorState(
        title: "We couldn't load opportunities",
        message: state.error!.userMessage,
        onRetry: controller.refresh,
      );
    }

    if (state.items.isEmpty) {
      final filtered = !state.filters.isEmpty || state.filters.sort != "newest";
      return RefreshIndicator(
        onRefresh: controller.refresh,
        child: ListView(
          children: [
            filtered
                ? EmptyState(
                    icon: AppIcons.search,
                    title: "No matches for these filters",
                    message: "Try removing a filter or searching a broader term.",
                    actionLabel: "Clear Filters",
                    onAction: onClearFilters,
                  )
                : EmptyState(
                    icon: feed == JobFeed.internships ? AppIcons.internship : AppIcons.job,
                    title: switch (feed) {
                      JobFeed.all => "No jobs published yet",
                      JobFeed.internships => "No internships right now",
                      JobFeed.entryLevel => "No entry-level roles right now",
                    },
                    message: "New opportunities appear here as soon as they're published. Pull down to refresh.",
                  ),
          ],
        ),
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
      onRefresh: controller.refresh,
      child: ListView.separated(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl),
        itemCount: rows.length + 1 + (state.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => Gap.sm,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Text(
              state.total == 1 ? "1 opportunity" : "${state.total} opportunities",
              style: context.text.labelMedium,
            );
          }
          final rowIndex = index - 1;
          if (rowIndex >= rows.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: SizedBox.square(dimension: 24, child: CircularProgressIndicator(strokeWidth: 2.4))),
            );
          }
          final row = rows[rowIndex];
          if (row.isAd) return const BannerAdSlot(placement: AdPlacement.jobsFeed);
          final job = row.job!;
          return JobCardTile(
            job: job,
            onTap: () => context.push("/jobs/${job.slug}"),
            onToggleSave: () => controller.toggleSave(job.id),
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
