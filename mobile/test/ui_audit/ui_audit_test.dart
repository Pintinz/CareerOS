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
import 'package:careeros/core/widgets/widgets.dart';
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
import 'package:careeros/core/monetization/consent_manager.dart';
import 'package:careeros/features/applications/presentation/create_application_screen.dart';
import 'package:careeros/features/aptitude/presentation/active_test_screen.dart';
import 'package:careeros/features/aptitude/presentation/aptitude_analytics_screen.dart';
import 'package:careeros/features/aptitude/presentation/question_review_screen.dart';
import 'package:careeros/features/aptitude/presentation/test_results_screen.dart';
import 'package:careeros/features/auth/presentation/register_screen.dart';
import 'package:careeros/features/companies/data/company_models.dart';
import 'package:careeros/features/companies/data/company_repository.dart';
import 'package:careeros/features/companies/presentation/company_detail_screen.dart';
import 'package:careeros/features/companies/presentation/company_providers.dart';
import 'package:careeros/features/email_tracking/data/email_tracking_models.dart';
import 'package:careeros/features/email_tracking/presentation/connect_consent_screen.dart';
import 'package:careeros/features/email_tracking/presentation/recruitment_events_screen.dart';
import 'package:careeros/features/email_tracking/presentation/smart_tracking_settings_screen.dart';
import 'package:careeros/features/intelligence/presentation/intelligence_detail_screen.dart';
import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/company_prep_screen.dart';
import 'package:careeros/features/interview/presentation/interview_analytics_screen.dart';
import 'package:careeros/features/interview/presentation/interview_configuration_screen.dart';
import 'package:careeros/features/interview/presentation/interview_results_screen.dart';
import 'package:careeros/features/interview/presentation/interview_session_screen.dart';
import 'package:careeros/features/interview/presentation/star_story_list_screen.dart';
import 'package:careeros/features/profile/presentation/saved_items_screen.dart';
import 'package:careeros/features/scholarships/presentation/scholarship_list_tab.dart';
import 'package:careeros/features/settings/presentation/ads_privacy_screen.dart';
import 'package:careeros/features/settings/presentation/pro_screen.dart';
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
import 'package:careeros/features/jobs/presentation/job_list_tab.dart';
import 'package:careeros/features/onboarding/presentation/onboarding_illustrations.dart';
import 'package:careeros/features/onboarding/presentation/onboarding_screen.dart';
import 'package:careeros/features/onboarding/presentation/welcome_screen.dart';
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

/// Capture height in logical pixels; raise it (e.g. `--dart-define=UI_AUDIT_HEIGHT=1600`) to review
/// whole scrolling pages.
const _captureHeight = int.fromEnvironment('UI_AUDIT_HEIGHT', defaultValue: 780);

/// Restricts the run to screens whose name contains this text (e.g. `UI_AUDIT_ONLY=home`).
const _only = String.fromEnvironment('UI_AUDIT_ONLY');

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

/// A graduate programme whose official listing disappeared: exercises programme facts, provenance
/// and the "Listing unavailable" state (no Apply button).
JobDetail _removedProgrammeDetail() => JobDetail(
      id: 'job-2',
      slug: 'graduate-programme-removed',
      title: 'Graduate Engineer Trainee Programme 2027',
      company: _jobDetail().company,
      location: 'Port Harcourt, Nigeria',
      employmentType: 'UNSPECIFIED',
      workMode: 'UNSPECIFIED',
      description: 'A two-year rotational programme across operations and maintenance.',
      sourceType: 'WORKDAY',
      sourceUrl: 'https://example.com/programme',
      applicationUrl: 'https://example.com/programme/apply',
      publishedAt: _now.subtract(const Duration(days: 20)),
      applicationDeadline: _now.add(const Duration(days: 10)),
      isVerified: true,
      isFeatured: false,
      isDemo: true,
      isSaved: true,
      opportunityType: 'GRADUATE_PROGRAM',
      availability: 'UNAVAILABLE',
      isOfficialSource: true,
      lastVerifiedAt: _now.subtract(const Duration(days: 1)),
      programDuration: '24 months',
      programStartDate: DateTime(2027, 2, 1),
      eligibility: const {
        'eligible_degrees': ['B.Eng', 'B.Sc'],
        'eligible_fields': ['Mechanical Engineering', 'Chemical Engineering'],
        'graduation_year_requirements': ['2024', '2025', '2026'],
      },
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
  Future<JobDetail> getByIdOrSlug(String idOrSlug) async =>
      idOrSlug == 'graduate-programme-removed' ? _removedProgrammeDetail() : _jobDetail();
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
  @override
  Future<({List<ScholarshipCard> items, int total})> listSaved({int page = 1}) async => (items: _scholarships(), total: 1);
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
      // The demo user follows no companies.
      followedOnly ? (items: <IntelligenceCard>[], total: 0) : (items: _posts(), total: 1);
  @override
  Future<IntelligenceDetail> getByIdOrSlug(String idOrSlug) async => IntelligenceDetail(
        id: 'i1',
        slug: 'expansion',
        headline: 'Demo Energy Corp announces a new offshore project and graduate hiring drive',
        category: 'HIRING',
        company: _company,
        summary: 'The project is expected to open technician and engineering roles next year.',
        fullContent: 'Demo Energy Corp said the offshore project will move into construction next year, with '
            'recruitment for process technicians, instrumentation engineers and graduate trainees.',
        whyItMatters: 'Graduate and technician roles usually open months before construction starts.',
        relevantRoles: const ['Process Technician', 'Instrumentation Engineer'],
        relevantSkills: const ['Process safety', 'PLC'],
        sourceUrl: 'https://example.com/news',
        sourceName: 'Demo Energy Corp newsroom',
        publishedAt: _now.subtract(const Duration(hours: 5)),
        isVerified: true,
        isDemo: true,
      );
  @override
  Future<({List<IntelligenceCard> items, int total})> listByCompany(String companyId, {int page = 1}) async =>
      (items: _posts(), total: 1);
}

class _CompanyRepo extends CompanyRepository {
  _CompanyRepo() : super(apiClient: ApiClient());
  @override
  Future<Company> getByIdOrSlug(String idOrSlug) async => _jobDetail().company.copyWithWebsite();
}

extension on Company {
  Company copyWithWebsite() => Company(
        id: id,
        name: name,
        slug: slug,
        industry: industry,
        headquarters: headquarters,
        country: 'Nigeria',
        websiteUrl: 'https://example.com',
        careerUrl: 'https://example.com/careers',
        description: description,
        isVerified: isVerified,
        isActive: isActive,
        isDemo: isDemo,
      );
}

class _Consent implements ConsentManager {
  @override
  Future<void> gatherConsent({bool debugForceEea = false}) async {}
  @override
  Future<bool> canRequestAds() async => false;
  @override
  Future<bool> isPrivacyOptionsRequired() async => true;
  @override
  Future<void> showPrivacyOptionsForm() async {}
}

final _starStory = StarStory(
  id: 'star-1',
  title: 'Stopped a pump failure during night shift',
  category: StarCategory.equipmentFailure,
  situation: 'A feed pump started vibrating during a night shift.',
  task: 'Keep the unit running safely until maintenance arrived.',
  action: 'I isolated the pump, switched to the standby unit and logged readings every 15 minutes.',
  result: 'No downtime and the fault was fixed the next morning.',
  skillsDemonstrated: const ['Process safety', 'Troubleshooting'],
  completeness: const StarCompleteness(sections: {}, gaps: [], isComplete: true),
  createdAt: _now.subtract(const Duration(days: 4)),
  updatedAt: _now.subtract(const Duration(days: 1)),
);

SessionReview _review() => const SessionReview(
      sessionId: 'session-1',
      questions: [
        ReviewQuestion(
          id: 'q1',
          orderIndex: 0,
          questionText: 'What is 15% of 200?',
          questionType: QuestionType.singleChoice,
          difficulty: QuestionDifficulty.easy,
          categoryName: 'Numerical Reasoning',
          topicName: 'Percentages',
          options: [
            TestOption(id: 'opt-correct', optionText: '30', displayOrder: 0, isCorrect: true),
            TestOption(id: 'opt-wrong', optionText: '20', displayOrder: 1, isCorrect: false),
          ],
          selectedOptionIds: ['opt-wrong'],
          isCorrect: false,
          marksAwarded: -0.25,
          explanation: '15% of 200 is 0.15 × 200 = 30.',
          timeSpentSeconds: 42,
        ),
      ],
    );

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
      byCategory: {
        'Numerical Reasoning': CategoryStat(attempted: 34, correct: 26, percentage: 76),
        'Verbal Reasoning': CategoryStat(attempted: 28, correct: 17, percentage: 61),
      },
      byTopic: {},
    )
    ..reviewOverride = _review()
    ..sessionProvider = ((id) => buildSampleSession(id: id, status: id == 'session-done' ? TestStatus.submitted : TestStatus.inProgress))
    ..historyOverride = [
      TestSessionSummary(
        id: 'session-0',
        mode: TestMode.practice,
        status: TestStatus.submitted,
        questionCount: 20,
        percentage: 70,
        createdAt: _now.subtract(const Duration(days: 2)),
      ),
    ];
  final interview = FakeInterviewRepository()
    ..sessionProvider = ((id) => buildSampleInterviewSession(
          id: id,
          status: id == 'interview-done' ? InterviewSessionStatus.completed : InterviewSessionStatus.inProgress,
        ))
    ..starStoriesOverride = [_starStory]
    ..analyticsOverride = const InterviewAnalytics(
      sessionsCompleted: 3,
      questionsPracticed: 21,
      averageSelfRating: 3.7,
      starStoriesCreated: 1,
      starStoriesReady: 1,
      companyPrepCompleted: 0,
      technicalTopicsCovered: 2,
      byCategory: {'Behavioral': CategoryCompletion(completed: 12, total: 15)},
    );
  final email = FakeEmailTrackingRepository()..events = [buildSampleRecruitmentEvent(matchedApplicationId: 'app-1')];
  final base = await aptitudeTestOverrides(
    repository: aptitude,
    applicationRepository: FakeApplicationRepository(items: [_application()]),
    interviewRepository: interview,
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
    companyRepositoryProvider.overrideWithValue(_CompanyRepo()),
    consentManagerProvider.overrideWithValue(_Consent()),
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
  AppTypography.debugFontFamily = 'Roboto';
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
  _Screen('02b_welcome', () => const WelcomeScreen()),
  _Screen(
    '02c_onboarding_art',
    () => Scaffold(
      body: SafeArea(
        child: Column(
          children: [for (final scene in OnboardingScene.values) Expanded(child: OnboardingIllustration(scene: scene))],
        ),
      ),
    ),
  ),
  _Screen('03_login', () => const LoginScreen()),
  _Screen('03b_register', () => const RegisterScreen()),
  _Screen('04_home', () => const HomeShell()),
  _Screen('05_opportunities', () => const Scaffold(body: SafeArea(child: OpportunitiesTab()))),
  _Screen('05b_scholarships_feed', () => const Scaffold(body: SafeArea(child: ScholarshipListTab()))),
  _Screen('06_job_detail', () => const JobDetailScreen(idOrSlug: 'process-technician')),
  _Screen('06b_job_detail_unavailable_programme', () => const JobDetailScreen(idOrSlug: 'graduate-programme-removed')),
  _Screen('06c_graduate_programmes_feed', () => const Scaffold(body: SafeArea(child: JobListTab(feed: JobFeed.graduatePrograms)))),
  _Screen('07_scholarship_detail', () => const ScholarshipDetailScreen(idOrSlug: 'global-masters')),
  _Screen('07b_company_detail', () => const CompanyDetailScreen(idOrSlug: 'demo-energy-corp')),
  _Screen('08_intelligence', () => const Scaffold(body: SafeArea(child: IntelligenceFeedTab()))),
  _Screen('08b_intelligence_detail', () => const IntelligenceDetailScreen(idOrSlug: 'expansion')),
  _Screen('09_applications', () => const ApplicationListScreen()),
  _Screen('09b_create_application', () => const CreateApplicationScreen()),
  _Screen('10_application_detail', () => const ApplicationDetailScreen(applicationId: 'app-1')),
  _Screen('11_prepare', () => const Scaffold(body: SafeArea(child: PreparationHubScreen()))),
  _Screen('12_aptitude_setup', () => const TestConfigurationScreen(args: AptitudeConfigureArgs())),
  _Screen('12b_active_test', () => const ActiveTestScreen(sessionId: 'session-1')),
  _Screen('12c_test_results', () => const TestResultsScreen(sessionId: 'session-done')),
  _Screen('12d_question_review', () => const QuestionReviewScreen(sessionId: 'session-1')),
  _Screen('12e_aptitude_analytics', () => const AptitudeAnalyticsScreen()),
  _Screen('13_interview_home', () => const InterviewHomeScreen()),
  _Screen('13b_interview_setup', () => const InterviewConfigurationScreen(args: InterviewConfigureArgs())),
  _Screen('13c_interview_session', () => const InterviewSessionScreen(sessionId: 'interview-session-1')),
  _Screen('13d_interview_results', () => const InterviewResultsScreen(sessionId: 'interview-done')),
  _Screen('13e_interview_analytics', () => const InterviewAnalyticsScreen()),
  _Screen('13f_star_stories', () => const StarStoryListScreen()),
  _Screen('13g_company_prep', () => const CompanyPrepScreen(applicationId: 'app-1')),
  _Screen('14_star_editor', () => const StarStoryEditorScreen()),
  _Screen('15_cv_tools', () => const AtsAnalyzeScreen()),
  _Screen('16_profile', () => const Scaffold(body: SafeArea(child: ProfileTab()))),
  _Screen('16b_saved', () => const SavedItemsScreen()),
  _Screen('17_settings', () => const SettingsScreen()),
  _Screen('17b_ads_privacy', () => const AdsPrivacyScreen()),
  _Screen('17c_pro', () => const ProScreen()),
  _Screen('17d_smart_tracking', () => const SmartTrackingSettingsScreen()),
  _Screen('17e_recruitment_updates', () => const RecruitmentEventsScreen()),
  _Screen('17f_connect_consent', () => ConnectConsentScreen(provider: EmailProvider.gmail, onContinue: (_) async {})),
  _Screen('18_email_update', () => const RecruitmentEventDetailScreen(eventId: 'event-1')),
  _Screen(
    '19_states',
    () => Scaffold(
      body: SafeArea(
        child: ListView(
          children: [
            EmptyState(
              icon: Icons.bookmark_border_rounded,
              title: 'No saved opportunities yet',
              message: 'Save jobs, scholarships and programmes you want to revisit later.',
              actionLabel: 'Explore Opportunities',
              onAction: () {},
            ),
            ErrorState(message: 'Please check your connection and try again.', onRetry: () {}),
          ],
        ),
      ),
    ),
  ),
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

  for (final screen in _screens.where((s) => s.name.contains(_only))) {
    for (final mode in [ThemeMode.light, ThemeMode.dark]) {
      testWidgets('${screen.name} renders without overflow — ${mode.name}, 360dp', (tester) async {
        final key = GlobalKey();
        final size = Size(360, _captureHeight.toDouble());
        // Tests paint shadows as solid offset shapes by default; captures should show real soft shadows.
        if (_capture) debugDisableShadows = false;
        try {
          await _pumpScreen(tester, screen: screen, mode: mode, size: size, textScale: 1.0, boundaryKey: key);
          _expectNoException(tester);
          if (_capture) await _captureTo(tester, key, '${screen.name}_${mode.name}');
        } finally {
          debugDisableShadows = true;
        }
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
