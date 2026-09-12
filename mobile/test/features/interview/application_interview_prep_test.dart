import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/applications/presentation/application_detail_screen.dart';
import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

Application _applicationAtStage(ApplicationStage stage) => Application(
      id: 'app-1',
      jobId: 'job-1',
      companyName: 'Acme Corp',
      roleTitle: 'Process Technician',
      currentStage: stage,
      updatedAt: DateTime.now(),
    );

void main() {
  testWidgets('Shows a real Interview Preparation card with readiness for an interview-stage application', (tester) async {
    final applicationRepo = FakeApplicationRepository(items: [_applicationAtStage(ApplicationStage.interview)]);
    final interviewRepo = FakeInterviewRepository()
      ..readinessOverride = const Readiness(
        overall: 55,
        insufficientData: false,
        components: ReadinessComponents(questionPractice: 60),
      );
    final overrides = await aptitudeTestOverrides(
      repository: FakeAptitudeRepository(), applicationRepository: applicationRepo, interviewRepository: interviewRepo,
    );

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const ApplicationDetailScreen(applicationId: 'app-1')),
      GoRoute(path: '/prepare/interview/configure', builder: (context, state) => const Scaffold(body: Text('Interview Configure Screen'))),
      GoRoute(path: '/prepare/interview/company-prep/:id', builder: (context, state) => const Scaffold(body: Text('Company Prep Screen'))),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.text('Interview Preparation'), findsOneWidget);
    expect(find.text('Readiness: 55%'), findsNothing); // that copy lives on Home, not here
    expect(find.text('55%'), findsOneWidget);
    expect(find.text('Continue Preparation'), findsOneWidget);
    expect(find.textContaining('never changes this application'), findsOneWidget);

    await tester.tap(find.text('Continue Preparation'));
    await tester.pumpAndSettle();
    expect(find.text('Interview Configure Screen'), findsOneWidget);
  });

  testWidgets('Shows the card for recruiter screen and assessment centre stages too', (tester) async {
    for (final stage in [ApplicationStage.recruiterScreen, ApplicationStage.assessmentCentre, ApplicationStage.finalInterview]) {
      final applicationRepo = FakeApplicationRepository(items: [_applicationAtStage(stage)]);
      final overrides = await aptitudeTestOverrides(
        repository: FakeAptitudeRepository(), applicationRepository: applicationRepo, interviewRepository: FakeInterviewRepository(),
      );

      await tester.pumpWidget(
        ProviderScope(overrides: overrides, child: const MaterialApp(home: ApplicationDetailScreen(applicationId: 'app-1'))),
      );
      await tester.pumpAndSettle();

      expect(find.text('Interview Preparation'), findsOneWidget, reason: 'stage=$stage');
    }
  });
}
