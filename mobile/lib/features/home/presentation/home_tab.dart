import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../profile/presentation/profile_providers.dart";

/// Home dashboard (master spec §11). Only the greeting header is wired to real data in this
/// phase — Career Readiness Score, match cards, and the daily career brief depend on the
/// jobs/scholarships/ATS/application data models built in Phases 2-5 and are not faked here.
class HomeTab extends ConsumerWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(userProfileProvider);

    return RefreshIndicator(
      onRefresh: () => ref.refresh(userProfileProvider.future),
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          profileAsync.when(
            loading: () => const _GreetingSkeleton(),
            error: (error, _) => Text(
              "Good day.",
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            data: (profile) {
              final firstName = (profile.fullName ?? "").split(" ").firstOrNull;
              return Text(
                firstName == null || firstName.isEmpty ? "Good day." : "Good day, $firstName",
                style: Theme.of(context).textTheme.headlineMedium,
              );
            },
          ),
          const SizedBox(height: 4),
          Text(
            "Let's make progress today.",
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 32),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Career Readiness Score", style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  Text(
                    "Available once your profile, CV and preferences are complete "
                    "(Phases 1-3).",
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GreetingSkeleton extends StatelessWidget {
  const _GreetingSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 180,
      height: 28,
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}

extension _FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
