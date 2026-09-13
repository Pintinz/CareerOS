/// Centralized interstitial pacing (spec §19) — the only place that decides "is it too soon to
/// show another interstitial." No screen makes this decision on its own.
///
/// All limits are injected (from `MonetizationConfig`, itself admin-configurable via the existing
/// system-settings architecture) rather than hardcoded, per spec §19's "keep all limits
/// configurable." A fresh controller resets `sessionInterstitialCount` — the cap is per app
/// session, not per calendar day.
class AdFrequencyController {
  AdFrequencyController({
    required this.minIntervalSeconds,
    required this.maxPerSession,
    DateTime Function()? now,
  }) : _now = now ?? DateTime.now;

  final int minIntervalSeconds;
  final int maxPerSession;
  final DateTime Function() _now;

  DateTime? _lastInterstitialShownAt;
  int _sessionInterstitialCount = 0;

  DateTime? get lastInterstitialShownAt => _lastInterstitialShownAt;
  int get sessionInterstitialCount => _sessionInterstitialCount;

  /// True only when every rule (session cap, minimum interval) is satisfied. Never optimizes for
  /// maximum impressions (spec §19) — when in doubt, this returns false.
  bool canShowInterstitial() {
    if (_sessionInterstitialCount >= maxPerSession) return false;
    final last = _lastInterstitialShownAt;
    if (last == null) return true;
    return _now().difference(last).inSeconds >= minIntervalSeconds;
  }

  /// Call only after an interstitial actually displayed (not merely loaded) — see AdService.
  void recordShown() {
    _lastInterstitialShownAt = _now();
    _sessionInterstitialCount += 1;
  }

  void resetSession() {
    _lastInterstitialShownAt = null;
    _sessionInterstitialCount = 0;
  }
}
