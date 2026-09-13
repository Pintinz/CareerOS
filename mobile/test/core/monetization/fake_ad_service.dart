import 'package:careeros/core/monetization/ad_placement.dart';
import 'package:careeros/core/monetization/ad_service.dart';
import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// Test double for [AdService] — mirrors the fake-`RecordingService` pattern used for interview
/// recording tests (Phase 7.5): no real platform channel is ever touched, and every outcome is
/// controllable so tests can assert exact behavior for success/failure/duplicate-call cases.
class FakeAdService implements AdService {
  bool initializeCalled = false;
  bool rewardedResult = false;
  int showRewardedCallCount = 0;
  bool interstitialAllowed = true;
  int interstitialShownCount = 0;
  BannerAd? bannerToReturn;

  @override
  Future<void> initialize() async {
    initializeCalled = true;
  }

  @override
  Future<bool> canRequestAd(AdFormat format) async => true;

  @override
  bool canShowInterstitialNow() => interstitialAllowed;

  @override
  void recordInterstitialShown() => interstitialShownCount++;

  @override
  Future<BannerAd?> loadBanner({required AdPlacement placement, required AdSize size}) async {
    return bannerToReturn;
  }

  @override
  Future<bool> showRewarded({required AdPlacement placement, required RewardType rewardType}) async {
    showRewardedCallCount++;
    return rewardedResult;
  }

  int maybeShowInterstitialCallCount = 0;

  @override
  Future<void> maybeShowInterstitial({required AdPlacement placement}) async {
    maybeShowInterstitialCallCount++;
  }

  @override
  Future<void> dispose() async {}
}
