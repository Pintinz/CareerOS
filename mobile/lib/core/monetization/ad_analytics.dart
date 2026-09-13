import "dart:developer" as developer;

import "ad_placement.dart";
import "monetization_models.dart";

/// Internal product-analytics abstraction (spec §31) — no Firebase dependency, no revenue claims.
/// The default implementation just logs; swap `AdAnalytics` for a real sink later (this app's
/// existing product-metrics store, if one is ever built) without touching any call site.
///
/// **Never logs** (spec §29): full ad request payloads, device advertising identifiers, or any
/// private CareerOS user data. Only ad type, placement, and a generic outcome category.
abstract class AdAnalytics {
  void track(AdAnalyticsEvent event, {required AdFormat format, required AdPlacement placement, String? reason});
}

class LoggingAdAnalytics implements AdAnalytics {
  const LoggingAdAnalytics();

  @override
  void track(AdAnalyticsEvent event, {required AdFormat format, required AdPlacement placement, String? reason}) {
    developer.log(
      "${event.name} format=${format.name} placement=${placement.name}${reason != null ? ' reason=$reason' : ''}",
      name: "careeros.ads",
    );
  }
}
