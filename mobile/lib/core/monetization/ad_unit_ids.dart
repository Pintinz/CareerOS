import "dart:io" show Platform;

import "monetization_models.dart";

/// Google's own official public test ad units (documented at
/// developers.google.com/admob/flutter/test-ads) — never a real publisher's inventory. These are
/// intentionally hardcoded: they are not secrets, they are Google's published constant test IDs,
/// the same for every AdMob developer in the world.
///
/// The App IDs themselves (same test values: `ca-app-pub-3940256099942544~3347511713` Android,
/// `ca-app-pub-3940256099942544~1458002511` iOS) are configured natively, not through this Dart
/// API — see `android/app/src/main/AndroidManifest.xml`'s
/// `com.google.android.gms.ads.APPLICATION_ID` meta-data and `ios/Runner/Info.plist`'s
/// `GADApplicationIdentifier`.
class _TestAdUnitIds {
  static const androidBanner = "ca-app-pub-3940256099942544/6300978111";
  static const androidInterstitial = "ca-app-pub-3940256099942544/1033173712";
  static const androidRewarded = "ca-app-pub-3940256099942544/5224354917";
  static const androidAppOpen = "ca-app-pub-3940256099942544/9257395921";

  static const iosBanner = "ca-app-pub-3940256099942544/2934735716";
  static const iosInterstitial = "ca-app-pub-3940256099942544/4411468910";
  static const iosRewarded = "ca-app-pub-3940256099942544/1712485313";
  static const iosAppOpen = "ca-app-pub-3940256099942544/5662855259";
}

/// Resolves the ad unit id to actually request, per platform and format (spec §4).
///
/// **Fail-safe by design (spec §5)**: a real production ad unit id is only used when the app was
/// actually built with one via `--dart-define` AND the build is a genuine production build. A
/// production build with no production ad unit configured does **not** fall back to Google's test
/// units (that would risk shipping test-ad traffic as "real" inventory, or — worse — could look
/// like accidental test-ad-in-production if reversed) — it disables that ad format outright. See
/// `AdUnitConfig.resolve`.
class AdUnitConfig {
  const AdUnitConfig({
    required this.androidProductionAppId,
    required this.iosProductionAppId,
    required this.androidProductionUnitIds,
    required this.iosProductionUnitIds,
    required this.isProductionBuild,
  });

  final String androidProductionAppId;
  final String iosProductionAppId;
  final Map<AdFormat, String> androidProductionUnitIds;
  final Map<AdFormat, String> iosProductionUnitIds;
  final bool isProductionBuild;

  /// Reads production values from `--dart-define` (never hardcoded source, spec §4). Empty
  /// strings mean "not configured".
  factory AdUnitConfig.fromEnvironment({required bool isProductionBuild}) {
    return AdUnitConfig(
      isProductionBuild: isProductionBuild,
      androidProductionAppId: const String.fromEnvironment("ADMOB_ANDROID_APP_ID"),
      iosProductionAppId: const String.fromEnvironment("ADMOB_IOS_APP_ID"),
      androidProductionUnitIds: const {
        AdFormat.banner: String.fromEnvironment("ADMOB_ANDROID_BANNER_UNIT_ID"),
        AdFormat.interstitial: String.fromEnvironment("ADMOB_ANDROID_INTERSTITIAL_UNIT_ID"),
        AdFormat.rewarded: String.fromEnvironment("ADMOB_ANDROID_REWARDED_UNIT_ID"),
        AdFormat.appOpen: String.fromEnvironment("ADMOB_ANDROID_APP_OPEN_UNIT_ID"),
      },
      iosProductionUnitIds: const {
        AdFormat.banner: String.fromEnvironment("ADMOB_IOS_BANNER_UNIT_ID"),
        AdFormat.interstitial: String.fromEnvironment("ADMOB_IOS_INTERSTITIAL_UNIT_ID"),
        AdFormat.rewarded: String.fromEnvironment("ADMOB_IOS_REWARDED_UNIT_ID"),
        AdFormat.appOpen: String.fromEnvironment("ADMOB_IOS_APP_OPEN_UNIT_ID"),
      },
    );
  }

  bool get _isAndroid => Platform.isAndroid;

  /// Returns the ad unit id to request, or null if this format has no safe id to use (production
  /// build with nothing configured for it — see class docs).
  String? resolve(AdFormat format) {
    final testId = _isAndroid ? _androidTestId(format) : _iosTestId(format);
    if (!isProductionBuild) return testId;

    final productionId = (_isAndroid ? androidProductionUnitIds : iosProductionUnitIds)[format];
    if (productionId == null || productionId.isEmpty) return null; // fail-safe: disable, don't fall back.
    return productionId;
  }

  static String _androidTestId(AdFormat format) => switch (format) {
        AdFormat.banner => _TestAdUnitIds.androidBanner,
        AdFormat.interstitial => _TestAdUnitIds.androidInterstitial,
        AdFormat.rewarded => _TestAdUnitIds.androidRewarded,
        AdFormat.appOpen => _TestAdUnitIds.androidAppOpen,
      };

  static String _iosTestId(AdFormat format) => switch (format) {
        AdFormat.banner => _TestAdUnitIds.iosBanner,
        AdFormat.interstitial => _TestAdUnitIds.iosInterstitial,
        AdFormat.rewarded => _TestAdUnitIds.iosRewarded,
        AdFormat.appOpen => _TestAdUnitIds.iosAppOpen,
      };
}
