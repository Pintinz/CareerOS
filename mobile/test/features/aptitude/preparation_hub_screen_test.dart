import 'package:careeros/features/aptitude/data/aptitude_models.dart';
import 'package:careeros/features/aptitude/presentation/preparation_hub_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'aptitude_test_support.dart';

Widget _wrap(Widget child, List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => child),
    GoRoute(path: '/prepare/aptitude/configure', builder: (context, state) => const Scaffold(body: Text('Configure Screen'))),
    GoRoute(path: '/prepare/aptitude/analytics', builder: (context, state) => const Scaffold(body: Text('Analytics Screen'))),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

void main() {
  testWidgets('Prep Hub shows the "what are you preparing for" header and both cards', (tester) async {
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const PreparationHubScreen(), overrides));
    await tester.pumpAndSettle();

    expect(find.text('What are you preparing for?'), findsOneWidget);
    expect(find.text('Aptitude Test'), findsOneWidget);
    expect(find.text('Start Preparing'), findsOneWidget);
    expect(find.text('Interview Preparation'), findsOneWidget);
    expect(find.text('Coming in Phase 7'), findsOneWidget);

    // The disabled Interview button must never navigate anywhere — no dead button that does
    // something unexpected either.
    final interviewButton = tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Coming in Phase 7'));
    expect(interviewButton.onPressed, isNull);
  });

  testWidgets('Prep Hub shows real stats from analytics, not placeholders', (tester) async {
    final repo = FakeAptitudeRepository()
      ..analyticsOverride = const AptitudeAnalytics(
        testsCompleted: 4,
        questionsAnswered: 62,
        averageScore: 71,
        bestScore: 90,
        byCategory: {},
        byTopic: {},
      );
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const PreparationHubScreen(), overrides));
    await tester.pumpAndSettle();

    expect(find.text('4'), findsOneWidget); // Tests Completed
    expect(find.text('71%'), findsOneWidget); // Average Score
    expect(find.text('62'), findsOneWidget); // Questions Practiced
    expect(find.text('90%'), findsOneWidget); // Best Score
  });

  testWidgets('Tapping Start Preparing navigates to the configuration screen', (tester) async {
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const PreparationHubScreen(), overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Start Preparing'));
    await tester.pumpAndSettle();

    expect(find.text('Configure Screen'), findsOneWidget);
  });
}
