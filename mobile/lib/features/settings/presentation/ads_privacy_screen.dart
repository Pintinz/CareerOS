import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/monetization/monetization_providers.dart";
import "../../../core/design/design.dart";

/// Settings → Ads & Privacy (spec §24-25). Shows consent/personalization status and CareerOS Pro
/// status, and lets the user revisit Google's own privacy-options form when required — never a
/// homemade consent dialog (spec §23), and never exposes a Google-internal identifier.
class AdsPrivacyScreen extends ConsumerStatefulWidget {
  const AdsPrivacyScreen({super.key});

  @override
  ConsumerState<AdsPrivacyScreen> createState() => _AdsPrivacyScreenState();
}

class _AdsPrivacyScreenState extends ConsumerState<AdsPrivacyScreen> {
  bool? _privacyOptionsRequired;

  @override
  void initState() {
    super.initState();
    _loadPrivacyOptionsStatus();
  }

  Future<void> _loadPrivacyOptionsStatus() async {
    try {
      final required = await ref.read(consentManagerProvider).isPrivacyOptionsRequired();
      if (mounted) setState(() => _privacyOptionsRequired = required);
    } catch (_) {
      if (mounted) setState(() => _privacyOptionsRequired = false);
    }
  }

  Future<void> _openPrivacyOptions() async {
    try {
      await ref.read(consentManagerProvider).showPrivacyOptionsForm();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text("Couldn't open privacy options right now.")));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final entitlement = ref.watch(entitlementProvider).valueOrNull;
    final config = ref.watch(monetizationConfigProvider).valueOrNull;

    return Scaffold(
      appBar: AppBar(title: const Text("Ads & Privacy")),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.workspace_premium_outlined, color: AppColors.blue),
              title: const Text("CareerOS Pro status"),
              subtitle: Text(entitlement?.isPro ?? false ? "Pro (no ads)" : "CareerOS Free"),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.ads_click_outlined, color: AppColors.blue),
              title: const Text("Advertising"),
              subtitle: Text(
                entitlement?.isPro ?? false
                    ? "Disabled — CareerOS Pro shows no ads."
                    : config?.adsEnabled ?? true
                        ? "Enabled — supports CareerOS at no cost to you."
                        : "Currently disabled.",
              ),
            ),
          ),
          if (_privacyOptionsRequired == true) ...[
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.tune_outlined, color: AppColors.blue),
                title: const Text("Privacy choices"),
                subtitle: const Text("Review or change your ad personalization choices"),
                trailing: const Icon(Icons.chevron_right, color: AppColors.muted),
                onTap: _openPrivacyOptions,
              ),
            ),
          ],
          const SizedBox(height: 20),
          Text(
            "CareerOS never uses your CV, application history, email content, interview "
            "recordings, or other private career data to target ads.",
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
          ),
        ],
      ),
    );
  }
}
