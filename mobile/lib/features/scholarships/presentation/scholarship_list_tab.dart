import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
import "scholarship_card.dart";
import "scholarship_providers.dart";

const _fundingTypes = ["FULLY_FUNDED", "PARTIAL"];
const _degreeLevels = ["UNDERGRADUATE", "MASTERS", "PHD"];

class ScholarshipListTab extends ConsumerStatefulWidget {
  const ScholarshipListTab({super.key});

  @override
  ConsumerState<ScholarshipListTab> createState() => _ScholarshipListTabState();
}

class _ScholarshipListTabState extends ConsumerState<ScholarshipListTab> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

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

  void _submitSearch(String value) {
    final filters = ref.read(scholarshipListProvider).filters;
    ref.read(scholarshipListProvider.notifier).updateFilters(filters.copyWith(search: value));
  }

  void _toggleFilter({String? fundingType, String? degreeLevel}) {
    final current = ref.read(scholarshipListProvider).filters;
    final controller = ref.read(scholarshipListProvider.notifier);
    if (fundingType != null) {
      controller.updateFilters(current.copyWith(fundingType: current.fundingType == fundingType ? "" : fundingType));
    } else if (degreeLevel != null) {
      controller.updateFilters(current.copyWith(degreeLevel: current.degreeLevel == degreeLevel ? "" : degreeLevel));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(scholarshipListProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _searchController,
            onSubmitted: _submitSearch,
            decoration: const InputDecoration(hintText: "Search scholarships", prefixIcon: Icon(Icons.search)),
          ),
        ),
        SizedBox(
          height: 40,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              for (final type in _fundingTypes)
                _FilterChip(
                  label: type.replaceAll("_", " "),
                  selected: state.filters.fundingType == type,
                  onTap: () => _toggleFilter(fundingType: type),
                ),
              for (final level in _degreeLevels)
                _FilterChip(
                  label: level,
                  selected: state.filters.degreeLevel == level,
                  onTap: () => _toggleFilter(degreeLevel: level),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(child: _ScholarshipListBody(state: state, scrollController: _scrollController)),
      ],
    );
  }
}

class _ScholarshipListBody extends ConsumerWidget {
  const _ScholarshipListBody({required this.state, required this.scrollController});

  final ScholarshipListState state;
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
                onPressed: () => ref.read(scholarshipListProvider.notifier).refresh(),
                child: const Text("Retry"),
              ),
            ],
          ),
        ),
      );
    }

    if (state.items.isEmpty) {
      return const PhasePendingPlaceholder(
        icon: Icons.school_outlined,
        title: "No scholarships found",
        message: "Try adjusting your search or filters.",
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(scholarshipListProvider.notifier).refresh(),
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
          final scholarship = state.items[index];
          return ScholarshipCardTile(
            scholarship: scholarship,
            onTap: () => context.push("/scholarships/${scholarship.slug}"),
            onToggleSave: () => ref.read(scholarshipListProvider.notifier).toggleSave(scholarship.id),
          );
        },
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
        selectedColor: AppColors.blue.withValues(alpha: 0.15),
        labelStyle: TextStyle(color: selected ? AppColors.blue : AppColors.text),
        side: BorderSide(color: selected ? AppColors.blue : AppColors.muted.withValues(alpha: 0.3)),
      ),
    );
  }
}
