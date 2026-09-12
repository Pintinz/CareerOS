import "package:cached_network_image/cached_network_image.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
import "../data/intelligence_models.dart";
import "intelligence_providers.dart";

const _categories = [
  "TECHNOLOGY",
  "AUTOMATION",
  "HIRING",
  "GRADUATE_RECRUITMENT",
  "INVESTMENTS",
  "LEADERSHIP",
  "ACQUISITION",
];

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

    return Column(
      children: [
        SizedBox(
          height: 40,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            children: [
              _FilterChip(
                label: "Following",
                selected: state.followedOnly,
                onTap: () => ref.read(intelligenceListProvider.notifier).setFollowedOnly(!state.followedOnly),
              ),
              for (final category in _categories)
                _FilterChip(
                  label: category.replaceAll("_", " "),
                  selected: state.category == category,
                  onTap: () => ref
                      .read(intelligenceListProvider.notifier)
                      .setCategory(state.category == category ? null : category),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
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
                onPressed: () => ref.read(intelligenceListProvider.notifier).refresh(),
                child: const Text("Retry"),
              ),
            ],
          ),
        ),
      );
    }

    if (state.items.isEmpty) {
      return PhasePendingPlaceholder(
        icon: Icons.newspaper_outlined,
        title: state.followedOnly ? "No news from companies you follow" : "No news found",
        message: state.followedOnly
            ? "Follow companies from their profile page to see their updates here."
            : "Try a different category.",
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(intelligenceListProvider.notifier).refresh(),
      child: ListView.separated(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        itemCount: state.items.length + (state.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index >= state.items.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          return _IntelligenceCardTile(post: state.items[index]);
        },
      ),
    );
  }
}

class _IntelligenceCardTile extends StatelessWidget {
  const _IntelligenceCardTile({required this.post});

  final IntelligenceCard post;

  static final _timeFormat = DateFormat("MMM d");

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push("/intelligence/${post.slug}"),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (post.thumbnailUrl != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: CachedNetworkImage(
                    imageUrl: post.thumbnailUrl!,
                    width: 56,
                    height: 56,
                    fit: BoxFit.cover,
                    errorWidget: (context, url, error) => const SizedBox(width: 56, height: 56),
                  ),
                )
              else
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: AppColors.purple.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.newspaper_outlined, color: AppColors.purple),
                ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.purple.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        post.category.replaceAll("_", " "),
                        style: const TextStyle(fontSize: 10, color: AppColors.purple, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(post.headline, style: Theme.of(context).textTheme.titleLarge, maxLines: 2, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        if (post.company != null) Text(post.company!.name, style: Theme.of(context).textTheme.bodyMedium),
                        if (post.company != null && post.publishedAt != null) const Text("  ·  ", style: TextStyle(color: AppColors.muted)),
                        if (post.publishedAt != null)
                          Text(_timeFormat.format(post.publishedAt!), style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
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
        selectedColor: AppColors.purple.withValues(alpha: 0.15),
        labelStyle: TextStyle(color: selected ? AppColors.purple : AppColors.text),
        side: BorderSide(color: selected ? AppColors.purple : AppColors.muted.withValues(alpha: 0.3)),
      ),
    );
  }
}
