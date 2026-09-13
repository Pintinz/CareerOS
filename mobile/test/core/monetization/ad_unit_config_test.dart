import 'package:careeros/core/monetization/ad_unit_ids.dart';
import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AdUnitConfig', () {
    test('a non-production build always resolves to a real (Google test) ad unit id', () {
      const config = AdUnitConfig(
        androidProductionAppId: '',
        iosProductionAppId: '',
        androidProductionUnitIds: {},
        iosProductionUnitIds: {},
        isProductionBuild: false,
      );
      expect(config.resolve(AdFormat.banner), isNotNull);
      expect(config.resolve(AdFormat.banner), isNotEmpty);
    });

    test('a production build with no configured production id fails safe (disables), never falls back to test ads', () {
      const config = AdUnitConfig(
        androidProductionAppId: '',
        iosProductionAppId: '',
        androidProductionUnitIds: {},
        iosProductionUnitIds: {},
        isProductionBuild: true,
      );
      expect(config.resolve(AdFormat.banner), isNull);
      expect(config.resolve(AdFormat.interstitial), isNull);
      expect(config.resolve(AdFormat.rewarded), isNull);
    });

    test('a production build with a configured production id uses it', () {
      const config = AdUnitConfig(
        androidProductionAppId: 'ca-app-pub-real~123',
        iosProductionAppId: 'ca-app-pub-real~456',
        androidProductionUnitIds: {AdFormat.banner: 'ca-app-pub-real/banner'},
        iosProductionUnitIds: {AdFormat.banner: 'ca-app-pub-real/banner-ios'},
        isProductionBuild: true,
      );
      // Whichever platform the test runner reports, resolve() must return a real, non-test id.
      final resolved = config.resolve(AdFormat.banner);
      expect(resolved, isNotNull);
      expect(resolved, isNot(contains('3940256099942544'))); // never Google's test publisher id.
    });
  });
}
