import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/design/theme_mode_controller.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
import "../../auth/presentation/auth_controller.dart";
import "../../profile/presentation/profile_providers.dart";

/// Settings, grouped by intent. Only settings that are actually built appear — no dead rows.
/// Log out and Delete Account are separated at the bottom.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showCareerDialog(
      context: context,
      title: "Delete your account?",
      message:
          "This permanently deletes your CareerOS account and everything in it — profile, CVs, applications, "
          "practice history, STAR stories and saved items. This can't be undone.",
      confirmLabel: "Delete Account",
      destructive: true,
    );
    if (!confirmed || !context.mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const PopScope(canPop: false, child: Center(child: CircularProgressIndicator())),
    );
    try {
      await ref.read(authControllerProvider.notifier).deleteAccount();
      // The router's auth redirect takes the user to login once the session is cleared.
    } catch (e) {
      if (context.mounted) Navigator.of(context, rootNavigator: true).pop();
      messenger.showSnackBar(SnackBar(content: Text("We couldn't delete your account. ${e.userMessage}")));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final email = ref.watch(currentUserProvider).valueOrNull?.email;
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Settings")),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          CareerListGroup(
            title: "Account",
            children: [
              CareerListRow(icon: Icons.alternate_email_rounded, title: "Email", subtitle: email ?? "—", tone: AppTone.neutral),
            ],
          ),
          Gap.lg,
          CareerListGroup(
            title: "Appearance",
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const IconTile(icon: AppIcons.appearance, size: 38),
                        Gap.md,
                        Expanded(child: Text("Theme", style: context.text.titleSmall)),
                      ],
                    ),
                    Gap.sm,
                    SizedBox(
                      width: double.infinity,
                      child: SegmentedButton<ThemeMode>(
                        showSelectedIcon: false,
                        segments: const [
                          ButtonSegment(value: ThemeMode.system, icon: Icon(Icons.brightness_auto_outlined, size: 18), label: Text("System")),
                          ButtonSegment(value: ThemeMode.light, icon: Icon(Icons.light_mode_outlined, size: 18), label: Text("Light")),
                          ButtonSegment(value: ThemeMode.dark, icon: Icon(Icons.dark_mode_outlined, size: 18), label: Text("Dark")),
                        ],
                        selected: {themeMode},
                        onSelectionChanged: (value) => ref.read(themeModeProvider.notifier).setMode(value.first),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          Gap.lg,
          CareerListGroup(
            title: "Career tools",
            children: [
              CareerListRow(
                icon: AppIcons.email,
                title: "Smart Application Tracking",
                subtitle: "Connected mailboxes and recruitment updates",
                onTap: () => context.push("/settings/tracking"),
              ),
            ],
          ),
          Gap.lg,
          CareerListGroup(
            title: "Privacy & plan",
            children: [
              CareerListRow(
                icon: AppIcons.privacy,
                tone: AppTone.success,
                title: "Ads & Privacy",
                subtitle: "Ad personalization choices",
                onTap: () => context.push("/settings/ads-privacy"),
              ),
              CareerListRow(
                icon: AppIcons.pro,
                tone: AppTone.purple,
                title: "CareerOS Pro",
                subtitle: "Coming soon",
                onTap: () => context.push("/settings/pro"),
              ),
            ],
          ),
          Gap.lg,
          CareerListGroup(
            title: "About",
            children: [
              CareerListRow(
                icon: AppIcons.about,
                tone: AppTone.neutral,
                title: "About CareerOS",
                subtitle: "Open-source licenses",
                onTap: () => showLicensePage(
                  context: context,
                  applicationName: "CareerOS",
                  applicationLegalese: "Opportunities Today. A Brighter You Tomorrow.",
                  applicationIcon: const Padding(padding: EdgeInsets.all(AppSpacing.md), child: CareerOSMark(size: 56)),
                ),
              ),
            ],
          ),
          Gap.xxl,
          AppOutlineButton(label: "Log Out", icon: AppIcons.logout, onPressed: () => ref.read(authControllerProvider.notifier).logout()),
          Gap.sm,
          Center(
            child: TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: AppColors.error),
              onPressed: () => _confirmDelete(context, ref),
              icon: const Icon(AppIcons.delete),
              label: const Text("Delete Account"),
            ),
          ),
        ],
      ),
    );
  }
}
