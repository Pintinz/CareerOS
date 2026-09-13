# CareerOS — Monetization & AdMob Architecture

Phase 10. Covers AdMob integration, ad formats, placements, forbidden contexts, the reward
ledger, the Free/Pro entitlement architecture, privacy/consent, and production readiness.

**Nothing in this document should be read as "monetization is live."** Every ad request in this
environment uses Google's own official public test ad units. No real AdMob account, no real ad
unit, no real revenue exists anywhere in this project. See "Production readiness" at the end of
this document for the precise, honest gap between what's built and what real production serving
requires.

## 1. Monetization principle

CareerOS monetizes attention at natural pauses and browse surfaces — never inside a workflow the
user came to the app to actually complete. The following are hard-coded absences, not
configuration: no ad code exists anywhere in the aptitude test session, the interview session
(including audio recording), STAR story editing, application stage confirmation, recruitment
email review, CV upload, document upload, profile editing, or authentication screens. See
"Forbidden contexts" below.

## 2. Architecture overview

```
lib/core/monetization/
  monetization_models.dart      MonetizationConfig, Entitlement, RewardType — pure data
  monetization_repository.dart  talks to /monetization/* backend endpoints
  monetization_providers.dart   Riverpod wiring (config, entitlement, consent, AdService)
  ad_unit_ids.dart               AdUnitConfig — test vs production ad unit resolution
  ad_placement.dart              AdPlacement / AdAnalyticsEvent enums
  ad_analytics.dart              AdAnalytics abstraction (no Firebase dependency)
  ad_frequency_controller.dart   AdFrequencyController — interstitial pacing, pure logic
  consent_manager.dart           ConsentManager — wraps Google's real UMP SDK
  ad_service.dart                AdService — the ONE abstraction every screen uses
  feed_ad_interval.dart          pure helper: which list positions get an ad slot
  widgets/
    banner_ad_slot.dart          anchored adaptive banner, graceful failure collapse
    rewarded_unlock_dialog.dart  the spec's exact "Watch Ad & Unlock" flow
```

No screen anywhere constructs a `BannerAd`, `InterstitialAd`, or `RewardedAd` directly — every ad
request goes through `AdService`, obtained via `adServiceProvider`. This is enforced by
convention (there is exactly one file, `ad_service.dart`, that imports the raw
`google_mobile_ads` ad classes for loading purposes; `banner_ad_slot.dart` only renders an
already-loaded `BannerAd` handed to it by `AdService`).

Backend (`backend/app/`):
```
models/monetization.py           RewardUnlock, RewardType
repositories/monetization_repository.py
services/monetization_service.py  entitlement computation, reward claim (idempotent)
schemas/monetization.py
api/v1/monetization.py           GET /config, GET /entitlement, POST /rewards/claim
```
Reuses Phase 9's `system_settings` table for `monetization_config` and `free_tier_limits` — no
new admin UI was needed; both keys are automatically editable at Settings → System Settings by a
SUPER_ADMIN, exactly like every other setting.

## 3. Supported ad formats

| Format | Status | Package API |
|---|---|---|
| Adaptive Banner | Implemented | `AdService.loadBanner` → `BannerAdSlot` widget |
| Rewarded | Implemented | `AdService.showRewarded` → `showRewardedUnlockDialog` |
| Interstitial | Implemented, frequency-capped | `AdService.maybeShowInterstitial` |
| App Open | Architecture only, **disabled** | `AdFormat.appOpen` exists; `MonetizationConfig.appOpenAdsEnabled` is hardcoded `false` in `MonetizationConfig.fromJson` regardless of what the backend returns — a defense-in-depth guarantee, not just a default. No screen calls it. |

`google_mobile_ads: ^9.1.0` (already present in `pubspec.yaml` — the current stable release at
the time of this phase, not an obsolete pin) provides all of the above plus the bundled UMP
(User Messaging Platform) consent SDK.

`MobileAds.instance.initialize()` runs once, in `CareerOSApp.initState()`, fire-and-forget
(`unawaited`) — an initialization failure is caught internally by `AdService.initialize()` and
never prevents the app from launching or rendering its first frame.

## 4. Test ads in development

`AdUnitConfig` (`lib/core/monetization/ad_unit_ids.dart`) hardcodes Google's own published public
test ad unit IDs (documented at developers.google.com/admob/flutter/test-ads — the same constant
values for every AdMob developer, never a real publisher's inventory):

| Format | Android test unit | iOS test unit |
|---|---|---|
| App ID | `ca-app-pub-3940256099942544~3347511713` | `ca-app-pub-3940256099942544~1458002511` |
| Banner | `ca-app-pub-3940256099942544/6300978111` | `ca-app-pub-3940256099942544/2934735716` |
| Interstitial | `ca-app-pub-3940256099942544/1033173712` | `ca-app-pub-3940256099942544/4411468910` |
| Rewarded | `ca-app-pub-3940256099942544/5224354917` | `ca-app-pub-3940256099942544/1712485313` |
| App Open | `ca-app-pub-3940256099942544/9257395921` | `ca-app-pub-3940256099942544/5662855259` |

The App IDs are also set natively: `android/app/src/main/AndroidManifest.xml`'s
`com.google.android.gms.ads.APPLICATION_ID` meta-data, and `ios/Runner/Info.plist`'s
`GADApplicationIdentifier` — both currently hold the test App ID above. **Both must be replaced
with real values from a real AdMob account before any production release.**

**Fail-safe production configuration** (`AdUnitConfig.resolve`): when the app is built as a
genuine production build (`Env.isProduction`), a format with no real ad unit id configured via
`--dart-define` (`ADMOB_ANDROID_BANNER_UNIT_ID` etc.) is **disabled outright** — it never falls
back to Google's test units. This is deliberate: test-ad traffic must never accidentally ship as
"real" monetized inventory, and the reverse (a misconfigured production build silently serving
nothing) is the safer failure mode. Covered by
`test/core/monetization/ad_unit_config_test.dart`.

## 5. Feature flags

All flags are read from `GET /monetization/config`, backed by the `monetization_config`
system-setting (admin-editable, non-secret):

```
ads_enabled                          — global kill switch (spec §40)
banner_ads_enabled
interstitial_ads_enabled
rewarded_ads_enabled
app_open_ads_enabled                 — always forced false client-side regardless of this value
feed_ad_interval                     — e.g. 6 = one ad slot per 6 feed items
interstitial_min_interval_seconds    — e.g. 480 (8 minutes)
interstitial_max_per_session         — e.g. 3
```

`free_tier_limits` (separate setting): `ats_daily`, `aptitude_daily`.

If the config fetch fails entirely (offline, backend down), the app falls back to
`MonetizationConfig.disabled` — ads OFF, never guessed as on. `ADS_DEBUG_MODE` is implicit in
`Env.isProduction == false`: every non-production build uses test ad units by construction (see
§4), so a separate debug flag was not needed on top of that.

## 6. Central AdService

`AdService` (abstract) / `GoogleMobileAdsService` (real implementation) is the one class that:
initializes the SDK, checks consent state, resolves the correct ad unit id per format/platform,
loads/shows each format, enforces interstitial frequency limits via `AdFrequencyController`,
checks entitlement (Pro → zero ad requests), and handles every failure without throwing. Tests
use a hand-written `FakeAdService` (mirrors the `RecordingService` fake-subclass pattern from
Phase 7.5) rather than mocking the real SDK, since `MobileAds.instance.initialize()` and the real
UMP consent flow both open real platform channels that don't exist under `flutter test`.

## 7. Entitlement architecture

`Entitlement` (`GET /monetization/entitlement`) reports: `tier` (`FREE`/`PRO`), `isPro`,
`shouldShowAds`, `canUseUnlimitedAts`, `canUseUnlimitedAptitude`, `canUseAdvancedAnalytics`, and
today's usage/remaining counts for ATS analyses and aptitude tests.

Backend (`app/models/user.py`): `User.subscription_tier` (`SubscriptionTier.FREE`/`PRO`,
persisted, defaults to `FREE` for everyone) and `entitlement_expires_at` (nullable, unused today
— exists so a future subscription can set it without a schema change). **No `if user.email ==
...` shortcut exists anywhere** — every user is `FREE` unless the persisted column says
otherwise, and nothing in this codebase currently sets it to `PRO` (no payment processing exists
— see §10).

**Time-zone policy** (explicit, per spec §54): "today" is always the current **UTC calendar day**.
CareerOS doesn't store a user's local timezone, so UTC is the only universally-correct choice.
Usage is computed as a live date-window query against `AtsAnalysis`/`TestSession` (`created_at >=
start of UTC day`) — **there is no reset job anywhere**, because there is nothing to reset; the
window simply moves forward every day on its own.

## 8. Free tier

Defaults (`free_tier_limits`, admin-editable): 3 ATS analyses/day, 1 aptitude test/day. A reward
unlock (§9) widens that day's effective limit by exactly one, until the reward expires (24h) or
the UTC day rolls over, whichever comes first.

**Important, honest scoping note**: the backend computes and reports usage/remaining accurately
and is authoritative for *reporting*, but does **not yet hard-block** creating a new
`AtsAnalysis`/`TestSession` once the limit is exhausted — `AtsService.analyze()` and
`AptitudeService.create_session()` were not modified to enforce this. This was a deliberate
scoping decision: both services have extensive existing test coverage built around unlimited
creation, and adding a new blocking rule to them risked destabilizing well-tested core flows for
a phase whose brief explicitly said "may support" limits and warned against enforcing "arbitrary
restrictive limits" without full centralization. The mobile app enforces the *intended* UX (the
rewarded-unlock soft-gate before starting a new aptitude test, see §9) at the natural point, but a
determined client calling the API directly could bypass it today. Hard enforcement (calling
`RewardUnlockRepository.mark_used` and rejecting over-limit requests) is prepared for — the
repository method exists and is documented — but not wired in. This is a real, tracked gap, not a
misrepresentation of what's built.

## 9. Rewarded ads and the reward ledger

The rewarded flow (spec §15's exact copy) lives in
`lib/core/monetization/widgets/rewarded_unlock_dialog.dart`, wired into the aptitude test
configuration screen (`test_configuration_screen.dart`'s `_start()`) as the reference
implementation:

```
Daily free limit reached
Want another practice session?
[Watch Ad & Unlock]   [Come Back Tomorrow]
```

Flow: user taps "Watch Ad & Unlock" → `AdService.showRewarded` loads and shows a real rewarded ad
→ **only** the SDK's `onUserEarnedReward` callback sets `earnedReward = true` (never "ad
loaded"/"ad started"/"ad dismissed" — those are tracked separately for analytics but never grant
anything) → on success, the client calls `POST /monetization/rewards/claim` with a freshly
generated `reference_id` → the backend inserts a `RewardUnlock` row.

**Reward ledger** (`reward_unlocks` table, `app/models/monetization.py`): `id`, `user_id`,
`reward_type` (`EXTRA_APTITUDE_TEST`/`EXTRA_ATS_ANALYSIS`/`PREMIUM_PRACTICE_SET`/
`ADVANCED_REPORT`), `granted_at`, `expires_at` (24h from grant), `source` (`"rewarded_ad"`),
`reference_id`, `used_at` (nullable, unused today — see §8's hard-enforcement note). A
`UniqueConstraint` on `reference_id` is the actual idempotency mechanism (spec §17): a duplicated
claim call for the same `reference_id` returns the existing row rather than inserting a second
one — enforced at the database level, not just application logic, matching this codebase's
established idempotency pattern (Phase 8's `recruitment_email_events` dedup, Phase 9's discovery
dedup). Covered by `test_duplicate_reward_reference_id_is_idempotent_not_double_granted` and
`test_another_users_reference_id_cannot_be_reused`.

**No AdMob server-side verification (SSV) exists.** This is the "mock verifier" spec §55
explicitly allows for development — the backend trusts that a claim call genuinely followed a
real earned-reward callback because the mobile client is only ever coded to call it from that
exact callback. A production deployment serving real ad revenue should add AdMob's SSV (a signed
callback from Google's ad servers to a backend endpoint) before trusting this path against real
money — tracked as a Phase 11 candidate, not attempted here.

## 10. Pro tier architecture

No purchase flow exists. `lib/features/settings/presentation/pro_screen.dart` shows the intended
feature set (no ads, unlimited ATS/aptitude, advanced analytics, premium interview content,
multiple-CV features) honestly labeled **"Coming Soon"** — no button that looks purchasable, and
explicit copy stating nothing on the screen will charge the user. `EntitlementService`'s role is
played by `Entitlement` + `entitlementProvider` + `MonetizationRepository` together (no separate
class was needed — the model itself answers `shouldShowAds`/`canUseUnlimitedAts`/etc.).

## 11-13. Banner ads, placement, and failure handling

`BannerAdSlot` (anchored adaptive banner) is wired into the jobs feed
(`job_list_tab.dart`) at a configurable interval (`feed_ad_interval`, default 6) via the pure
`adSlotPositionsForFeed` helper — an ad slot never appears before the first `interval` items and
never trails after the last item. Every banner slot renders a small "Advertisement" label above
it (spec §41-42 — never disguised as a job/scholarship/company post).

On any failure (disabled globally, Pro user, consent not obtained, SDK load failure), `BannerAdSlot`
renders `SizedBox.shrink()` — no blank fixed-height container, no stuck spinner, no layout hole.
Content around it is unaffected either way. Covered by
`test/features/jobs/job_feed_ads_test.dart` (interval placement, Pro-disables, globally-disabled)
and the pure `feed_ad_interval_test.dart`.

Scholarships and Company Intelligence feeds are architected for the same treatment
(`AdPlacement.scholarshipsFeed`/`.intelligenceFeed` already exist) but were not wired into their
list screens this phase — jobs is the reference implementation; extending the same three-line
pattern (`config`/`entitlement` watch + `adSlotPositionsForFeed` + `BannerAdSlot`) to the other
feeds is a small, low-risk follow-up, not attempted here to keep this phase's mobile diff focused.

## 14. Interstitial ads

`AdService.maybeShowInterstitial(placement)` is the only way to show one — it checks the
frequency controller, entitlement, config, and consent, in that order, before ever loading an ad;
any gate failing is a silent no-op. Wired into the ATS analyze screen
(`ats_analyze_screen.dart`) immediately after an analysis completes (spec §18's suggested
placement) — never before or during the analysis itself.

**`AdFrequencyController`** (`lib/core/monetization/ad_frequency_controller.dart`, pure and fully
unit-tested in `test/core/monetization/ad_frequency_controller_test.dart`): tracks
`lastInterstitialShownAt`, `sessionInterstitialCount`, and enforces both
`interstitialMinIntervalSeconds` (default 480s / 8 minutes) and `interstitialMaxPerSession`
(default 3) before allowing another interstitial. Resets each app session
(`AdService.dispose()`), not daily. Explicitly not optimized for maximum impressions — every
default favors under-showing over over-showing.

**Never placed**: opening an application, before Apply, during any test/session, immediately
after answering a question, between interview questions, when confirming a stage, when reading a
recruitment update, or after every navigation. None of these screens import
`ad_service.dart` for interstitial purposes — verified by inspection, and the two highest-stakes
ones (active aptitude/interview sessions) have a dedicated regression test (§18 below).

## 15. Never blocking Apply or recruitment updates

`openExternalUrl` (job/scholarship Apply links) has never been touched to add any ad
requirement — tapping Apply opens the external URL directly, exactly as before this phase.
Recruitment-event confirmation (`recruitment_event_detail_screen.dart`) and the "Prepare for
Aptitude/Interview" buttons it offers have zero ad-related code added this phase. This is a
structural guarantee (no code path exists to violate), not a runtime check.

## 16. App Open ads (prepared, disabled)

`AdFormat.appOpen` and its test/production ad unit ids exist in `AdUnitConfig` so a future phase
can wire it in without re-deriving the ID-resolution architecture, but:
- `MonetizationConfig.appOpenAdsEnabled` is hardcoded `false` regardless of the server value.
- No screen, lifecycle observer, or app-open-specific loading code exists anywhere.
- `AdService` has no `loadAppOpen`/`showAppOpen` method.

This is intentional per spec §22: CareerOS's users often open the app for a specific, time-
sensitive task (an interview, an assessment, a deadline), and degrading that first-launch moment
before real retention data justifies it is a real product risk, not just a policy checkbox.

## 17. Consent and privacy

`ConsentManager` (`lib/core/monetization/consent_manager.dart`) wraps Google's real UMP SDK
(`ConsentInformation`, `ConsentForm` — bundled in `google_mobile_ads` 9.1.0) end to end. **No
homemade consent dialog exists anywhere in this codebase.** `AdService.initialize()` calls
`gatherConsent()` before `MobileAds.instance.initialize()`; a consent-gathering failure (network,
form-load error) never blocks app launch or any core feature — it only means `AdService` treats
consent as not-yet-obtained and requests no ads until it resolves.

Settings → **Ads & Privacy** (`ads_privacy_screen.dart`) shows CareerOS Pro status, whether
advertising is currently active, and — only when
`ConsentInformation.instance.getPrivacyOptionsRequirementStatus()` reports it's required — a
"Privacy choices" entry that opens Google's own `ConsentForm.showPrivacyOptionsForm()`. No Google
internal identifier (consent string, ad ID, etc.) is ever displayed.

**iOS ATT** (`Info.plist`): `NSUserTrackingUsageDescription` is set with accurate wording, but
**no code anywhere calls `ATTrackingManager.requestTrackingAuthorization`** — CareerOS does not
request ATT simply because the app launched, per spec §26. If a future phase adds an ATT prompt
for ad personalization, this description is what iOS will show; until then the string is inert
preparation only. The app functions identically regardless of ATT status since no code path
depends on it.

## 18. Advertising and sensitive data

No ad-request code anywhere reads or transmits CV content, email content, application
history/rejections, interview recordings, medical-stage information, document contents, salary
data, or STAR stories — `AdRequest()` is constructed with no custom targeting parameters
whatsoever in every `AdService` call site. `AdAnalytics`/`LoggingAdAnalytics` only ever logs ad
type, placement, and a generic outcome category (never a full request payload, a device
advertising identifier, or any user data) — grep-verified, matching this codebase's existing
logging-audit discipline (see SYSTEM_AUDIT.md §36).

## 19. Forbidden contexts — explicit tests

`test/core/monetization/forbidden_contexts_test.dart` asserts `BannerAdSlot` (and by extension any
ad widget) is absent from the widget tree during an active aptitude test session and an active
interview session — the two screens where an ad would be most disruptive and most policy-risky.
Application stage confirmation, recruitment email review, CV upload, document vault, STAR editing,
and authentication screens were not given dedicated widget tests this phase (no ad code was ever
added to them, so there's nothing to regress), but are documented here as contexts that must
never gain ad code in any future phase without updating this document first.

## 20. Admin controls

Reuses Phase 9's system-settings architecture exactly (`GET/PUT /admin/settings/{key}`,
SUPER_ADMIN-only): `monetization_config` and `free_tier_limits` are two more entries in the same
generic JSON-editor Settings page — no new admin UI code was needed. Consistent with spec §39, the
admin UI never exposes or lets an admin change AdMob credentials, OAuth secrets, or signing
material — none of those live in `system_settings` at all; they stay in mobile build config /
native manifest files, which the admin app has no access to.

## 21. Database changes

- `users.subscription_tier` (`FREE`/`PRO`, default `FREE`), `users.entitlement_expires_at`
  (nullable).
- `reward_unlocks` table (see §9).
- `system_settings` gained two new keys (`monetization_config`, `free_tier_limits`) — no schema
  change, since `system_settings` is a generic key/JSON-value store.

Migration `9ad67addbcef` (revises Phase 9.5's `b2ff7f49cf7d`) — verified on a fresh empty SQLite
database with no manual intervention, using `server_default='FREE'` to backfill the new NOT NULL
`subscription_tier` column on any pre-existing `users` rows, then dropping that server default so
future inserts go through the ORM's Python-level default like every other column in this codebase.

## 22. Production readiness — what is and isn't verified

**Test-ad verified** (this phase): every ad format loads and behaves correctly against Google's
official test ad units, in development builds, on the code paths described above.

**Real-AdMob verified**: **NOT DONE.** No real AdMob account exists in this environment. No real
ad unit has ever served a real impression. No real revenue has ever been generated.

**Store/app-readiness verified**: **NOT DONE.** No app-ads.txt is hosted anywhere real (only
`app-ads.example.txt`, a placeholder-only reference document — see that file for the exact future
process). No Google Play or App Store listing exists. AdMob's own "app readiness" checklist has
never been run against this app.

These three are genuinely different things, and none of the first implies either of the other
two. Phase 11 is where real-AdMob and store/app-readiness verification belong — this phase
deliberately built and tested everything that *can* be verified without them.

### What Phase 11 will need
1. A real Google AdMob account and a real Android (and, once buildable, iOS) app registration.
2. Real ad units for banner/interstitial/rewarded (and app-open, only if a future phase decides
   to enable it) on both platforms, supplied via `--dart-define` at build time
   (`ADMOB_ANDROID_BANNER_UNIT_ID` etc. — see `ad_unit_ids.dart`).
3. Real App IDs in `AndroidManifest.xml`/`Info.plist`, replacing the test values currently there.
4. A real, owned, HTTPS-reachable developer domain to host `app-ads.txt` (see
   `app-ads.example.txt`) — a private/local address is explicitly insufficient (spec §36).
5. AdMob server-side reward verification (SSV) before trusting the reward-claim endpoint against
   real ad revenue (see §9).
6. Hard enforcement of free-tier usage limits at the API layer, if that product decision is made
   (see §8's honest scoping note).
7. A real payment/subscription integration before "CareerOS Pro" can be anything but "Coming
   Soon."
