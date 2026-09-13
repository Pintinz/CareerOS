import "package:flutter/material.dart";

import "../../../core/design/design.dart";
import "../../../core/utils/url_launcher_helper.dart";
import "../../../core/widgets/widgets.dart";
import "../data/email_tracking_models.dart";

/// Spec §3 — shown before every OAuth authorization, for both Gmail and Microsoft. Exact required
/// copy, never skipped, never combined with the authorization redirect itself so the user always
/// sees this on CareerOS before their browser opens.
class ConnectConsentScreen extends StatelessWidget {
  const ConnectConsentScreen({super.key, required this.provider, required this.onContinue});

  final EmailProvider provider;
  final Future<void> Function(BuildContext context) onContinue;

  @override
  Widget build(BuildContext context) {
    final providerName = provider == EmailProvider.gmail ? "Gmail" : "Microsoft";
    return Scaffold(
      appBar: AppBar(title: Text("Connect $providerName for Smart Tracking")),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.pageH, AppSpacing.sm, AppSpacing.pageH, AppSpacing.md),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              PrimaryButton(
                label: "Continue to ${provider == EmailProvider.gmail ? 'Google' : 'Microsoft'}",
                icon: AppIcons.external,
                onPressed: () => onContinue(context),
              ),
              Gap.xs,
              SizedBox(width: double.infinity, child: TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Not Now"))),
            ],
          ),
        ),
      ),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          IconTile(icon: provider == EmailProvider.gmail ? Icons.mail_outline : Icons.alternate_email, size: 64),
          Gap.xl,
          Text(
            "CareerOS uses authorized email access only\n"
            "to identify recruitment-related messages\n"
            "and suggest updates to applications you track.",
            style: context.text.titleMedium?.copyWith(height: 1.45),
          ),
          Gap.lg,
          const CareerListGroup(
            children: [
              CareerListRow(icon: Icons.block_outlined, tone: AppTone.success, title: "We do not use your inbox for advertising."),
              CareerListRow(icon: Icons.verified_user_outlined, tone: AppTone.success, title: "No application stage changes automatically."),
              CareerListRow(icon: Icons.link_off_rounded, tone: AppTone.success, title: "You can disconnect at any time."),
            ],
          ),
        ],
      ),
    );
  }
}

/// Opens the given OAuth authorization URL in the system browser (spec §6/§10 — the mobile app
/// never handles the provider's login form itself, it hands off entirely).
Future<void> openAuthorizationUrl(BuildContext context, String url) => openExternalUrl(context, url);
