import "dart:async";

import "package:google_mobile_ads/google_mobile_ads.dart";

import "ad_analytics.dart";
import "ad_frequency_controller.dart";
import "ad_placement.dart";
import "ad_unit_ids.dart";
import "consent_manager.dart";
import "monetization_models.dart";
import "monetization_repository.dart";

/// The single abstraction every screen goes through for ads (spec §7) — no screen ever
/// constructs a `BannerAd`/`InterstitialAd`/`RewardedAd` directly. Responsibilities: SDK
/// initialization, consent gating, format/placement-aware load decisions, frequency limits,
/// entitlement checks (Pro users never see ads), and failure handling that never crashes or
/// leaves a dead UI slot.
abstract class AdService {
  Future<void> initialize();

  /// Whether `format` may be requested right now at all, folding together: the remote
  /// `MonetizationConfig` kill switches, the current `Entitlement` (Pro → never show ads), and
  /// consent state. Does **not** check interstitial frequency — see `canShowInterstitialNow`.
  Future<bool> canRequestAd(AdFormat format);

  /// Interstitial-specific: also consults `AdFrequencyController`. Callers must check this before
  /// ever attempting to load+show an interstitial.
  bool canShowInterstitialNow();

  void recordInterstitialShown();

  /// Loads a banner for `placement` or returns null if it shouldn't/can't be shown right now
  /// (disabled, Pro user, load failure). Never throws.
  Future<BannerAd?> loadBanner({required AdPlacement placement, required AdSize size});

  /// Loads and immediately shows a rewarded ad. Returns true only if the SDK's actual
  /// earned-reward callback fired (spec §15) — never for "loaded"/"started"/"dismissed" alone.
  /// On success, the reward is also claimed server-side (idempotent) before this resolves.
  Future<bool> showRewarded({required AdPlacement placement, required RewardType rewardType});

  /// Shows an interstitial at `placement` only if every gate passes: format enabled, not Pro,
  /// consent obtained, AND the frequency controller allows it right now (spec §19) — callers
  /// never make their own frequency decision. A no-op (never throws, never blocks navigation) if
  /// any gate fails or the ad fails to load.
  Future<void> maybeShowInterstitial({required AdPlacement placement});

  Future<void> dispose();
}

class GoogleMobileAdsService implements AdService {
  GoogleMobileAdsService({
    required MonetizationRepository repository,
    required ConsentManager consentManager,
    required AdAnalytics analytics,
    required bool Function() isProUser,
    required MonetizationConfig Function() currentConfig,
    AdUnitConfig? adUnitConfig,
    AdFrequencyController? frequencyController,
  })  : _repository = repository,
        _consentManager = consentManager,
        _analytics = analytics,
        _isProUser = isProUser,
        _currentConfig = currentConfig,
        _adUnitConfig = adUnitConfig ?? AdUnitConfig.fromEnvironment(isProductionBuild: false),
        _frequency = frequencyController ??
            AdFrequencyController(minIntervalSeconds: 480, maxPerSession: 3);

  final MonetizationRepository _repository;
  final ConsentManager _consentManager;
  final AdAnalytics _analytics;
  final bool Function() _isProUser;
  final MonetizationConfig Function() _currentConfig;
  final AdUnitConfig _adUnitConfig;
  final AdFrequencyController _frequency;

  bool _initialized = false;

  @override
  Future<void> initialize() async {
    // Ad init failure must never block app launch (spec §3) — every step here is best-effort.
    try {
      await _consentManager.gatherConsent();
    } catch (_) {
      // Proceed without personalized consent state; canRequestAd() re-checks before any request.
    }
    try {
      await MobileAds.instance.initialize();
      _initialized = true;
    } catch (_) {
      _initialized = false;
    }
  }

  @override
  Future<bool> canRequestAd(AdFormat format) async {
    if (!_initialized) return false;
    if (_isProUser()) return false; // spec §68: Pro requests/shows zero ads.
    if (!_currentConfig().isFormatEnabled(format)) return false;
    try {
      return await _consentManager.canRequestAds();
    } catch (_) {
      return false; // fail-safe: unknown consent state never requests an ad.
    }
  }

  @override
  bool canShowInterstitialNow() => _frequency.canShowInterstitial();

  @override
  void recordInterstitialShown() => _frequency.recordShown();

  @override
  Future<BannerAd?> loadBanner({required AdPlacement placement, required AdSize size}) async {
    if (!await canRequestAd(AdFormat.banner)) return null;
    final unitId = _adUnitConfig.resolve(AdFormat.banner);
    if (unitId == null) return null;

    _analytics.track(AdAnalyticsEvent.requested, format: AdFormat.banner, placement: placement);
    final completer = _BannerCompleter();
    final banner = BannerAd(
      adUnitId: unitId,
      size: size,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          _analytics.track(AdAnalyticsEvent.loaded, format: AdFormat.banner, placement: placement);
          completer.complete(ad as BannerAd);
        },
        onAdFailedToLoad: (ad, error) {
          _analytics.track(
            AdAnalyticsEvent.failed,
            format: AdFormat.banner,
            placement: placement,
            reason: error.code.toString(),
          );
          ad.dispose();
          completer.complete(null);
        },
        onAdOpened: (ad) => _analytics.track(AdAnalyticsEvent.opened, format: AdFormat.banner, placement: placement),
        onAdClosed: (ad) => _analytics.track(AdAnalyticsEvent.closed, format: AdFormat.banner, placement: placement),
        onAdImpression: (ad) =>
            _analytics.track(AdAnalyticsEvent.impression, format: AdFormat.banner, placement: placement),
      ),
    );
    try {
      await banner.load();
    } catch (_) {
      return null;
    }
    return completer.future;
  }

  @override
  Future<bool> showRewarded({required AdPlacement placement, required RewardType rewardType}) async {
    if (!await canRequestAd(AdFormat.rewarded)) return false;
    final unitId = _adUnitConfig.resolve(AdFormat.rewarded);
    if (unitId == null) return false;

    _analytics.track(AdAnalyticsEvent.requested, format: AdFormat.rewarded, placement: placement);
    final loadCompleter = _RewardedLoadCompleter();
    await RewardedAd.load(
      adUnitId: unitId,
      request: const AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: (ad) {
          _analytics.track(AdAnalyticsEvent.loaded, format: AdFormat.rewarded, placement: placement);
          loadCompleter.complete(ad);
        },
        onAdFailedToLoad: (error) {
          _analytics.track(
            AdAnalyticsEvent.failed,
            format: AdFormat.rewarded,
            placement: placement,
            reason: error.code.toString(),
          );
          loadCompleter.complete(null);
        },
      ),
    );
    final ad = await loadCompleter.future;
    if (ad == null) return false;

    var earnedReward = false;
    final showCompleter = _ShowCompleter();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdShowedFullScreenContent: (ad) => _analytics.track(AdAnalyticsEvent.opened, format: AdFormat.rewarded, placement: placement),
      onAdDismissedFullScreenContent: (ad) {
        _analytics.track(AdAnalyticsEvent.closed, format: AdFormat.rewarded, placement: placement);
        ad.dispose();
        showCompleter.complete();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        ad.dispose();
        showCompleter.complete();
      },
    );

    await ad.show(
      onUserEarnedReward: (ad, reward) {
        // The ONLY trigger for granting a reward (spec §15) — never ad-loaded/started/dismissed.
        earnedReward = true;
        _analytics.track(AdAnalyticsEvent.rewardGranted, format: AdFormat.rewarded, placement: placement);
      },
    );
    await showCompleter.future;

    if (!earnedReward) return false;

    // Claim server-side — idempotent on reference_id (spec §17), so a duplicated local call from
    // this exact ad-watch attempt can never grant a second reward.
    final referenceId = "${placement.name}-${DateTime.now().microsecondsSinceEpoch}";
    try {
      await _repository.claimReward(rewardType: rewardType, referenceId: referenceId);
      return true;
    } catch (_) {
      // The user genuinely earned the reward but the backend claim failed (offline, server
      // error) — do not silently grant a client-only unlock. Surface as failure; the caller can
      // offer to retry.
      return false;
    }
  }

  @override
  Future<void> maybeShowInterstitial({required AdPlacement placement}) async {
    if (!canShowInterstitialNow()) return;
    if (!await canRequestAd(AdFormat.interstitial)) return;
    final unitId = _adUnitConfig.resolve(AdFormat.interstitial);
    if (unitId == null) return;

    _analytics.track(AdAnalyticsEvent.requested, format: AdFormat.interstitial, placement: placement);
    final loadCompleter = _InterstitialLoadCompleter();
    await InterstitialAd.load(
      adUnitId: unitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) {
          _analytics.track(AdAnalyticsEvent.loaded, format: AdFormat.interstitial, placement: placement);
          loadCompleter.complete(ad);
        },
        onAdFailedToLoad: (error) {
          _analytics.track(
            AdAnalyticsEvent.failed,
            format: AdFormat.interstitial,
            placement: placement,
            reason: error.code.toString(),
          );
          loadCompleter.complete(null);
        },
      ),
    );
    final ad = await loadCompleter.future;
    if (ad == null) return;

    final showCompleter = _ShowCompleter();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdShowedFullScreenContent: (ad) {
        recordInterstitialShown();
        _analytics.track(AdAnalyticsEvent.opened, format: AdFormat.interstitial, placement: placement);
      },
      onAdDismissedFullScreenContent: (ad) {
        _analytics.track(AdAnalyticsEvent.closed, format: AdFormat.interstitial, placement: placement);
        ad.dispose();
        showCompleter.complete();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        ad.dispose();
        showCompleter.complete();
      },
    );
    await ad.show();
    await showCompleter.future;
  }

  @override
  Future<void> dispose() async {
    _frequency.resetSession();
  }
}

class _BannerCompleter {
  final _completer = Completer<BannerAd?>();
  void complete(BannerAd? ad) {
    if (!_completer.isCompleted) _completer.complete(ad);
  }

  Future<BannerAd?> get future => _completer.future;
}

class _InterstitialLoadCompleter {
  final _completer = Completer<InterstitialAd?>();
  void complete(InterstitialAd? ad) {
    if (!_completer.isCompleted) _completer.complete(ad);
  }

  Future<InterstitialAd?> get future => _completer.future;
}

class _RewardedLoadCompleter {
  final _completer = Completer<RewardedAd?>();
  void complete(RewardedAd? ad) {
    if (!_completer.isCompleted) _completer.complete(ad);
  }

  Future<RewardedAd?> get future => _completer.future;
}

class _ShowCompleter {
  final _completer = Completer<void>();
  void complete() {
    if (!_completer.isCompleted) _completer.complete();
  }

  Future<void> get future => _completer.future;
}
