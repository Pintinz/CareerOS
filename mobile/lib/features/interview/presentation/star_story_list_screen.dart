import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "interview_providers.dart";

class StarStoryListScreen extends ConsumerWidget {
  const StarStoryListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final storiesAsync = ref.watch(starStoriesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("STAR Stories")),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push("/prepare/interview/star-stories/new"),
        icon: const Icon(AppIcons.add),
        label: const Text("New Story"),
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(starStoriesProvider),
        child: storiesAsync.when(
          loading: () => const SkeletonList(),
          error: (e, _) => ErrorState(
            title: "We couldn't load your stories",
            message: e.userMessage,
            onRetry: () => ref.invalidate(starStoriesProvider),
          ),
          data: (stories) {
            if (stories.isEmpty) {
              return ListView(
                children: [
                  EmptyState(
                    icon: AppIcons.starStory,
                    title: "No STAR stories yet",
                    message:
                        "Build a reusable bank of Situation/Task/Action/Result stories to draw on during behavioral interviews.",
                    actionLabel: "Write Your First Story",
                    onAction: () => context.push("/prepare/interview/star-stories/new"),
                  ),
                ],
              );
            }
            final ready = stories.where((s) => s.completeness.isComplete).length;
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.md, AppSpacing.pageH, 96),
              itemCount: stories.length + 1,
              separatorBuilder: (_, __) => Gap.sm,
              itemBuilder: (context, index) {
                if (index == 0) {
                  return Text("$ready of ${stories.length} stories complete", style: context.text.labelMedium);
                }
                final story = stories[index - 1];
                final complete = story.completeness.isComplete;
                return CareerCard(
                  onTap: () => context.push("/prepare/interview/star-stories/${story.id}"),
                  child: Row(
                    children: [
                      IconTile(icon: AppIcons.starStory, tone: complete ? AppTone.success : AppTone.warning, size: 44),
                      Gap.sm,
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(story.title, style: context.text.titleMedium, maxLines: 2, overflow: TextOverflow.ellipsis),
                            const SizedBox(height: 2),
                            Text(
                              "${story.category.label} · Updated ${DateLabels.published(story.updatedAt).toLowerCase()}",
                              style: context.text.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      Gap.xs,
                      Semantics(
                        label: complete ? "Complete" : "Needs work",
                        child: Icon(
                          complete ? Icons.check_circle : Icons.warning_amber_rounded,
                          color: complete ? AppColors.success : AppColors.warning,
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
