import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:careeros/core/monetization/monetization_providers.dart';
import 'package:careeros/features/aptitude/presentation/test_configuration_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../core/monetization/fake_ad_service.dart';
import '../../test_utils.dart';
import 'aptitude_test_support.dart';

const _limitReached = Entitlement(
  tier: 'FREE',
  isPro: false,
  shouldShowAds: true,
  canUseUnlimitedAts: false,
  canUseUnlimitedAptitude: false,
  canUseAdvancedAnalytics: false,
  atsUsedToday: 0,
  atsDailyLimit: 3,
  atsRemainingToday: 3,
  aptitudeUsedToday: 1,
  aptitudeDailyLimit: 1,
  aptitudeRemainingToday: 0,
);

Widget _wrap(List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const TestConfigurationScreen(args: AptitudeConfigureArgs()),
    ),
    GoRoute(
      path: '/prepare/aptitude/sessions/:id',
      builder: (context, state) => Scaffold(body: Text('Active test: ${state.pathParameters['id']}')),
    ),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

void main() {
  testWidgets(
    'Daily aptitude limit reached offers a rewarded unlock, and a successful watch starts the test',
    (tester) async {
      useLargeTestViewport(tester);
      final repo = FakeAptitudeRepository();
      final baseOverrides = await aptitudeTestOverrides(repository: repo);
      final fakeAdService = FakeAdService()..rewardedResult = true;

      await tester.pumpWidget(_wrap([
        ...baseOverrides,
        entitlementProvider.overrideWith((ref) async => _limitReached),
        adServiceProvider.overrideWithValue(fakeAdService),
      ]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Start Assessment'));
      await tester.pumpAndSettle();

      // The rewarded-unlock dialog appeared (spec §15's exact copy) rather than silently
      // starting or silently blocking.
      expect(find.text('Daily free limit reached'), findsOneWidget);
      expect(find.text('Watch Ad & Unlock'), findsOneWidget);

      await tester.tap(find.text('Watch Ad & Unlock'));
      await tester.pumpAndSettle();

      // Exactly one ad watch was requested, and the test session was created/started afterward.
      expect(fakeAdService.showRewardedCallCount, 1);
      expect(find.textContaining('Active test:'), findsOneWidget);
    },
  );

  testWidgets(
    'A failed rewarded ad grants nothing and does not start a session',
    (tester) async {
      useLargeTestViewport(tester);
      final repo = FakeAptitudeRepository();
      final baseOverrides = await aptitudeTestOverrides(repository: repo);
      final fakeAdService = FakeAdService()..rewardedResult = false;

      await tester.pumpWidget(_wrap([
        ...baseOverrides,
        entitlementProvider.overrideWith((ref) async => _limitReached),
        adServiceProvider.overrideWithValue(fakeAdService),
      ]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Start Assessment'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Watch Ad & Unlock'));
      await tester.pumpAndSettle();

      // Never grants a reward merely because the ad was attempted — only the earned-reward
      // callback would (fakeAdService.rewardedResult mirrors that here).
      expect(fakeAdService.showRewardedCallCount, 1);
      expect(find.textContaining('Active test:'), findsNothing);
      expect(find.textContaining("couldn't be completed"), findsOneWidget);
    },
  );

  testWidgets(
    'Choosing "Come Back Tomorrow" never requests an ad and never starts a session',
    (tester) async {
      useLargeTestViewport(tester);
      final repo = FakeAptitudeRepository();
      final baseOverrides = await aptitudeTestOverrides(repository: repo);
      final fakeAdService = FakeAdService();

      await tester.pumpWidget(_wrap([
        ...baseOverrides,
        entitlementProvider.overrideWith((ref) async => _limitReached),
        adServiceProvider.overrideWithValue(fakeAdService),
      ]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Start Assessment'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Come Back Tomorrow'));
      await tester.pumpAndSettle();

      expect(fakeAdService.showRewardedCallCount, 0);
      expect(find.textContaining('Active test:'), findsNothing);
    },
  );
}
