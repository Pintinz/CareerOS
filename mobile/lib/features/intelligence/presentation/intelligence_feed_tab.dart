import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "intelligence_card.dart";
import "intelligence_providers.dart";

/// Categories surfaced as quick filters — a subset of the backend's IntelligenceCategory enum,
/// ordered by how often candidates act on them.
const _categories = [
  "HIRING",
  "TECHNOLOGY",
  "GRADUATE_RECRUITMENT",
  "LEADERSHIP",
  "INVESTMENTS",
  "PROJECTS",
  "ACQUISITION",
  "AI",
];

/// Intelligence hub — "What should I know about companies and careers?". Company intelligence,
/// not generic news.
class IntelligenceFeedTab extends ConsumerStatefulWidget {
  const IntelligenceFeedTab({super.key});

  @override
  ConsumerState<IntelligenceFeedTab> createState() => _IntelligenceFeedTabState();
}

class _IntelligenceFeedTabState extends ConsumerState<IntelligenceFeedTab> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels > _scrollController.position.maxScrollExtent - 200) {
        ref.read(intelligenceListProvider.notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(intelligenceListProvider);
    final controller = ref.read(intelligenceListProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, 0),
          child: HubHeader(title: "Intelligence", subtitle: "Company moves that shape your opportunities"),
        ),
        FeedToolbar(
          quickFilters: [
            AppFilterChip(
              label: "Following",
              icon: Icons.star_outline_rounded,
              selected: state.followedOnly,
              onSelected: (_) => controller.setFollowedOnly(!state.followedOnly),
            ),
            for (final category in _categories)
              AppFilterChip(
                label: humanizeEnum(category),
                selected: state.category == category,
                onSelected: (_) => controller.setCategory(state.category == category ? null : category),
              ),
          ],
        ),
        Expanded(child: _FeedBody(state: state, scrollController: _scrollController)),
      ],
    );
  }
}

class _FeedBody extends ConsumerWidget {
  const _FeedBody({required this.state, required this.scrollController});

  final IntelligenceListState state;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(intelligenceListProvider.notifier);

    if (state.isLoading && state.items.isEmpty) {
      return const SkeletonList(padding: EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl));
    }

    if (state.error != null && state.items.isEmpty) {
      return ErrorState(
        title: "We couldn't load company intelligence",
        message: state.error!.userMessage,
        onRetry: controller.refresh,
      );
    }

    if (state.items.isEmpty) {
      return RefreshIndicator(
        onRefresh: controller.refresh,
        child: ListView(
          children: [
            if (state.followedOnly)
              const EmptyState(
                icon: Icons.star_outline_rounded,
                title: "Nothing from companies you follow yet",
                message: "Follow companies from their profile to see their hiring, projects and leadership news here.",
              )
            else if (state.category != null)
              EmptyState(
                icon: AppIcons.intelligence,
                title: "No ${humanizeEnum(state.category!).toLowerCase()} updates yet",
                message: "Try another category, or check back soon.",
                actionLabel: "Show All",
                onAction: () => controller.setCategory(null),
              )
            else
              const EmptyState(
                icon: AppIcons.intelligence,
                title: "No company intelligence yet",
                message: "Verified company updates appear here as soon as they're published. Pull down to refresh.",
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
        itemCount: state.items.length + (state.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => Gap.sm,
        itemBuilder: (context, index) {
          if (index >= state.items.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: SizedBox.square(dimension: 24, child: CircularProgressIndicator(strokeWidth: 2.4))),
            );
          }
          return IntelligenceCardTile(post: state.items[index]);
        },
      ),
    );
  }
}
