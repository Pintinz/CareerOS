import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";
import "package:intl/intl.dart";

import "../../../core/utils/error_message.dart";
import "../../../core/design/design.dart";
import "../data/email_tracking_models.dart";
import "connect_consent_screen.dart";
import "email_tracking_providers.dart";

/// Profile → Settings → Application Tracking → "Smart Application Tracking" (spec §2).
/// Manual Tracking (Phase 5) keeps working exactly as before regardless of anything on this
/// screen — email integration is purely an optional enhancement layered on top (spec §37).
class SmartTrackingSettingsScreen extends ConsumerWidget {
  const SmartTrackingSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final availabilityAsync = ref.watch(providerAvailabilityProvider);
    final connectionsAsync = ref.watch(emailConnectionsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Smart Application Tracking")),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(providerAvailabilityProvider);
          ref.invalidate(emailConnectionsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              "CareerOS can detect recruitment updates such as aptitude tests, interviews and offers.",
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10)),
              child: const Row(
                children: [
                  Icon(Icons.verified_user_outlined, size: 18, color: AppColors.success),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "CareerOS will never change an application stage without your confirmation.",
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            connectionsAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (connections) {
                final gmail = connections.where((c) => c.provider == EmailProvider.gmail).toList();
                final outlook = connections.where((c) => c.provider == EmailProvider.outlook).toList();
                return availabilityAsync.when(
                  loading: () => const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
                  error: (e, _) => Text(e.userMessage, style: const TextStyle(color: AppColors.danger)),
                  data: (availability) => Column(
                    children: [
                      _ProviderCard(
                        icon: Icons.mail_outline,
                        title: "Gmail",
                        available: availability.gmailAvailable,
                        connection: gmail.isEmpty ? null : gmail.first,
                        onConnect: () => _connect(context, ref, EmailProvider.gmail),
                        onDisconnect: (id) => _disconnect(context, ref, id),
                      ),
                      const SizedBox(height: 12),
                      _ProviderCard(
                        icon: Icons.alternate_email,
                        title: "Outlook",
                        available: availability.outlookAvailable,
                        connection: outlook.isEmpty ? null : outlook.first,
                        onConnect: () => _connect(context, ref, EmailProvider.outlook),
                        onDisconnect: (id) => _disconnect(context, ref, id),
                      ),
                      const SizedBox(height: 12),
                      _ForwardEmailCard(availability: availability),
                      const SizedBox(height: 12),
                      const _ManualTrackingCard(),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(height: 28),
            OutlinedButton.icon(
              onPressed: () => _confirmDeleteTrackingData(context, ref),
              icon: const Icon(Icons.delete_outline, color: AppColors.danger),
              label: const Text("Delete Recruitment Email Data", style: TextStyle(color: AppColors.danger)),
            ),
            const SizedBox(height: 8),
            const Text(
              "This deletes stored CareerOS email-tracking metadata and suggestions. Confirmed "
              "application timeline stages remain unless you separately edit the application.",
              style: TextStyle(fontSize: 12, color: AppColors.muted),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _connect(BuildContext context, WidgetRef ref, EmailProvider provider) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ConnectConsentScreen(
          provider: provider,
          onContinue: (context) async {
            Navigator.of(context).pop();
            try {
              final repo = ref.read(emailTrackingRepositoryProvider);
              final url = provider == EmailProvider.gmail ? await repo.startConnectGmail() : await repo.startConnectOutlook();
              if (context.mounted) await openAuthorizationUrl(context, url);
            } catch (e) {
              if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
            }
          },
        ),
      ),
    );
    ref.invalidate(emailConnectionsProvider);
  }

  Future<void> _disconnect(BuildContext context, WidgetRef ref, String connectionId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Disconnect?"),
        content: const Text("CareerOS will stop checking this mailbox for recruitment updates. Your confirmed application history is unaffected."),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Cancel")),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Disconnect", style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(emailTrackingRepositoryProvider).disconnect(connectionId);
      ref.invalidate(emailConnectionsProvider);
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    }
  }

  Future<void> _confirmDeleteTrackingData(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Delete Recruitment Email Data"),
        content: const Text(
          "This deletes stored CareerOS email-tracking metadata and suggestions.\n\n"
          "Confirmed application timeline stages remain unless you separately edit the application.",
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text("Cancel")),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text("Delete", style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(emailTrackingRepositoryProvider).deleteTrackingData();
      ref.invalidate(recruitmentEventsProvider);
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Recruitment email data deleted.")));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.userMessage)));
    }
  }
}

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({
    required this.icon,
    required this.title,
    required this.available,
    required this.connection,
    required this.onConnect,
    required this.onDisconnect,
  });

  final IconData icon;
  final String title;
  final bool available;
  final EmailConnection? connection;
  final VoidCallback onConnect;
  final void Function(String connectionId) onDisconnect;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: AppColors.blue),
                const SizedBox(width: 10),
                Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16))),
                if (connection == null && !available)
                  const _StatusChip(label: "In Development", color: AppColors.muted),
              ],
            ),
            const SizedBox(height: 10),
            if (connection != null) ...[
              Text(connection!.providerEmail, style: const TextStyle(fontWeight: FontWeight.w500)),
              const SizedBox(height: 4),
              if (connection!.status == EmailConnectionStatus.active) ...[
                const _StatusChip(label: "Connected", color: AppColors.success),
                if (connection!.lastSyncAt != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      "Last synced: ${DateFormat.yMMMd().add_jm().format(connection!.lastSyncAt!)}",
                      style: const TextStyle(fontSize: 12, color: AppColors.muted),
                    ),
                  ),
              ] else if (connection!.status == EmailConnectionStatus.reauthorizationRequired)
                const _StatusChip(label: "Reauthorization Required", color: AppColors.warning)
              else
                const _StatusChip(label: "Error", color: AppColors.danger),
              const SizedBox(height: 10),
              Row(
                children: [
                  if (connection!.status != EmailConnectionStatus.active)
                    OutlinedButton(onPressed: onConnect, child: const Text("Reconnect")),
                  const Spacer(),
                  TextButton(
                    onPressed: () => onDisconnect(connection!.id),
                    child: const Text("Disconnect", style: TextStyle(color: AppColors.danger)),
                  ),
                ],
              ),
            ] else ...[
              const Text(
                "CareerOS uses read-only access to detect recruitment updates. Nothing changes without your confirmation.",
                style: TextStyle(fontSize: 12, color: AppColors.muted),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(onPressed: available ? onConnect : null, child: Text("Connect $title")),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ForwardEmailCard extends StatelessWidget {
  const _ForwardEmailCard({required this.availability});

  final ProviderAvailability availability;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.forward_to_inbox_outlined, color: AppColors.purple),
                const SizedBox(width: 10),
                const Expanded(child: Text("Forward Recruitment Email", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16))),
                if (!availability.forwardEmailAvailable) const _StatusChip(label: "In Development", color: AppColors.muted),
              ],
            ),
            const SizedBox(height: 10),
            const Text(
              "The most private option — no account connection at all. Forward a recruitment email to your "
              "personal CareerOS address and we'll suggest an update.",
              style: TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            if (availability.forwardEmailAvailable && availability.forwardEmailAlias != null) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(8)),
                child: Row(
                  children: [
                    Expanded(child: Text(availability.forwardEmailAlias!, style: const TextStyle(fontFamily: "monospace"))),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 18),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: availability.forwardEmailAlias!));
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Alias copied.")));
                      },
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ManualTrackingCard extends StatelessWidget {
  const _ManualTrackingCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            const Icon(Icons.edit_note_outlined, color: AppColors.blue),
            const SizedBox(width: 10),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Manual Tracking", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                  SizedBox(height: 2),
                  Text("Always available — update your application stages yourself, any time.", style: TextStyle(fontSize: 12, color: AppColors.muted)),
                ],
              ),
            ),
            TextButton(onPressed: () => context.push("/applications"), child: const Text("Open")),
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
      child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }
}
