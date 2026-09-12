import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../theme/app_colors.dart";
import "../../auth/presentation/auth_controller.dart";
import "profile_providers.dart";

class ProfileTab extends ConsumerWidget {
  const ProfileTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(currentUserProvider);
    final profileAsync = ref.watch(userProfileProvider);

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Row(
          children: [
            const CircleAvatar(
              radius: 32,
              backgroundColor: AppColors.blue,
              child: Icon(Icons.person, color: Colors.white, size: 32),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  profileAsync.when(
                    loading: () => const Text("Loading..."),
                    error: (_, __) => const Text("Unable to load profile"),
                    data: (profile) => Text(
                      (profile.fullName?.isNotEmpty ?? false) ? profile.fullName! : "Add your name",
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  userAsync.when(
                    loading: () => const SizedBox.shrink(),
                    error: (_, __) => const SizedBox.shrink(),
                    data: (user) => Text(user.email, style: Theme.of(context).textTheme.bodyMedium),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),
        _ProfileMenuItem(
          icon: Icons.bookmark_border,
          label: "Saved Jobs & Scholarships",
          onTap: () => context.push("/saved"),
        ),
        _ProfileMenuItem(
          icon: Icons.description_outlined,
          label: "CVs & ATS Analysis",
          onTap: () => context.push("/ats/analyze"),
        ),
        const _ProfileMenuItem(icon: Icons.tune_rounded, label: "Career Preferences"),
        const _ProfileMenuItem(icon: Icons.notifications_outlined, label: "Notifications"),
        const _ProfileMenuItem(icon: Icons.settings_outlined, label: "Settings"),
        const SizedBox(height: 24),
        OutlinedButton(
          onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
          child: const Text("Log Out"),
        ),
      ],
    );
  }
}

class _ProfileMenuItem extends StatelessWidget {
  const _ProfileMenuItem({required this.icon, required this.label, this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Icon(icon, color: AppColors.blue),
        title: Text(label),
        trailing: const Icon(Icons.chevron_right, color: AppColors.muted),
        onTap: onTap, // null until that destination's phase is built
      ),
    );
  }
}
