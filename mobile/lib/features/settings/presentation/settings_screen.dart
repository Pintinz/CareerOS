import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";

/// Profile → Settings (spec §2). Deliberately minimal — only "Application Tracking", "Ads &
/// Privacy" (Phase 10), and "CareerOS Pro" (Phase 10, architecture-only) are built; other
/// settings categories are a later phase's scope, not faked here with dead taps.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Settings")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.mark_email_read_outlined, color: AppColors.blue),
              title: const Text("Application Tracking"),
              subtitle: const Text("Smart Application Tracking, connected mailboxes, and updates"),
              trailing: const Icon(Icons.chevron_right, color: AppColors.muted),
              onTap: () => context.push("/settings/tracking"),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.workspace_premium_outlined, color: AppColors.blue),
              title: const Text("CareerOS Pro"),
              subtitle: const Text("Ad-free, unlimited practice, advanced analytics"),
              trailing: const Icon(Icons.chevron_right, color: AppColors.muted),
              onTap: () => context.push("/settings/pro"),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.privacy_tip_outlined, color: AppColors.blue),
              title: const Text("Ads & Privacy"),
              subtitle: const Text("Ad personalization choices and CareerOS Pro status"),
              trailing: const Icon(Icons.chevron_right, color: AppColors.muted),
              onTap: () => context.push("/settings/ads-privacy"),
            ),
          ),
        ],
      ),
    );
  }
}
