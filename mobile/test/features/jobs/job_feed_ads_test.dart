import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:careeros/core/monetization/monetization_providers.dart';
import 'package:careeros/core/monetization/widgets/banner_ad_slot.dart';
import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/features/companies/data/company_models.dart';
import 'package:careeros/features/jobs/data/job_models.dart';
import 'package:careeros/features/jobs/data/job_repository.dart';
import 'package:careeros/features/jobs/presentation/job_list_tab.dart';
import 'package:careeros/features/jobs/presentation/job_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../test_utils.dart';

class FakeJobRepository extends JobRepository {
  FakeJobRepository({required this.items}) : super(apiClient: ApiClient());

  final List<JobCard> items;

  @override
  Future<({List<JobCard> items, int total})> list({int page = 1, JobFilters filters = const JobFilters()}) async {
    return (items: items, total: items.length);
  }

  @override
  Future<void> save(String jobId) async {}

  @override
  Future<void> unsave(String jobId) async {}
}

JobCard _job(int i) => JobCard(
      id: 'job-$i',
      slug: 'job-$i',
      title: 'Role $i',
      company: const CompanySummary(id: 'c1', name: 'Acme Corp', slug: 'acme-corp'),
      employmentType: 'FULL_TIME',
      workMode: 'REMOTE',
      isFeatured: false,
      isUrgent: false,
      isVerified: false,
      isSaved: false,
    );

const _enabledConfig = MonetizationConfig(
  adsEnabled: true,
  bannerAdsEnabled: true,
  interstitialAdsEnabled: true,
  rewardedAdsEnabled: true,
  appOpenAdsEnabled: false,
  feedAdInterval: 3,
  interstitialMinIntervalSeconds: 480,
  interstitialMaxPerSession: 3,
);

const _freeEntitlement = Entitlement(
  tier: 'FREE',
  isPro: false,
  shouldShowAds: true,
  canUseUnlimitedAts: false,
  canUseUnlimitedAptitude: false,
  canUseAdvancedAnalytics: false,
  atsUsedToday: 0,
  atsDailyLimit: 3,
  atsRemainingToday: 3,
  aptitudeUsedToday: 0,
  aptitudeDailyLimit: 1,
  aptitudeRemainingToday: 1,
);

const _proEntitlement = Entitlement(
  tier: 'PRO',
  isPro: true,
  shouldShowAds: false,
  canUseUnlimitedAts: true,
  canUseUnlimitedAptitude: true,
  canUseAdvancedAnalytics: true,
  atsUsedToday: 0,
  atsDailyLimit: null,
  atsRemainingToday: null,
  aptitudeUsedToday: 0,
  aptitudeDailyLimit: null,
  aptitudeRemainingToday: null,
);

Future<void> _pumpFeed(WidgetTester tester, List<Override> overrides) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: const MaterialApp(home: Scaffold(body: JobListTab())),
    ),
  );
  await tester.pump();
  await tester.pump();
}

void main() {
  testWidgets('A free user sees an ad slot at the configured feed interval', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeJobRepository(items: List.generate(7, _job));

    await _pumpFeed(tester, [
      jobRepositoryProvider.overrideWithValue(repo),
      monetizationConfigProvider.overrideWith((ref) async => _enabledConfig),
      entitlementProvider.overrideWith((ref) async => _freeEntitlement),
    ]);
    await tester.pump(const Duration(milliseconds: 50));

    // interval=3 over 7 items -> ad slots after item 3 and item 6.
    expect(find.byType(BannerAdSlot), findsNWidgets(2));
    // Content remains present and usable alongside the ad slots.
    expect(find.text('Role 1'), findsOneWidget);
  });

  testWidgets('A Pro user never sees an ad slot in the jobs feed', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeJobRepository(items: List.generate(7, _job));

    await _pumpFeed(tester, [
      jobRepositoryProvider.overrideWithValue(repo),
      monetizationConfigProvider.overrideWith((ref) async => _enabledConfig),
      entitlementProvider.overrideWith((ref) async => _proEntitlement),
    ]);
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(BannerAdSlot), findsNothing);
    expect(find.text('Role 1'), findsOneWidget);
  });

  testWidgets('Globally disabled ads show no ad slot even for a free user', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeJobRepository(items: List.generate(7, _job));

    await _pumpFeed(tester, [
      jobRepositoryProvider.overrideWithValue(repo),
      monetizationConfigProvider.overrideWith((ref) async => MonetizationConfig.disabled),
      entitlementProvider.overrideWith((ref) async => _freeEntitlement),
    ]);
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(BannerAdSlot), findsNothing);
  });
}
