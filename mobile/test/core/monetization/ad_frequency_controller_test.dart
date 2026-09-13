import 'package:careeros/core/monetization/ad_frequency_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AdFrequencyController', () {
    test('allows the first interstitial with no prior history', () {
      final controller = AdFrequencyController(minIntervalSeconds: 480, maxPerSession: 3);
      expect(controller.canShowInterstitial(), isTrue);
    });

    test('blocks another interstitial before the minimum interval has elapsed', () {
      var now = DateTime(2026, 1, 1, 12, 0, 0);
      final controller = AdFrequencyController(minIntervalSeconds: 480, maxPerSession: 3, now: () => now);

      controller.recordShown();
      now = now.add(const Duration(seconds: 100));
      expect(controller.canShowInterstitial(), isFalse);

      now = now.add(const Duration(seconds: 400)); // total 500s, past the 480s minimum
      expect(controller.canShowInterstitial(), isTrue);
    });

    test('blocks once the per-session cap is reached, even after the interval passes', () {
      var now = DateTime(2026, 1, 1, 12, 0, 0);
      final controller = AdFrequencyController(minIntervalSeconds: 1, maxPerSession: 2, now: () => now);

      controller.recordShown();
      now = now.add(const Duration(seconds: 10));
      expect(controller.canShowInterstitial(), isTrue);

      controller.recordShown();
      now = now.add(const Duration(seconds: 10));
      expect(controller.canShowInterstitial(), isFalse);
    });

    test('resetSession clears both the count and the last-shown timestamp', () {
      var now = DateTime(2026, 1, 1, 12, 0, 0);
      final controller = AdFrequencyController(minIntervalSeconds: 480, maxPerSession: 1, now: () => now);

      controller.recordShown();
      expect(controller.canShowInterstitial(), isFalse);

      controller.resetSession();
      expect(controller.canShowInterstitial(), isTrue);
      expect(controller.sessionInterstitialCount, 0);
      expect(controller.lastInterstitialShownAt, isNull);
    });
  });
}
