import "dart:async";

import "package:google_mobile_ads/google_mobile_ads.dart";

/// Wraps Google's own User Messaging Platform (UMP) consent SDK (spec §23: "do not invent a
/// homemade GDPR consent dialog instead of the proper consent mechanism"). CareerOS never renders
/// its own consent UI — `ConsentForm.loadAndShowConsentFormIfRequired` and
/// `ConsentForm.showPrivacyOptionsForm` are Google-rendered, Google-certified surfaces.
abstract class ConsentManager {
  /// Requests the latest consent info and shows Google's consent form if (and only if) required
  /// for this user/region. Resolves once the app is safe to proceed — either because consent
  /// wasn't required, was already obtained, or was just collected. **The core app must never be
  /// gated on the result** (spec §49: "Core app must always remain available") — this only
  /// affects whether ad requests may be personalized/made at all.
  Future<void> gatherConsent({bool debugForceEea = false});

  /// Whether ads may be requested at all right now (spec: "Ads must not become a hard
  /// dependency" for the rest of the app; this only governs `AdService`'s own behavior).
  Future<bool> canRequestAds();

  /// Whether Settings → Ads & Privacy must show a "Privacy Options" entry point (spec §24).
  Future<bool> isPrivacyOptionsRequired();

  /// Opens Google's own privacy-options form so the user can revisit their choice (spec §24).
  Future<void> showPrivacyOptionsForm();
}

class UmpConsentManager implements ConsentManager {
  @override
  Future<void> gatherConsent({bool debugForceEea = false}) {
    final completer = Completer<void>();
    final params = ConsentRequestParameters(
      consentDebugSettings: debugForceEea
          ? ConsentDebugSettings(debugGeography: DebugGeography.debugGeographyEea)
          : null,
    );

    ConsentInformation.instance.requestConsentInfoUpdate(
      params,
      () async {
        try {
          await ConsentForm.loadAndShowConsentFormIfRequired((formError) {
            // A form-show failure (spec §49 "form failure") must not block the app — the caller
            // proceeds exactly as if no consent form were needed; AdService separately checks
            // `canRequestAds()` before ever loading an ad.
            if (!completer.isCompleted) completer.complete();
          });
          if (!completer.isCompleted) completer.complete();
        } catch (_) {
          if (!completer.isCompleted) completer.complete();
        }
      },
      (formError) {
        if (!completer.isCompleted) completer.complete();
      },
    );
    return completer.future;
  }

  @override
  Future<bool> canRequestAds() => ConsentInformation.instance.canRequestAds();

  @override
  Future<bool> isPrivacyOptionsRequired() async {
    final status = await ConsentInformation.instance.getPrivacyOptionsRequirementStatus();
    return status == PrivacyOptionsRequirementStatus.required;
  }

  @override
  Future<void> showPrivacyOptionsForm() {
    final completer = Completer<void>();
    ConsentForm.showPrivacyOptionsForm((formError) {
      completer.complete();
    });
    return completer.future;
  }
}
