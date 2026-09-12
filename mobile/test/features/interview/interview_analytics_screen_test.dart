import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/interview_analytics_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

void main() {
  testWidgets('Shows "not enough activity" instead of inventing a readiness score', (tester) async {
    useLargeTestViewport(tester);
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: FakeInterviewRepository());

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: const MaterialApp(home: InterviewAnalyticsScreen())));
    await tester.pumpAndSettle();

    expect(find.textContaining('Start practicing to build your readiness score'), findsOneWidget);
  });

  testWidgets('Shows a real readiness breakdown and activity stats when data exists', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeInterviewRepository()
      ..readinessOverride = const Readiness(
        overall: 62,
        insufficientData: false,
        components: ReadinessComponents(questionPractice: 80, starCoverage: 40, technicalPrep: 50, recentConsistency: 100),
      )
      ..analyticsOverride = const InterviewAnalytics(
        sessionsCompleted: 3,
        questionsPracticed: 24,
        averageSelfRating: 3.5,
        starStoriesCreated: 2,
        starStoriesReady: 1,
        companyPrepCompleted: 0,
        technicalTopicsCovered: 2,
        byCategory: {'Behavioral': CategoryCompletion(completed: 10, total: 12)},
      );
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: const MaterialApp(home: InterviewAnalyticsScreen())));
    await tester.pumpAndSettle();

    expect(find.text('62%'), findsOneWidget);
    expect(find.text('3'), findsOneWidget); // Sessions Completed
    expect(find.text('24'), findsOneWidget); // Questions Practiced
    expect(find.text('1 / 2'), findsOneWidget); // STAR Stories Ready
    expect(find.text('Behavioral'), findsOneWidget);
    expect(find.text('10/12'), findsOneWidget);
  });
}
