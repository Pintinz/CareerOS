/// Ad formats this app supports requesting. App Open is modeled here so the architecture exists,
/// but `MonetizationConfig.appOpenAdsEnabled` stays false by default (Phase 10 spec §2/§22) — no
/// screen in this app ever requests one this phase.
enum AdFormat { banner, interstitial, rewarded, appOpen }

enum RewardType {
  extraAptitudeTest,
  extraAtsAnalysis,
  premiumPracticeSet,
  advancedReport;

  String get wireValue => switch (this) {
        RewardType.extraAptitudeTest => "EXTRA_APTITUDE_TEST",
        RewardType.extraAtsAnalysis => "EXTRA_ATS_ANALYSIS",
        RewardType.premiumPracticeSet => "PREMIUM_PRACTICE_SET",
        RewardType.advancedReport => "ADVANCED_REPORT",
      };
}

/// Non-secret, admin-configurable ad/frequency settings fetched from `GET /monetization/config`
/// (spec §6/§38-39). Never carries AdMob credentials — those live in mobile build config only.
class MonetizationConfig {
  const MonetizationConfig({
    required this.adsEnabled,
    required this.bannerAdsEnabled,
    required this.interstitialAdsEnabled,
    required this.rewardedAdsEnabled,
    required this.appOpenAdsEnabled,
    required this.feedAdInterval,
    required this.interstitialMinIntervalSeconds,
    required this.interstitialMaxPerSession,
  });

  final bool adsEnabled;
  final bool bannerAdsEnabled;
  final bool interstitialAdsEnabled;
  final bool rewardedAdsEnabled;
  final bool appOpenAdsEnabled;
  final int feedAdInterval;
  final int interstitialMinIntervalSeconds;
  final int interstitialMaxPerSession;

  /// The fail-safe default (spec §5): if the config can't be fetched at all (offline, backend
  /// unreachable), ads stay OFF rather than guessing — a missing ad slot is invisible, a
  /// misconfigured one is a policy/UX risk.
  static const disabled = MonetizationConfig(
    adsEnabled: false,
    bannerAdsEnabled: false,
    interstitialAdsEnabled: false,
    rewardedAdsEnabled: false,
    appOpenAdsEnabled: false,
    feedAdInterval: 6,
    interstitialMinIntervalSeconds: 480,
    interstitialMaxPerSession: 3,
  );

  factory MonetizationConfig.fromJson(Map<String, dynamic> json) => MonetizationConfig(
        adsEnabled: json["ads_enabled"] as bool? ?? false,
        bannerAdsEnabled: json["banner_ads_enabled"] as bool? ?? false,
        interstitialAdsEnabled: json["interstitial_ads_enabled"] as bool? ?? false,
        rewardedAdsEnabled: json["rewarded_ads_enabled"] as bool? ?? false,
        // Always forced false regardless of what the backend says (spec §2: "keep
        // APP_OPEN_ADS_ENABLED=false by default... do not enable app-open ads during this
        // phase") — no code path in this app requests one, so this is a defense-in-depth
        // guarantee, not just a default.
        appOpenAdsEnabled: false,
        feedAdInterval: (json["feed_ad_interval"] as num?)?.toInt() ?? 6,
        interstitialMinIntervalSeconds: (json["interstitial_min_interval_seconds"] as num?)?.toInt() ?? 480,
        interstitialMaxPerSession: (json["interstitial_max_per_session"] as num?)?.toInt() ?? 3,
      );

  bool isFormatEnabled(AdFormat format) {
    if (!adsEnabled) return false;
    return switch (format) {
      AdFormat.banner => bannerAdsEnabled,
      AdFormat.interstitial => interstitialAdsEnabled,
      AdFormat.rewarded => rewardedAdsEnabled,
      AdFormat.appOpen => appOpenAdsEnabled, // always false — see above.
    };
  }
}

class Entitlement {
  const Entitlement({
    required this.tier,
    required this.isPro,
    required this.shouldShowAds,
    required this.canUseUnlimitedAts,
    required this.canUseUnlimitedAptitude,
    required this.canUseAdvancedAnalytics,
    required this.atsUsedToday,
    required this.atsDailyLimit,
    required this.atsRemainingToday,
    required this.aptitudeUsedToday,
    required this.aptitudeDailyLimit,
    required this.aptitudeRemainingToday,
  });

  final String tier;
  final bool isPro;
  final bool shouldShowAds;
  final bool canUseUnlimitedAts;
  final bool canUseUnlimitedAptitude;
  final bool canUseAdvancedAnalytics;
  final int atsUsedToday;
  final int? atsDailyLimit;
  final int? atsRemainingToday;
  final int aptitudeUsedToday;
  final int? aptitudeDailyLimit;
  final int? aptitudeRemainingToday;

  /// Fail-safe default if entitlement can't be fetched: assume FREE, but never show ads and
  /// never claim a limit was reached — a network hiccup must not block core career functionality
  /// (spec's "never lock basic career functionality" principle, applied to unknown state too).
  static const unknown = Entitlement(
    tier: "FREE",
    isPro: false,
    shouldShowAds: false,
    canUseUnlimitedAts: true,
    canUseUnlimitedAptitude: true,
    canUseAdvancedAnalytics: false,
    atsUsedToday: 0,
    atsDailyLimit: null,
    atsRemainingToday: null,
    aptitudeUsedToday: 0,
    aptitudeDailyLimit: null,
    aptitudeRemainingToday: null,
  );

  factory Entitlement.fromJson(Map<String, dynamic> json) => Entitlement(
        tier: json["tier"] as String? ?? "FREE",
        isPro: json["is_pro"] as bool? ?? false,
        shouldShowAds: json["should_show_ads"] as bool? ?? false,
        canUseUnlimitedAts: json["can_use_unlimited_ats"] as bool? ?? false,
        canUseUnlimitedAptitude: json["can_use_unlimited_aptitude"] as bool? ?? false,
        canUseAdvancedAnalytics: json["can_use_advanced_analytics"] as bool? ?? false,
        atsUsedToday: json["ats_used_today"] as int? ?? 0,
        atsDailyLimit: json["ats_daily_limit"] as int?,
        atsRemainingToday: json["ats_remaining_today"] as int?,
        aptitudeUsedToday: json["aptitude_used_today"] as int? ?? 0,
        aptitudeDailyLimit: json["aptitude_daily_limit"] as int?,
        aptitudeRemainingToday: json["aptitude_remaining_today"] as int?,
      );

  /// True only when a real (non-null, non-unlimited) limit is reported and it's exhausted.
  bool get aptitudeLimitReached => !canUseUnlimitedAptitude && (aptitudeRemainingToday ?? 1) <= 0;

  bool get atsLimitReached => !canUseUnlimitedAts && (atsRemainingToday ?? 1) <= 0;
}

class RewardUnlock {
  const RewardUnlock({required this.id, required this.rewardType, required this.referenceId});

  final String id;
  final RewardType rewardType;
  final String referenceId;

  factory RewardUnlock.fromJson(Map<String, dynamic> json) => RewardUnlock(
        id: json["id"] as String,
        rewardType: RewardType.values.firstWhere((r) => r.wireValue == json["reward_type"]),
        referenceId: json["reference_id"] as String,
      );
}
