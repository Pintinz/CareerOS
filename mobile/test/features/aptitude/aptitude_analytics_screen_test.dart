import 'package:careeros/features/aptitude/data/aptitude_models.dart';
import 'package:careeros/features/aptitude/presentation/aptitude_analytics_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import 'aptitude_test_support.dart';

void main() {
  testWidgets('Shows an honest empty state when no tests have been completed', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(
      ProviderScope(overrides: overrides, child: const MaterialApp(home: AptitudeAnalyticsScreen())),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('No tests completed yet'), findsOneWidget);
  });

  testWidgets('Shows real stats and weak-topic recommendations with a Practice Weak Areas button', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository()
      ..analyticsOverride = const AptitudeAnalytics(
        testsCompleted: 5,
        questionsAnswered: 80,
        averageScore: 64,
        bestScore: 88,
        byCategory: {
          'Numerical Reasoning': CategoryStat(attempted: 40, correct: 30, percentage: 75),
        },
        byTopic: {},
      )
      ..recommendationsOverride = const Recommendations(
        weakTopics: [
          WeakTopic(topicName: 'Pumps', topicSlug: 'pumps', categoryName: 'Technical / Skill', accuracy: 40, attempted: 5),
        ],
        minAttemptsRequired: 3,
      );
    final overrides = await aptitudeTestOverrides(repository: repo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const AptitudeAnalyticsScreen()),
      GoRoute(path: '/prepare/aptitude/configure', builder: (context, state) => const Scaffold(body: Text('Configure Screen'))),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.text('5'), findsOneWidget); // Tests Completed
    expect(find.text('64%'), findsOneWidget); // Average Score
    expect(find.text('Pumps'), findsOneWidget);
    expect(find.text('Practice Weak Areas'), findsOneWidget);

    await tester.tap(find.text('Practice Weak Areas'));
    await tester.pumpAndSettle();
    expect(find.text('Configure Screen'), findsOneWidget);
  });
}
