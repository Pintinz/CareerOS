/// Named ad slots (spec §30) — decouples analytics/frequency logic from widget names so a screen
/// can be renamed/refactored without losing its ad-placement identity.
enum AdPlacement {
  jobsFeed,
  scholarshipsFeed,
  intelligenceFeed,
  savedOpportunities,
  atsResults,
  aptitudeUnlock,
  atsUnlock,
}

/// Product events for internal analytics only (spec §31) — never presented as revenue metrics,
/// and does not require Firebase; see AdAnalytics.
enum AdAnalyticsEvent { requested, loaded, failed, impression, opened, closed, rewardGranted }
