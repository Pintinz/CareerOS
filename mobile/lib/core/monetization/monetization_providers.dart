import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../config/env.dart";
import "../app_providers.dart";
import "ad_analytics.dart";
import "ad_frequency_controller.dart";
import "ad_service.dart";
import "ad_unit_ids.dart";
import "consent_manager.dart";
import "monetization_models.dart";
import "monetization_repository.dart";

final monetizationRepositoryProvider = Provider<MonetizationRepository>((ref) {
  return MonetizationRepository(apiClient: ref.watch(apiClientProvider));
});

/// Fetched once at startup; `Entitlement.unknown`/`MonetizationConfig.disabled` (ads off) if it
/// fails, so a network hiccup can never accidentally turn ads ON or block core functionality.
final monetizationConfigProvider = FutureProvider<MonetizationConfig>((ref) async {
  try {
    return await ref.watch(monetizationRepositoryProvider).getConfig();
  } catch (_) {
    return MonetizationConfig.disabled;
  }
});

final entitlementProvider = FutureProvider.autoDispose<Entitlement>((ref) async {
  try {
    return await ref.watch(monetizationRepositoryProvider).getEntitlement();
  } catch (_) {
    return Entitlement.unknown;
  }
});

final consentManagerProvider = Provider<ConsentManager>((ref) => UmpConsentManager());

final adAnalyticsProvider = Provider<AdAnalytics>((ref) => const LoggingAdAnalytics());

/// The one AdService instance for the app's lifetime. Reads the *last known* config/entitlement
/// synchronously (via `.valueOrNull`) rather than depending on the async providers directly, so a
/// slow/failed refetch can never make `AdService` itself throw — it simply behaves as if ads are
/// off until a real config/entitlement value has loaded.
final adServiceProvider = Provider<AdService>((ref) {
  final config = ref.read(monetizationConfigProvider).valueOrNull ?? MonetizationConfig.disabled;
  final service = GoogleMobileAdsService(
    repository: ref.watch(monetizationRepositoryProvider),
    consentManager: ref.watch(consentManagerProvider),
    analytics: ref.watch(adAnalyticsProvider),
    isProUser: () => ref.read(entitlementProvider).valueOrNull?.isPro ?? false,
    currentConfig: () => ref.read(monetizationConfigProvider).valueOrNull ?? MonetizationConfig.disabled,
    adUnitConfig: AdUnitConfig.fromEnvironment(isProductionBuild: Env.isProduction),
    frequencyController: AdFrequencyController(
      minIntervalSeconds: config.interstitialMinIntervalSeconds,
      maxPerSession: config.interstitialMaxPerSession,
    ),
  );
  ref.onDispose(() => service.dispose());
  return service;
});
