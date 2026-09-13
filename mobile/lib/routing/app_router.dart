import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../core/app_providers.dart";
import "../features/applications/presentation/application_detail_screen.dart";
import "../features/applications/presentation/application_list_screen.dart";
import "../features/applications/presentation/create_application_screen.dart";
import "../features/aptitude/presentation/active_test_screen.dart";
import "../features/aptitude/presentation/aptitude_analytics_screen.dart";
import "../features/aptitude/presentation/question_review_screen.dart";
import "../features/aptitude/presentation/test_configuration_screen.dart";
import "../features/aptitude/presentation/test_results_screen.dart";
import "../features/ats/presentation/ats_analyze_screen.dart";
import "../features/auth/presentation/login_screen.dart";
import "../features/companies/presentation/company_detail_screen.dart";
import "../features/auth/presentation/register_screen.dart";
import "../features/email_tracking/presentation/recruitment_event_detail_screen.dart";
import "../features/email_tracking/presentation/recruitment_events_screen.dart";
import "../features/email_tracking/presentation/smart_tracking_settings_screen.dart";
import "../features/home/presentation/home_shell.dart";
import "../features/intelligence/presentation/intelligence_detail_screen.dart";
import "../features/interview/presentation/company_prep_screen.dart";
import "../features/interview/presentation/interview_analytics_screen.dart";
import "../features/interview/presentation/interview_configuration_screen.dart";
import "../features/interview/presentation/interview_home_screen.dart";
import "../features/interview/presentation/interview_results_screen.dart";
import "../features/interview/presentation/interview_session_screen.dart";
import "../features/interview/presentation/star_story_editor_screen.dart";
import "../features/interview/presentation/star_story_list_screen.dart";
import "../features/jobs/presentation/job_detail_screen.dart";
import "../features/onboarding/presentation/onboarding_screen.dart";
import "../features/profile/presentation/saved_items_screen.dart";
import "../features/scholarships/presentation/scholarship_detail_screen.dart";
import "../features/settings/presentation/ads_privacy_screen.dart";
import "../features/settings/presentation/pro_screen.dart";
import "../features/settings/presentation/settings_screen.dart";
import "../features/splash/presentation/splash_screen.dart";

class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authStateProvider, (_, __) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _RouterRefreshNotifier(ref);

  return GoRouter(
    initialLocation: "/splash",
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final authState = ref.read(authStateProvider);

      // Auth state hasn't resolved yet (first launch) — stay on splash until it does.
      if (!authState.hasValue) {
        return location == "/splash" ? null : "/splash";
      }

      final isAuthenticated = authState.value == AuthState.authenticated;
      final hasOnboarded = ref.read(appPreferencesProvider).hasCompletedOnboarding;
      final isAuthRoute = location == "/login" || location == "/register";

      if (!hasOnboarded) {
        return location == "/onboarding" ? null : "/onboarding";
      }
      if (location == "/onboarding") {
        return isAuthenticated ? "/home" : "/login";
      }
      if (!isAuthenticated) {
        return isAuthRoute ? null : "/login";
      }
      // Authenticated + onboarded: keep out of splash/auth/onboarding routes.
      if (location == "/splash" || isAuthRoute) {
        return "/home";
      }
      return null;
    },
    // A bad/stale deep link or an unmatched route otherwise fell through to go_router's default
    // unbranded "page not found" screen with no way back into the app (Phase 9.5 audit finding).
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text("Page not found")),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("That link doesn't lead anywhere in CareerOS.", textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(onPressed: () => context.go("/home"), child: const Text("Go to Home")),
            ],
          ),
        ),
      ),
    ),
    routes: [
      GoRoute(path: "/splash", builder: (context, state) => const SplashScreen()),
      GoRoute(path: "/onboarding", builder: (context, state) => const OnboardingScreen()),
      GoRoute(path: "/login", builder: (context, state) => const LoginScreen()),
      GoRoute(path: "/register", builder: (context, state) => const RegisterScreen()),
      // `/home?tab=opportunities` opens a specific hub — lets pushed screens (e.g. an empty tracker)
      // send the user into the right hub rather than a dead end.
      GoRoute(
        path: "/home",
        builder: (context, state) => HomeShell(key: ValueKey(state.uri.queryParameters["tab"]), initialTab: state.uri.queryParameters["tab"]),
      ),
      GoRoute(
        path: "/jobs/:idOrSlug",
        builder: (context, state) => JobDetailScreen(idOrSlug: state.pathParameters["idOrSlug"]!),
      ),
      GoRoute(
        path: "/scholarships/:idOrSlug",
        builder: (context, state) => ScholarshipDetailScreen(idOrSlug: state.pathParameters["idOrSlug"]!),
      ),
      GoRoute(
        path: "/companies/:idOrSlug",
        builder: (context, state) => CompanyDetailScreen(idOrSlug: state.pathParameters["idOrSlug"]!),
      ),
      GoRoute(
        path: "/intelligence/:idOrSlug",
        builder: (context, state) => IntelligenceDetailScreen(idOrSlug: state.pathParameters["idOrSlug"]!),
      ),
      GoRoute(
        path: "/ats/analyze",
        builder: (context, state) => AtsAnalyzeScreen(args: state.extra as AtsAnalyzeArgs?),
      ),
      GoRoute(path: "/saved", builder: (context, state) => const SavedItemsScreen()),
      GoRoute(path: "/settings", builder: (context, state) => const SettingsScreen()),
      GoRoute(path: "/settings/pro", builder: (context, state) => const ProScreen()),
      GoRoute(path: "/settings/ads-privacy", builder: (context, state) => const AdsPrivacyScreen()),
      GoRoute(path: "/settings/tracking", builder: (context, state) => const SmartTrackingSettingsScreen()),
      GoRoute(path: "/settings/tracking/events", builder: (context, state) => const RecruitmentEventsScreen()),
      GoRoute(
        path: "/settings/tracking/events/:id",
        builder: (context, state) => RecruitmentEventDetailScreen(eventId: state.pathParameters["id"]!),
      ),
      GoRoute(path: "/applications", builder: (context, state) => const ApplicationListScreen()),
      GoRoute(path: "/applications/new", builder: (context, state) => const CreateApplicationScreen()),
      GoRoute(
        path: "/applications/:id",
        builder: (context, state) => ApplicationDetailScreen(applicationId: state.pathParameters["id"]!),
      ),
      GoRoute(
        path: "/prepare/aptitude/configure",
        builder: (context, state) =>
            TestConfigurationScreen(args: state.extra as AptitudeConfigureArgs? ?? const AptitudeConfigureArgs()),
      ),
      GoRoute(
        path: "/prepare/aptitude/analytics",
        builder: (context, state) => const AptitudeAnalyticsScreen(),
      ),
      GoRoute(
        path: "/prepare/aptitude/sessions/:id",
        builder: (context, state) => ActiveTestScreen(sessionId: state.pathParameters["id"]!),
      ),
      GoRoute(
        path: "/prepare/aptitude/sessions/:id/results",
        builder: (context, state) => TestResultsScreen(sessionId: state.pathParameters["id"]!),
      ),
      GoRoute(
        path: "/prepare/aptitude/sessions/:id/review",
        builder: (context, state) => QuestionReviewScreen(sessionId: state.pathParameters["id"]!),
      ),
      GoRoute(path: "/prepare/interview", builder: (context, state) => const InterviewHomeScreen()),
      GoRoute(
        path: "/prepare/interview/configure",
        builder: (context, state) =>
            InterviewConfigurationScreen(args: state.extra as InterviewConfigureArgs? ?? const InterviewConfigureArgs()),
      ),
      GoRoute(path: "/prepare/interview/analytics", builder: (context, state) => const InterviewAnalyticsScreen()),
      GoRoute(
        path: "/prepare/interview/sessions/:id",
        builder: (context, state) => InterviewSessionScreen(sessionId: state.pathParameters["id"]!),
      ),
      GoRoute(
        path: "/prepare/interview/sessions/:id/results",
        builder: (context, state) => InterviewResultsScreen(sessionId: state.pathParameters["id"]!),
      ),
      GoRoute(path: "/prepare/interview/star-stories", builder: (context, state) => const StarStoryListScreen()),
      GoRoute(path: "/prepare/interview/star-stories/new", builder: (context, state) => const StarStoryEditorScreen()),
      GoRoute(
        path: "/prepare/interview/star-stories/:id",
        builder: (context, state) => StarStoryEditorScreen(storyId: state.pathParameters["id"]!),
      ),
      GoRoute(
        path: "/prepare/interview/company-prep/:applicationId",
        builder: (context, state) => CompanyPrepScreen(applicationId: state.pathParameters["applicationId"]!),
      ),
    ],
  );
});
