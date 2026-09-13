import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../data/application_models.dart";
import "application_card.dart";
import "application_providers.dart";
import "stage_badge.dart";

/// Stages offered as quick filters — the rest are one tap away in the "All stages" sheet.
const _quickStages = [
  ApplicationStage.applied,
  ApplicationStage.shortlisted,
  ApplicationStage.aptitudeTest,
  ApplicationStage.interview,
  ApplicationStage.offer,
  ApplicationStage.rejected,
];

/// Application tracker — a career CRM for every role the user is pursuing.
class ApplicationListScreen extends ConsumerWidget {
  const ApplicationListScreen({super.key});

  void _openStageSheet(BuildContext context, WidgetRef ref, ApplicationStage? current) {
    showCareerBottomSheet<void>(
      context: context,
      title: "Filter by stage",
      builder: (sheetContext) => SingleChildScrollView(
        child: Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: [
            for (final stage in ApplicationStage.values)
              ChoiceChip(
                avatar: Icon(stageIcon(stage), size: 16, color: stageTone(stage).color(sheetContext)),
                label: Text(stage.label),
                selected: current == stage,
                onSelected: (_) {
                  ref.read(applicationListProvider.notifier).setStageFilter(current == stage ? null : stage);
                  Navigator.of(sheetContext).pop();
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(applicationListProvider);
    final controller = ref.read(applicationListProvider.notifier);
    final filter = state.stageFilter;
    final filterIsQuick = filter == null || _quickStages.contains(filter);

    return Scaffold(
      appBar: AppBar(title: const Text("My Applications")),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push("/applications/new"),
        icon: const Icon(AppIcons.add),
        label: const Text("Track Application"),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FeedToolbar(
            onOpenFilters: () => _openStageSheet(context, ref, filter),
            activeFilterCount: filterIsQuick ? 0 : 1,
            quickFilters: [
              AppFilterChip(label: "All", selected: filter == null, onSelected: (_) => controller.setStageFilter(null)),
              for (final stage in _quickStages)
                AppFilterChip(
                  label: stage.label,
                  selected: filter == stage,
                  onSelected: (on) => controller.setStageFilter(on ? stage : null),
                ),
              if (!filterIsQuick) AppFilterChip(label: filter.label, selected: true, onSelected: (_) => controller.setStageFilter(null)),
            ],
          ),
          Expanded(child: _Body(state: state)),
        ],
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.state});

  final ApplicationListState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(applicationListProvider.notifier);

    if (state.isLoading && state.items.isEmpty) {
      return const SkeletonList(padding: EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, AppSpacing.xl));
    }

    if (state.error != null && state.items.isEmpty) {
      return ErrorState(title: "We couldn't load your applications", message: state.error!.userMessage, onRetry: controller.refresh);
    }

    if (state.items.isEmpty) {
      return RefreshIndicator(
        onRefresh: controller.refresh,
        child: ListView(
          children: [
            if (state.stageFilter != null)
              EmptyState(
                icon: stageIcon(state.stageFilter!),
                title: "No applications at ${state.stageFilter!.label}",
                message: "Applications you move to this stage will show up here.",
                actionLabel: "Show All",
                onAction: () => controller.setStageFilter(null),
              )
            else
              EmptyState(
                icon: AppIcons.application,
                title: "No applications yet",
                message: "Track a job you've applied for and CareerOS will help you follow every stage.",
                actionLabel: "Find Opportunities",
                onAction: () => context.go("/home?tab=opportunities"),
              ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.xs, AppSpacing.pageH, 96),
        itemCount: state.items.length + 1,
        separatorBuilder: (context, index) => Gap.sm,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Text(state.total == 1 ? "1 application" : "${state.total} applications", style: context.text.labelMedium);
          }
          return ApplicationCardTile(application: state.items[index - 1]);
        },
      ),
    );
  }
}
