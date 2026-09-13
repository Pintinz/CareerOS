import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/scholarship_repository.dart";
import "scholarship_card.dart";
import "scholarship_providers.dart";

const _fundingTypes = ["FULLY_FUNDED", "PARTIAL"];
const _degreeLevels = ["UNDERGRADUATE", "MASTERS", "PHD", "OTHER"];

class ScholarshipListTab extends ConsumerStatefulWidget {
  const ScholarshipListTab({super.key});

  @override
  ConsumerState<ScholarshipListTab> createState() => _ScholarshipListTabState();
}

class _ScholarshipListTabState extends ConsumerState<ScholarshipListTab> with AutomaticKeepAliveClientMixin {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels > _scrollController.position.maxScrollExtent - 200) {
        ref.read(scholarshipListProvider.notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  ScholarshipListController get _controller => ref.read(scholarshipListProvider.notifier);

  void _submitSearch(String value) {
    _controller.updateFilters(ref.read(scholarshipListProvider).filters.copyWith(search: value));
  }

  void _openFilters() {
    showCareerBottomSheet<void>(
      context: context,
      title: "Filters",
      builder: (sheetContext) => Consumer(
        builder: (context, ref, _) {
          final filters = ref.watch(scholarshipListProvider).filters;
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                FilterOptionGroup(
                  title: "Funding",
                  options: _fundingTypes,
                  selected: filters.fundingType,
                  labelFor: humanizeEnum,
                  onChanged: (v) => _controller.updateFilters(filters.copyWith(fundingType: v)),
                ),
                FilterOptionGroup(
                  title: "Degree level",
                  options: _degreeLevels,
                  selected: filters.degreeLevel,
                  labelFor: humanizeEnum,
                  onChanged: (v) => _controller.updateFilters(filters.copyWith(degreeLevel: v)),
                ),
                Row(
                  children: [
                    Expanded(
                      child: AppOutlineButton(
                        label: "Clear all",
                        onPressed: () => _controller.updateFilters(ScholarshipFilters(search: filters.search)),
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
    final state = ref.watch(scholarshipListProvider);
    final filters = state.filters;

    return Column(
      children: [
        FeedToolbar(
          searchHint: "Search scholarships or providers",
          searchController: _searchController,
          onSearchSubmitted: _submitSearch,
          onOpenFilters: _openFilters,
          activeFilterCount: filters.activeRefinementCount,
          quickFilters: [
            AppFilterChip(
              label: "Fully funded",
              selected: filters.fundingType == "FULLY_FUNDED",
              onSelected: (on) => _controller.updateFilters(filters.copyWith(fundingType: on ? "FULLY_FUNDED" : "")),
            ),
            for (final level in const ["MASTERS", "PHD", "UNDERGRADUATE"])
              AppFilterChip(
                label: humanizeEnum(level),
                selected: filters.degreeLevel == level,
                onSelected: (on) => _controller.updateFilters(filters.copyWith(degreeLevel: on ? level : "")),
              ),
          ],
        ),
        Expanded(
          child: _ScholarshipListBody(
            state: state,
            scrollController: _scrollController,
            onClearFilters: () {
              _searchController.clear();
              _controller.updateFilters(const ScholarshipFilters());
            },
          ),
        ),
      ],
    );
  }
}

class _ScholarshipListBody extends ConsumerWidget {
  const _ScholarshipListBody({required this.state, required this.scrollController, required this.onClearFilters});

  final ScholarshipListState state;
  final ScrollController scrollController;
  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(scholarshipListProvider.notifier);

    if (state.isLoading && state.items.isEmpty) {
      return const SkeletonList(padding: EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl));
    }

    if (state.error != null && state.items.isEmpty) {
      return ErrorState(
        title: "We couldn't load scholarships",
        message: state.error!.userMessage,
        onRetry: controller.refresh,
      );
    }

    if (state.items.isEmpty) {
      return RefreshIndicator(
        onRefresh: controller.refresh,
        child: ListView(
          children: [
            state.filters.isEmpty
                ? const EmptyState(
                    icon: AppIcons.scholarship,
                    title: "No scholarships right now",
                    message: "New scholarships appear here as soon as they're published. Pull down to refresh.",
                  )
                : EmptyState(
                    icon: AppIcons.search,
                    title: "No matches for these filters",
                    message: "Try removing a filter or searching a broader term.",
                    actionLabel: "Clear Filters",
                    onAction: onClearFilters,
                  ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView.separated(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl),
        itemCount: state.items.length + 1 + (state.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => Gap.sm,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Text(
              state.total == 1 ? "1 scholarship" : "${state.total} scholarships",
              style: context.text.labelMedium,
            );
          }
          final itemIndex = index - 1;
          if (itemIndex >= state.items.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: SizedBox.square(dimension: 24, child: CircularProgressIndicator(strokeWidth: 2.4))),
            );
          }
          final scholarship = state.items[itemIndex];
          return ScholarshipCardTile(
            scholarship: scholarship,
            onTap: () => context.push("/scholarships/${scholarship.slug}"),
            onToggleSave: () => controller.toggleSave(scholarship.id),
          );
        },
      ),
    );
  }
}
