// UI audit: renders the main CareerOS screens in light and dark themes, at a common phone width and
// at a narrow 320dp width with 1.3x text, failing on any layout overflow or build exception.
//
// Screenshot capture for visual QA (no backend or login needed):
//   flutter test test/ui_audit --dart-define=UI_AUDIT_CAPTURE=true
// writes PNGs to build/ui_audit/.

import 'dart:io';
import 'dart:ui' as ui;

import 'package:careeros/core/app_providers.dart';
import 'package:careeros/core/design/design.dart';
import 'package:careeros/core/monetization/monetization_models.dart';
import 'package:careeros/core/monetization/monetization_providers.dart';
import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/core/storage/app_preferences.dart';
import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/applications/presentation/application_detail_screen.dart';
import 'package:careeros/features/applications/presentation/application_list_screen.dart';
import 'package:careeros/features/aptitude/data/aptitude_models.dart';
import 'package:careeros/features/aptitude/presentation/preparation_hub_screen.dart';
import 'package:careeros/features/aptitude/presentation/test_configuration_screen.dart';
import 'package:careeros/features/ats/data/ats_models.dart';
import 'package:careeros/features/ats/data/ats_repository.dart';
import 'package:careeros/features/ats/presentation/ats_analyze_screen.dart';
import 'package:careeros/features/ats/presentation/ats_providers.dart';
import 'package:careeros/features/auth/presentation/login_screen.dart';
import 'package:careeros/features/companies/data/company_models.dart';
import 'package:careeros/features/email_tracking/presentation/email_tracking_providers.dart';
import 'package:careeros/features/email_tracking/presentation/recruitment_event_detail_screen.dart';
import 'package:careeros/features/home/presentation/home_shell.dart';
import 'package:careeros/features/intelligence/data/intelligence_models.dart';
import 'package:careeros/features/intelligence/data/intelligence_repository.dart';
import 'package:careeros/features/intelligence/presentation/intelligence_feed_tab.dart';
import 'package:careeros/features/intelligence/presentation/intelligence_providers.dart';
import 'package:careeros/features/interview/presentation/interview_home_screen.dart';
import 'package:careeros/features/interview/presentation/star_story_editor_screen.dart';
import 'package:careeros/features/jobs/data/job_models.dart';
import 'package:careeros/features/jobs/data/job_repository.dart';
import 'package:careeros/features/jobs/presentation/job_detail_screen.dart';
import 'package:careeros/features/jobs/presentation/job_providers.dart';
import 'package:careeros/features/onboarding/presentation/onboarding_screen.dart';
import 'package:careeros/features/opportunities/presentation/opportunities_tab.dart';
import 'package:careeros/features/profile/data/profile_repository.dart';
import 'package:careeros/features/profile/presentation/profile_providers.dart';
import 'package:careeros/features/profile/presentation/profile_tab.dart';
import 'package:careeros/features/scholarships/data/scholarship_models.dart';
import 'package:careeros/features/scholarships/data/scholarship_repository.dart';
import 'package:careeros/features/scholarships/presentation/scholarship_detail_screen.dart';
import 'package:careeros/features/scholarships/presentation/scholarship_providers.dart';
import 'package:careeros/features/settings/presentation/settings_screen.dart';
import 'package:careeros/features/splash/presentation/splash_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../features/aptitude/aptitude_test_support.dart';
import '../features/email_tracking/email_tracking_test_support.dart';
import '../features/interview/interview_test_support.dart';

const _capture = bool.fromEnvironment('UI_AUDIT_CAPTURE');

// ---------------------------------------------------------------------------------------------
// Sample data (clearly fictional, mirrors the backend demo seed)
// ---------------------------------------------------------------------------------------------

final _now = DateTime.now();

const _company = CompanySummary(id: 'c1', name: 'Demo Energy Corp', slug: 'demo-energy-corp');

List<JobCard> _jobs() => [
      JobCard(
        id: 'job-1',
        slug: 'process-technician',
        title: 'Process Technician',
        company: _company,
        location: 'Lagos, Nigeria',
        employmentType: 'FULL_TIME',
        workMode: 'ON_SITE',
        experienceLevel: 'ENTRY',
        isFeatured: true,
        isUrgent: false,
        isVerified: true,
        isSaved: false,
        isDemo: true,
        publishedAt: _now.subtract(const Duration(days: 2)),
        applicationDeadline: _now.add(const Duration(days: 6)),
      ),
      JobCard(
        id: 'job-2',
        slug: 'backend-engineer',
        title: 'Senior Backend Engineer, Payments Infrastructure Platform',
        company: const CompanySummary(id: 'c2', name: 'Demo FinTech Labs International', slug: 'demo-fintech'),
        location: 'Remote',
        employmentType: 'CONTRACT',
        workMode: 'REMOTE',
        isFeatured: false,
        isUrgent: true,
        isVerified: false,
        isSaved: true,
        isDemo: true,
        publishedAt: _now.subtract(const Duration(days: 12)),
      ),
    ];

JobDetail _jobDetail() => JobDetail(
      id: 'job-1',
      slug: 'process-technician',
      title: 'Process Technician',
      company: const Company(
        id: 'c1',
        name: 'Demo Energy Corp',
        slug: 'demo-energy-corp',
        industry: 'Energy',
        headquarters: 'Lagos',
        description: 'A fictional energy company used for CareerOS demo content.',
        isVerified: true,
        isActive: true,
        isDemo: true,
      ),
      location: 'Lagos, Nigeria',
      employmentType: 'FULL_TIME',
      workMode: 'ON_SITE',
      experienceLevel: 'ENTRY',
      industry: 'Energy',
      salaryMin: 400000,
      salaryMax: 650000,
      salaryCurrency: 'NGN',
      salaryPeriod: 'MONTHLY',
      shortSummary: 'Operate and monitor process units safely.',
      description: 'Monitor plant equipment, record readings, and support maintenance teams across shifts.',
      responsibilities: const ['Monitor process parameters', 'Perform routine inspections'],
      requirements: const ['OND/HND in a technical field', 'Basic knowledge of pumps and valves'],
      preferredSkills: const ['PLC', 'SCADA'],
      benefits: const ['Health insurance', 'Training allowance'],
      applicationUrl: 'https://example.com/apply',
      sourceType: 'OFFICIAL_CAREER_PAGE',
      publishedAt: _now.subtract(const Duration(days: 2)),
      applicationDeadline: _now.add(const Duration(days: 6)),
      isVerified: true,
      isFeatured: true,
      isDemo: true,
      isSaved: false,
    );

List<ScholarshipCard> _scholarships() => [
      ScholarshipCard(
        id: 's1',
        slug: 'global-masters',
        name: 'Demo Global Masters Award',
        organization: 'Demo Foundation',
        country: 'United Kingdom',
        degreeLevels: const ['MASTERS', 'PHD'],
        fundingType: 'FULLY_FUNDED',
        applicationDeadline: _now.add(const Duration(days: 45)),
        isVerified: true,
        isFeatured: false,
        isSaved: false,
        isDemo: true,
      ),
    ];

ScholarshipDetail _scholarshipDetail() => ScholarshipDetail(
      id: 's1',
      slug: 'global-masters',
      name: 'Demo Global Masters Award',
      organization: 'Demo Foundation',
      country: 'United Kingdom',
      degreeLevels: const ['MASTERS'],
      fieldsOfStudy: const ['Engineering', 'Data Science'],
      fundingType: 'FULLY_FUNDED',
      tuitionCoverage: 'Full tuition',
      monthlyStipend: '£1,400',
      summary: 'A fictional scholarship for demo purposes.',
      eligibleNationalities: const ['All countries'],
      requiredDocuments: const ['CV', 'Two references'],
      applicationDeadline: _now.add(const Duration(days: 45)),
      isVerified: true,
      isFeatured: false,
      isSaved: false,
      isDemo: true,
    );

List<IntelligenceCard> _posts() => [
      IntelligenceCard(
        id: 'i1',
        slug: 'expansion',
        headline: 'Demo Energy Corp announces a new offshore project and graduate hiring drive',
        category: 'HIRING',
        company: _company,
        summary: 'The project is expected to open technician and engineering roles next year.',
        publishedAt: _now.subtract(const Duration(hours: 5)),
        isFeatured: true,
      ),
    ];

Application _application() => Application(
      id: 'app-1',
      jobId: 'job-1',
      companyName: 'Demo Energy Corp',
      roleTitle: 'Process Technician',
      location: 'Lagos',
      currentStage: ApplicationStage.interview,
      appliedDate: _now.subtract(const Duration(days: 20)),
      interviewDate: _now.add(const Duration(days: 3)),
      updatedAt: _now.subtract(const Duration(days: 1)),
      timeline: [
        ApplicationStageEvent(id: 'e1', stage: ApplicationStage.applied, occurredAt: _now.subtract(const Duration(days: 20))),
        ApplicationStageEvent(id: 'e2', stage: ApplicationStage.shortlisted, occurredAt: _now.subtract(const Duration(days: 9))),
        ApplicationStageEvent(
          id: 'e3',
          stage: ApplicationStage.interview,
          occurredAt: _now.subtract(const Duration(days: 1)),
          note: 'Panel interview invitation received.',
        ),
      ],
      notes: [ApplicationNote(id: 'n1', text: 'Prepare a safety incident story.', createdAt: _now)],
    );

// ---------------------------------------------------------------------------------------------
// Fakes
// ---------------------------------------------------------------------------------------------

class _Prefs implements AppPreferences {
  @override
  bool get hasCompletedOnboarding => true;
  @override
  Future<void> setOnboardingComplete() async {}
  @override
  ThemeMode get themeMode => ThemeMode.system;
  @override
  Future<void> setThemeMode(ThemeMode mode) async {}
}

class _JobRepo extends JobRepository {
  _JobRepo() : super(apiClient: ApiClient());
  @override
  Future<({List<JobCard> items, int total})> list({int page = 1, JobFilters filters = const JobFilters()}) async =>
      (items: _jobs(), total: 2);
  @override
  Future<JobDetail> getByIdOrSlug(String idOrSlug) async => _jobDetail();
  @override
  Future<({List<JobCard> items, int total})> listByCompany(String companyId, {int page = 1}) async => (items: _jobs(), total: 2);
  @override
  Future<({List<JobCard> items, int total})> listSaved({int page = 1}) async => (items: _jobs().sublist(1), total: 1);
}

class _ScholarshipRepo extends ScholarshipRepository {
  _ScholarshipRepo() : super(apiClient: ApiClient());
  @override
  Future<({List<ScholarshipCard> items, int total})> list({int page = 1, ScholarshipFilters filters = const ScholarshipFilters()}) async =>
      (items: _scholarships(), total: 1);
  @override
  Future<ScholarshipDetail> getByIdOrSlug(String idOrSlug) async => _scholarshipDetail();
}

class _IntelligenceRepo extends IntelligenceRepository {
  _IntelligenceRepo() : super(apiClient: ApiClient());
  @override
  Future<({List<IntelligenceCard> items, int total})> list({
    int page = 1,
    String? search,
    String? category,
    bool followedOnly = false,
  }) async =>
      (items: _posts(), total: 1);
}

class _ProfileRepo extends ProfileRepository {
  _ProfileRepo() : super(apiClient: ApiClient());
  @override
  Future<CurrentUser> getCurrentUser() async => const CurrentUser(id: 'u1', email: 'ada@example.com', isVerified: true);
  @override
  Future<UserProfile> getProfile() async => const UserProfile(
        fullName: 'Ada Obi',
        professionalTitle: 'Process Technician',
        location: 'Lagos, Nigeria',
        yearsOfExperience: 3,
        highestEducation: 'HND',
      );
}

class _AtsRepo extends AtsRepository {
  _AtsRepo() : super(apiClient: ApiClient());
  @override
  Future<List<CvDocument>> listCvs() async => const [CvDocument(id: 'cv1', name: 'Ada Obi — CV 2026', isPrimary: true)];
}

const _disabledAds = MonetizationConfig.disabled;

const _freeEntitlement = Entitlement(
  tier: 'FREE',
  isPro: false,
  shouldShowAds: false,
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

Future<List<Override>> _overrides() async {
  final aptitude = FakeAptitudeRepository()
    ..analyticsOverride = const AptitudeAnalytics(
      testsCompleted: 4,
      questionsAnswered: 62,
      averageScore: 71,
      bestScore: 90,
      byCategory: {},
      byTopic: {},
    );
  final email = FakeEmailTrackingRepository()..events = [buildSampleRecruitmentEvent(matchedApplicationId: 'app-1')];
  final base = await aptitudeTestOverrides(
    repository: aptitude,
    applicationRepository: FakeApplicationRepository(items: [_application()]),
    interviewRepository: FakeInterviewRepository(),
  );
  return [
    ...base,
    appPreferencesProvider.overrideWithValue(_Prefs()),
    authStateProvider.overrideWith((ref) async => AuthState.authenticated),
    jobRepositoryProvider.overrideWithValue(_JobRepo()),
    scholarshipRepositoryProvider.overrideWithValue(_ScholarshipRepo()),
    intelligenceRepositoryProvider.overrideWithValue(_IntelligenceRepo()),
    profileRepositoryProvider.overrideWithValue(_ProfileRepo()),
    atsRepositoryProvider.overrideWithValue(_AtsRepo()),
    emailTrackingRepositoryProvider.overrideWithValue(email),
    monetizationConfigProvider.overrideWith((ref) async => _disabledAds),
    entitlementProvider.overrideWith((ref) async => _freeEntitlement),
  ];
}

// ---------------------------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------------------------

Future<void> _loadFonts() async {
  final root = Platform.environment['FLUTTER_ROOT'];
  if (root == null) return;
  final dir = '$root/bin/cache/artifacts/material_fonts';
  Future<ByteData> read(String name) async => ByteData.sublistView(await File('$dir/$name').readAsBytes());
  if (!File('$dir/roboto-regular.ttf').existsSync()) return;
  final roboto = FontLoader('Roboto')
    ..addFont(read('roboto-regular.ttf'))
    ..addFont(read('roboto-medium.ttf'))
    ..addFont(read('roboto-bold.ttf'))
    ..addFont(read('roboto-black.ttf'));
  await roboto.load();
  final icons = FontLoader('MaterialIcons')..addFont(read('materialicons-regular.otf'));
  await icons.load();
}

class _Screen {
  const _Screen(this.name, this.builder);
  final String name;
  final Widget Function() builder;
}

final _screens = <_Screen>[
  _Screen('01_splash', () => const SplashScreen()),
  _Screen('02_onboarding', () => const OnboardingScreen()),
  _Screen('03_login', () => const LoginScreen()),
  _Screen('04_home', () => const HomeShell()),
  _Screen('05_opportunities', () => const Scaffold(body: SafeArea(child: OpportunitiesTab()))),
  _Screen('06_job_detail', () => const JobDetailScreen(idOrSlug: 'process-technician')),
  _Screen('07_scholarship_detail', () => const ScholarshipDetailScreen(idOrSlug: 'global-masters')),
  _Screen('08_intelligence', () => const Scaffold(body: SafeArea(child: IntelligenceFeedTab()))),
  _Screen('09_applications', () => const ApplicationListScreen()),
  _Screen('10_application_detail', () => const ApplicationDetailScreen(applicationId: 'app-1')),
  _Screen('11_prepare', () => const Scaffold(body: SafeArea(child: PreparationHubScreen()))),
  _Screen('12_aptitude_setup', () => const TestConfigurationScreen(args: AptitudeConfigureArgs())),
  _Screen('13_interview_home', () => const InterviewHomeScreen()),
  _Screen('14_star_editor', () => const StarStoryEditorScreen()),
  _Screen('15_cv_tools', () => const AtsAnalyzeScreen()),
  _Screen('16_profile', () => const Scaffold(body: SafeArea(child: ProfileTab()))),
  _Screen('17_settings', () => const SettingsScreen()),
  _Screen('18_email_update', () => const RecruitmentEventDetailScreen(eventId: 'event-1')),
];

Future<void> _pumpScreen(
  WidgetTester tester, {
  required _Screen screen,
  required ThemeMode mode,
  required Size size,
  required double textScale,
  required GlobalKey boundaryKey,
}) async {
  tester.view.physicalSize = size * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(routes: [GoRoute(path: '/', builder: (context, state) => screen.builder())]);
  await tester.pumpWidget(
    ProviderScope(
      overrides: await _overrides(),
      child: RepaintBoundary(
        key: boundaryKey,
        child: MaterialApp.router(
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          themeMode: mode,
          routerConfig: router,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)),
            child: child!,
          ),
        ),
      ),
    ),
  );
  // Let fake futures resolve and entrance tweens finish without waiting on looping skeletons.
  for (var i = 0; i < 6; i++) {
    await tester.pump(const Duration(milliseconds: 250));
  }
}

Future<void> _captureTo(WidgetTester tester, GlobalKey key, String fileName) async {
  await tester.runAsync(() async {
    final boundary = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 2);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    final file = File('build/ui_audit/$fileName.png');
    await file.parent.create(recursive: true);
    await file.writeAsBytes(bytes!.buffer.asUint8List());
  });
}

void main() {
  setUpAll(_loadFonts);

  for (final screen in _screens) {
    for (final mode in [ThemeMode.light, ThemeMode.dark]) {
      testWidgets('${screen.name} renders without overflow — ${mode.name}, 360dp', (tester) async {
        final key = GlobalKey();
        await _pumpScreen(tester, screen: screen, mode: mode, size: const Size(360, 780), textScale: 1.0, boundaryKey: key);
        _expectNoException(tester);
        if (_capture) await _captureTo(tester, key, '${screen.name}_${mode.name}');
      });
    }

    testWidgets('${screen.name} renders without overflow — 320dp at 1.3x text', (tester) async {
      final key = GlobalKey();
      await _pumpScreen(tester, screen: screen, mode: ThemeMode.light, size: const Size(320, 1400), textScale: 1.3, boundaryKey: key);
      _expectNoException(tester);
    });
  }
}

/// Fails with the full diagnostic (including the offending widget's source location) rather than
/// just the one-line summary.
void _expectNoException(WidgetTester tester) {
  // With --dart-define=UI_AUDIT_VERBOSE=true the framework reports the error itself, including
  // "The relevant error-causing widget was: <file>:<line>".
  if (const bool.fromEnvironment('UI_AUDIT_VERBOSE')) return;
  expect(tester.takeException(), isNull);
}
