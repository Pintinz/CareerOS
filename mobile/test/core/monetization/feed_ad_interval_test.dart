import 'package:careeros/core/monetization/feed_ad_interval.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('adSlotPositionsForFeed', () {
    test('inserts no ad slot when the feed is shorter than the interval', () {
      expect(adSlotPositionsForFeed(itemCount: 4, interval: 6), isEmpty);
    });

    test('inserts one slot after every `interval` items, never a trailing one', () {
      // 14 items, interval 6 -> slots after item 6 and item 12; never after item 14 (the end).
      expect(adSlotPositionsForFeed(itemCount: 14, interval: 6), [6, 12]);
    });

    test('an exact multiple of the interval does not add a trailing ad after the last item', () {
      expect(adSlotPositionsForFeed(itemCount: 12, interval: 6), [6]);
    });

    test('a non-positive interval disables ad insertion entirely', () {
      expect(adSlotPositionsForFeed(itemCount: 100, interval: 0), isEmpty);
    });
  });
}
