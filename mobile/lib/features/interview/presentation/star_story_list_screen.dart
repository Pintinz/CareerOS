import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/utils/error_message.dart";
import "../../../theme/app_colors.dart";
import "interview_providers.dart";

class StarStoryListScreen extends ConsumerWidget {
  const StarStoryListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final storiesAsync = ref.watch(starStoriesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("STAR Stories")),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push("/prepare/interview/star-stories/new"),
        child: const Icon(Icons.add),
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(starStoriesProvider),
        child: storiesAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text(e.userMessage)),
          data: (stories) {
            if (stories.isEmpty) {
              return ListView(
                padding: const EdgeInsets.all(32),
                children: const [
                  SizedBox(height: 80),
                  Icon(Icons.auto_stories_outlined, size: 48, color: AppColors.muted),
                  SizedBox(height: 16),
                  Text(
                    "No STAR stories yet. Build a reusable bank of Situation/Task/Action/Result "
                    "stories to draw on during behavioral interviews.",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.muted),
                  ),
                ],
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.all(20),
              itemCount: stories.length,
              itemBuilder: (context, index) {
                final story = stories[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    onTap: () => context.push("/prepare/interview/star-stories/${story.id}"),
                    title: Text(story.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(story.category.label),
                    trailing: Icon(
                      story.completeness.isComplete ? Icons.check_circle : Icons.warning_amber_rounded,
                      color: story.completeness.isComplete ? AppColors.success : AppColors.warning,
                    ),
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
