import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/date_labels.dart";
import "../../../core/utils/error_message.dart";
import "../../../core/widgets/widgets.dart";
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
          padding: AppSpacing.page,
          children: [
            Text(
              "CareerOS can detect recruitment updates such as aptitude tests, interviews and offers.",
              style: context.text.bodyLarge,
            ),
            Gap.md,
            const InsightCard(
              icon: Icons.verified_user_outlined,
              tone: AppTone.success,
              title: "CareerOS will never change an application stage without your confirmation.",
            ),
            Gap.xl,
            connectionsAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (connections) {
                final gmail = connections.where((c) => c.provider == EmailProvider.gmail).toList();
                final outlook = connections.where((c) => c.provider == EmailProvider.outlook).toList();
                return availabilityAsync.when(
                  loading: () => const Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]),
                  error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(providerAvailabilityProvider)),
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
                      Gap.sm,
                      _ProviderCard(
                        icon: Icons.alternate_email,
                        title: "Outlook",
                        available: availability.outlookAvailable,
                        connection: outlook.isEmpty ? null : outlook.first,
                        onConnect: () => _connect(context, ref, EmailProvider.outlook),
                        onDisconnect: (id) => _disconnect(context, ref, id),
                      ),
                      Gap.sm,
                      _ForwardEmailCard(availability: availability),
                      Gap.sm,
                      const _ManualTrackingCard(),
                    ],
                  ),
                );
              },
            ),
            Gap.xxl,
            Center(
              child: TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: AppColors.error),
                onPressed: () => _confirmDeleteTrackingData(context, ref),
                icon: const Icon(AppIcons.delete),
                label: const Text("Delete Recruitment Email Data"),
              ),
            ),
            Text(
              "This deletes stored CareerOS email-tracking metadata and suggestions. Confirmed "
              "application timeline stages remain unless you separately edit the application.",
              style: context.text.bodySmall,
              textAlign: TextAlign.center,
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
          TextButton(
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text("Disconnect"),
          ),
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
    final confirmed = await showCareerDialog(
      context: context,
      title: "Delete Recruitment Email Data",
      message:
          "This deletes stored CareerOS email-tracking metadata and suggestions.\n\nConfirmed application timeline stages remain unless you separately edit the application.",
      confirmLabel: "Delete",
      destructive: true,
    );
    if (!confirmed) return;
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
    return CareerCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconTile(icon: icon, size: 40),
              Gap.sm,
              Expanded(child: Text(title, style: context.text.titleMedium)),
              if (connection == null && !available) const StatusChip(label: "In Development"),
            ],
          ),
          Gap.sm,
          if (connection != null) ...[
            Text(connection!.providerEmail, style: context.text.titleSmall),
            Gap.xxs,
            if (connection!.status == EmailConnectionStatus.active) ...[
              const StatusChip(label: "Connected", tone: AppTone.success, icon: AppIcons.check),
              if (connection!.lastSyncAt != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.xxs),
                  child: Text("Last synced: ${DateLabels.dateTime(connection!.lastSyncAt!)}", style: context.text.bodySmall),
                ),
            ] else if (connection!.status == EmailConnectionStatus.reauthorizationRequired)
              const StatusChip(label: "Reauthorization Required", tone: AppTone.warning, icon: Icons.warning_amber_rounded)
            else
              const StatusChip(label: "Error", tone: AppTone.danger, icon: AppIcons.error),
            Gap.sm,
            Row(
              children: [
                if (connection!.status != EmailConnectionStatus.active)
                  AppOutlineButton(label: "Reconnect", expand: false, onPressed: onConnect),
                const Spacer(),
                TextButton(
                  style: TextButton.styleFrom(foregroundColor: AppColors.error),
                  onPressed: () => onDisconnect(connection!.id),
                  child: const Text("Disconnect"),
                ),
              ],
            ),
          ] else ...[
            Text(
              "CareerOS uses read-only access to detect recruitment updates. Nothing changes without your confirmation.",
              style: context.text.bodySmall,
            ),
            Gap.sm,
            SizedBox(width: double.infinity, child: OutlinedButton(onPressed: available ? onConnect : null, child: Text("Connect $title"))),
          ],
        ],
      ),
    );
  }
}

class _ForwardEmailCard extends StatelessWidget {
  const _ForwardEmailCard({required this.availability});

  final ProviderAvailability availability;

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const IconTile(icon: Icons.forward_to_inbox_outlined, tone: AppTone.purple, size: 40),
              Gap.sm,
              Expanded(child: Text("Forward Recruitment Email", style: context.text.titleMedium)),
              if (!availability.forwardEmailAvailable) const StatusChip(label: "In Development"),
            ],
          ),
          Gap.sm,
          Text(
            "The most private option — no account connection at all. Forward a recruitment email to your "
            "personal CareerOS address and we'll suggest an update.",
            style: context.text.bodySmall,
          ),
          if (availability.forwardEmailAvailable && availability.forwardEmailAlias != null) ...[
            Gap.sm,
            Container(
              width: double.infinity,
              padding: const EdgeInsets.only(left: AppSpacing.sm),
              decoration: BoxDecoration(color: context.colors.surfaceMuted, borderRadius: AppRadius.mdAll),
              child: Row(
                children: [
                  Expanded(child: SelectableText(availability.forwardEmailAlias!, style: context.text.bodyMedium?.copyWith(fontFamily: "monospace"))),
                  IconButton(
                    tooltip: "Copy address",
                    icon: const Icon(Icons.copy_rounded, size: 18),
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
    );
  }
}

class _ManualTrackingCard extends StatelessWidget {
  const _ManualTrackingCard();

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      child: Row(
        children: [
          const IconTile(icon: Icons.edit_note_outlined, tone: AppTone.success, size: 40),
          Gap.sm,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Manual Tracking", style: context.text.titleMedium),
                const SizedBox(height: 2),
                Text("Always available — update your application stages yourself, any time.", style: context.text.bodySmall),
              ],
            ),
          ),
          TextButton(onPressed: () => context.push("/applications"), child: const Text("Open")),
        ],
      ),
    );
  }
}
