import "package:flutter/material.dart";

import "../../../core/utils/url_launcher_helper.dart";
import "../../../theme/app_colors.dart";
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
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(provider == EmailProvider.gmail ? Icons.mail_outline : Icons.alternate_email, size: 40, color: AppColors.blue),
            const SizedBox(height: 20),
            Text(
              "CareerOS uses authorized email access only\n"
              "to identify recruitment-related messages\n"
              "and suggest updates to applications you track.",
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            const _PrivacyPoint(text: "We do not use your inbox for advertising."),
            const _PrivacyPoint(text: "No application stage changes automatically."),
            const _PrivacyPoint(text: "You can disconnect at any time."),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => onContinue(context),
                child: Text("Continue to ${provider == EmailProvider.gmail ? 'Google' : 'Microsoft'}"),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Not Now")),
            ),
          ],
        ),
      ),
    );
  }
}

class _PrivacyPoint extends StatelessWidget {
  const _PrivacyPoint({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_outline, size: 18, color: AppColors.success),
          const SizedBox(width: 8),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

/// Opens the given OAuth authorization URL in the system browser (spec §6/§10 — the mobile app
/// never handles the provider's login form itself, it hands off entirely).
Future<void> openAuthorizationUrl(BuildContext context, String url) => openExternalUrl(context, url);
