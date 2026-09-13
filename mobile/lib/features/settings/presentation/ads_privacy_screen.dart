import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/design/design.dart";
import "../../../core/monetization/monetization_providers.dart";
import "../../../core/widgets/widgets.dart";

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
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Couldn't open privacy options right now.")));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final entitlement = ref.watch(entitlementProvider).valueOrNull;
    final config = ref.watch(monetizationConfigProvider).valueOrNull;
    final isPro = entitlement?.isPro ?? false;

    return Scaffold(
      appBar: AppBar(title: const Text("Ads & Privacy")),
      body: ListView(
        padding: AppSpacing.page,
        children: [
          CareerListGroup(
            title: "Your plan",
            children: [
              CareerListRow(
                icon: AppIcons.pro,
                tone: AppTone.purple,
                title: "CareerOS Pro status",
                subtitle: isPro ? "Pro (no ads)" : "CareerOS Free",
              ),
              CareerListRow(
                icon: Icons.ads_click_outlined,
                tone: AppTone.neutral,
                title: "Advertising",
                subtitle: isPro
                    ? "Disabled — CareerOS Pro shows no ads."
                    : config?.adsEnabled ?? true
                        ? "Enabled — supports CareerOS at no cost to you."
                        : "Currently disabled.",
              ),
            ],
          ),
          if (_privacyOptionsRequired == true) ...[
            Gap.lg,
            CareerListGroup(
              title: "Choices",
              children: [
                CareerListRow(
                  icon: Icons.tune_outlined,
                  title: "Privacy choices",
                  subtitle: "Review or change your ad personalization choices",
                  onTap: _openPrivacyOptions,
                ),
              ],
            ),
          ],
          Gap.lg,
          const InsightCard(
            icon: AppIcons.privacy,
            tone: AppTone.success,
            title: "Your career data is never used for ads",
            message:
                "CareerOS never uses your CV, application history, email content, interview recordings, or other private career data to target ads.",
          ),
        ],
      ),
    );
  }
}
