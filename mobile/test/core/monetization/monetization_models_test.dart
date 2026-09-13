import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MonetizationConfig', () {
    test('app open ads are always forced false regardless of the server value (spec §2/§22)', () {
      final config = MonetizationConfig.fromJson({
        'ads_enabled': true,
        'banner_ads_enabled': true,
        'interstitial_ads_enabled': true,
        'rewarded_ads_enabled': true,
        'app_open_ads_enabled': true, // even if a compromised/misconfigured backend sent true
        'feed_ad_interval': 6,
        'interstitial_min_interval_seconds': 480,
        'interstitial_max_per_session': 3,
      });
      expect(config.appOpenAdsEnabled, isFalse);
      expect(config.isFormatEnabled(AdFormat.appOpen), isFalse);
    });

    test('a disabled global kill switch disables every format even if individually enabled', () {
      final config = MonetizationConfig.fromJson({
        'ads_enabled': false,
        'banner_ads_enabled': true,
        'interstitial_ads_enabled': true,
        'rewarded_ads_enabled': true,
        'app_open_ads_enabled': false,
        'feed_ad_interval': 6,
        'interstitial_min_interval_seconds': 480,
        'interstitial_max_per_session': 3,
      });
      expect(config.isFormatEnabled(AdFormat.banner), isFalse);
      expect(config.isFormatEnabled(AdFormat.interstitial), isFalse);
      expect(config.isFormatEnabled(AdFormat.rewarded), isFalse);
    });

    test('disabled fail-safe default requests nothing', () {
      expect(MonetizationConfig.disabled.adsEnabled, isFalse);
      expect(MonetizationConfig.disabled.isFormatEnabled(AdFormat.banner), isFalse);
    });
  });

  group('Entitlement', () {
    test('Pro users never hit a limit even with used-up counters', () {
      const entitlement = Entitlement(
        tier: 'PRO',
        isPro: true,
        shouldShowAds: false,
        canUseUnlimitedAts: true,
        canUseUnlimitedAptitude: true,
        canUseAdvancedAnalytics: true,
        atsUsedToday: 99,
        atsDailyLimit: null,
        atsRemainingToday: null,
        aptitudeUsedToday: 99,
        aptitudeDailyLimit: null,
        aptitudeRemainingToday: null,
      );
      expect(entitlement.aptitudeLimitReached, isFalse);
      expect(entitlement.atsLimitReached, isFalse);
    });

    test('Free user with zero remaining aptitude sessions is limit-reached', () {
      const entitlement = Entitlement(
        tier: 'FREE',
        isPro: false,
        shouldShowAds: true,
        canUseUnlimitedAts: false,
        canUseUnlimitedAptitude: false,
        canUseAdvancedAnalytics: false,
        atsUsedToday: 3,
        atsDailyLimit: 3,
        atsRemainingToday: 0,
        aptitudeUsedToday: 1,
        aptitudeDailyLimit: 1,
        aptitudeRemainingToday: 0,
      );
      expect(entitlement.aptitudeLimitReached, isTrue);
      expect(entitlement.atsLimitReached, isTrue);
    });

    test('unknown fail-safe default never claims a limit was reached', () {
      expect(Entitlement.unknown.aptitudeLimitReached, isFalse);
      expect(Entitlement.unknown.atsLimitReached, isFalse);
      expect(Entitlement.unknown.shouldShowAds, isFalse);
    });
  });
}
