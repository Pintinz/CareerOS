import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "../../../widgets/phase_pending_placeholder.dart";
import "../data/application_models.dart";
import "application_providers.dart";
import "stage_badge.dart";

class ApplicationListScreen extends ConsumerWidget {
  const ApplicationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(applicationListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("My Applications")),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push("/applications/new"),
        icon: const Icon(Icons.add),
        label: const Text("Add"),
      ),
      body: Column(
        children: [
          SizedBox(
            height: 40,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              children: [
                _FilterChip(
                  label: "All",
                  selected: state.stageFilter == null,
                  onTap: () => ref.read(applicationListProvider.notifier).setStageFilter(null),
                ),
                for (final stage in ApplicationStage.values)
                  _FilterChip(
                    label: stage.label,
                    selected: state.stageFilter == stage,
                    onTap: () => ref.read(applicationListProvider.notifier).setStageFilter(stage),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),
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
              Text(state.error!.userMessage, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.read(applicationListProvider.notifier).refresh(),
                child: const Text("Retry"),
              ),
            ],
          ),
        ),
      );
    }

    if (state.items.isEmpty) {
      return const PhasePendingPlaceholder(
        icon: Icons.timeline_outlined,
        title: "No applications tracked yet",
        message: 'Tap "Add" to track one manually, or use "Track Application" from a job\'s detail page.',
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(applicationListProvider.notifier).refresh(),
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 80),
        itemCount: state.items.length,
        separatorBuilder: (context, index) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final application = state.items[index];
          return _ApplicationCard(application: application);
        },
      ),
    );
  }
}

class _ApplicationCard extends StatelessWidget {
  const _ApplicationCard({required this.application});

  final Application application;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push("/applications/${application.id}"),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(application.roleTitle, style: Theme.of(context).textTheme.titleLarge),
                        Text(application.companyName, style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ),
                  StageBadge(stage: application.currentStage),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                "Updated ${DateFormat.yMMMd().format(application.updatedAt)}",
                style: const TextStyle(fontSize: 12, color: AppColors.muted),
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
        selectedColor: AppColors.blue.withValues(alpha: 0.15),
        labelStyle: TextStyle(color: selected ? AppColors.blue : AppColors.text),
        side: BorderSide(color: selected ? AppColors.blue : AppColors.muted.withValues(alpha: 0.3)),
      ),
    );
  }
}
