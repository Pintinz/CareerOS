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
            const _TrackingIntro(),
            Gap.section,
            const SectionHeader(title: "Connect a Mailbox", subtitle: "Read-only access · disconnect any time"),
            connectionsAsync.when(
              loading: () => const Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]),
              error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(emailConnectionsProvider)),
              data: (connections) {
                final gmail = connections.where((c) => c.provider == EmailProvider.gmail).toList();
                final outlook = connections.where((c) => c.provider == EmailProvider.outlook).toList();
                return availabilityAsync.when(
                  loading: () => const Column(children: [SkeletonCard(), Gap.sm, SkeletonCard()]),
                  error: (e, _) => ErrorState(compact: true, message: e.userMessage, onRetry: () => ref.invalidate(providerAvailabilityProvider)),
                  data: (availability) => CareerListGroup(
                    children: [
                      _ProviderRow(
                        icon: Icons.mail_outline,
                        title: "Gmail",
                        available: availability.gmailAvailable,
                        connection: gmail.isEmpty ? null : gmail.first,
                        onConnect: () => _connect(context, ref, EmailProvider.gmail),
                        onDisconnect: (id) => _disconnect(context, ref, id),
                      ),
                      _ProviderRow(
                        icon: Icons.alternate_email,
                        title: "Outlook",
                        available: availability.outlookAvailable,
                        connection: outlook.isEmpty ? null : outlook.first,
                        onConnect: () => _connect(context, ref, EmailProvider.outlook),
                        onDisconnect: (id) => _disconnect(context, ref, id),
                      ),
                      _ForwardEmailRow(availability: availability),
                    ],
                  ),
                );
              },
            ),
            Gap.section,
            CareerListGroup(
              title: "Always available",
              children: [
                CareerListRow(
                  icon: Icons.mark_email_unread_outlined,
                  title: "Application Updates",
                  subtitle: "Review suggested stage changes",
                  onTap: () => context.push("/settings/tracking/events"),
                ),
                CareerListRow(
                  icon: Icons.edit_note_outlined,
                  tone: AppTone.success,
                  title: "Manual Tracking",
                  subtitle: "Update your application stages yourself, any time",
                  onTap: () => context.push("/applications"),
                ),
              ],
            ),
            Gap.section,
            CareerListGroup(
              title: "Your data",
              children: [
                CareerListRow(
                  icon: AppIcons.delete,
                  title: "Delete Recruitment Email Data",
                  subtitle: "Removes stored email-tracking metadata and suggestions. Confirmed application stages stay.",
                  destructive: true,
                  onTap: () => _confirmDeleteTrackingData(context, ref),
                ),
              ],
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

/// What Smart Tracking does and the two promises that make it safe, in one calm surface.
class _TrackingIntro extends StatelessWidget {
  const _TrackingIntro();

  @override
  Widget build(BuildContext context) {
    return CareerCard(
      variant: CareerCardVariant.feature,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const IconTile(icon: Icons.mark_email_unread_outlined, size: 48),
          Gap.md,
          Semantics(
            header: true,
            child: Text("Let CareerOS spot recruitment updates", style: context.text.titleLarge),
          ),
          const SizedBox(height: 4),
          Text(
            "CareerOS can detect recruitment updates such as aptitude tests, interviews and offers, and suggest the "
            "matching stage for applications you track.",
            style: context.text.bodyMedium,
          ),
          Gap.md,
          const _Promise(
            icon: Icons.verified_user_outlined,
            text: "CareerOS will never change an application stage without your confirmation.",
          ),
          Gap.xs,
          const _Promise(icon: Icons.visibility_outlined, text: "Read-only access. Email bodies are never shown in the app."),
        ],
      ),
    );
  }
}

class _Promise extends StatelessWidget {
  const _Promise({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 1),
          child: Icon(icon, size: 18, color: AppTone.success.onTint(context)),
        ),
        Gap.xs,
        Expanded(child: Text(text, style: context.text.bodySmall?.copyWith(color: context.colors.textPrimary))),
      ],
    );
  }
}

/// One mailbox provider inside the "Connect a Mailbox" group: not yet available, ready to connect,
/// or connected (with sync state and Reconnect/Disconnect).
class _ProviderRow extends StatelessWidget {
  const _ProviderRow({
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
    final connection = this.connection;
    final Widget? statusChip = connection == null
        ? (available ? null : const StatusChip(label: "Coming soon", dense: true))
        : switch (connection.status) {
            EmailConnectionStatus.active => const StatusChip(label: "Connected", tone: AppTone.success, icon: AppIcons.check, dense: true),
            EmailConnectionStatus.reauthorizationRequired =>
              const StatusChip(label: "Reauthorization Required", tone: AppTone.warning, icon: Icons.warning_amber_rounded, dense: true),
            _ => const StatusChip(label: "Error", tone: AppTone.danger, icon: AppIcons.error, dense: true),
          };

    // The status chip already says whether it's available, so the subtitle describes the access.
    final subtitle = connection != null ? null : "Read-only access to recruitment emails";

    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
      child: Row(
        crossAxisAlignment: connection == null ? CrossAxisAlignment.center : CrossAxisAlignment.start,
        children: [
          IconTile(icon: icon, tone: available || connection != null ? AppTone.primary : AppTone.neutral, size: 38),
          Gap.md,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xxs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(title, style: context.text.titleSmall),
                    if (statusChip != null) statusChip,
                  ],
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle, style: context.text.bodySmall),
                ],
                if (connection != null) ...[
                  const SizedBox(height: 2),
                  Text(connection.providerEmail, style: context.text.bodyMedium?.copyWith(color: context.colors.textPrimary)),
                  if (connection.status == EmailConnectionStatus.active && connection.lastSyncAt != null)
                    Text("Last synced ${DateLabels.dateTime(connection.lastSyncAt!)}", style: context.text.bodySmall),
                  Gap.xs,
                  Row(
                    children: [
                      if (connection.status != EmailConnectionStatus.active) ...[
                        AppOutlineButton(label: "Reconnect", expand: false, onPressed: onConnect),
                        Gap.xs,
                      ],
                      TextButton(
                        style: TextButton.styleFrom(foregroundColor: AppColors.error, padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs)),
                        onPressed: () => onDisconnect(connection.id),
                        child: const Text("Disconnect"),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          if (connection == null && available) ...[
            Gap.xs,
            AppOutlineButton(label: "Connect", expand: false, onPressed: onConnect),
          ],
        ],
      ),
    );
  }
}

class _ForwardEmailRow extends StatelessWidget {
  const _ForwardEmailRow({required this.availability});

  final ProviderAvailability availability;

  @override
  Widget build(BuildContext context) {
    final alias = availability.forwardEmailAvailable ? availability.forwardEmailAlias : null;
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconTile(
            icon: Icons.forward_to_inbox_outlined,
            tone: availability.forwardEmailAvailable ? AppTone.purple : AppTone.neutral,
            size: 38,
          ),
          Gap.md,
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xxs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text("Forward Recruitment Email", style: context.text.titleSmall),
                    if (!availability.forwardEmailAvailable) const StatusChip(label: "Coming soon", dense: true),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  "The most private option — no account connection at all. Forward a recruitment email to your "
                  "personal CareerOS address and we'll suggest an update.",
                  style: context.text.bodySmall,
                ),
                if (alias != null) ...[
                  Gap.xs,
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.only(left: AppSpacing.sm),
                    decoration: BoxDecoration(color: context.colors.surfaceMuted, borderRadius: AppRadius.mdAll),
                    child: Row(
                      children: [
                        Expanded(child: SelectableText(alias, style: context.text.bodyMedium?.copyWith(fontFamily: "monospace"))),
                        IconButton(
                          tooltip: "Copy address",
                          icon: const Icon(Icons.copy_rounded, size: 18),
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: alias));
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
        ],
      ),
    );
  }
}
