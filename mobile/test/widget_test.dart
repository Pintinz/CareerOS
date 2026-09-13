// Smoke test: the app boots to the splash screen without throwing. Deeper navigation/auth-flow
// tests need a mocked ApiClient/SecureStorage and are a Next Task (see PROJECT_STATUS.md) — this
// just proves `flutter test` runs against our real app rather than the stock counter template.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:careeros/core/app_providers.dart';
import 'package:careeros/core/monetization/ad_service.dart';
import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:careeros/core/monetization/monetization_providers.dart';
import 'package:careeros/core/monetization/ad_placement.dart';
import 'package:careeros/core/storage/app_preferences.dart';
import 'package:careeros/main.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

class _FakeAppPreferences implements AppPreferences {
  @override
  bool get hasCompletedOnboarding => false;

  @override
  Future<void> setOnboardingComplete() async {}
}

/// A no-op AdService for widget tests (mirrors the fake-`RecordingService` pattern used for
/// interview recording tests) — `MobileAds.instance.initialize()` and the real UMP consent flow
/// both touch platform channels that don't exist under `flutter test`, so any test that boots the
/// full app must override `adServiceProvider` with this instead.
class _NoopAdService implements AdService {
  @override
  Future<void> initialize() async {}

  @override
  Future<bool> canRequestAd(AdFormat format) async => false;

  @override
  bool canShowInterstitialNow() => false;

  @override
  void recordInterstitialShown() {}

  @override
  Future<BannerAd?> loadBanner({required AdPlacement placement, required AdSize size}) async => null;

  @override
  Future<bool> showRewarded({required AdPlacement placement, required RewardType rewardType}) async => false;

  @override
  Future<void> maybeShowInterstitial({required AdPlacement placement}) async {}

  @override
  Future<void> dispose() async {}
}

void main() {
  testWidgets('App boots to the splash screen', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appPreferencesProvider.overrideWithValue(_FakeAppPreferences()),
          adServiceProvider.overrideWithValue(_NoopAdService()),
        ],
        child: const CareerOSApp(),
      ),
    );

    expect(find.text('CareerOS'), findsOneWidget);
  });
}
