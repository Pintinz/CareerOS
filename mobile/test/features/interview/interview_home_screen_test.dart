import 'package:careeros/features/interview/presentation/interview_configuration_screen.dart';
import 'package:careeros/features/interview/presentation/interview_home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

void main() {
  testWidgets('Shows quick actions and category tiles', (tester) async {
    useLargeTestViewport(tester);
    final interviewRepo = FakeInterviewRepository();
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: interviewRepo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const InterviewHomeScreen()),
      GoRoute(
        path: '/prepare/interview/configure',
        builder: (context, state) => Scaffold(body: Text('Configure: ${(state.extra as InterviewConfigureArgs?)?.initialCategorySlug ?? (state.extra as InterviewConfigureArgs?)?.initialMode}')),
      ),
      GoRoute(path: '/prepare/interview/star-stories', builder: (context, state) => const Scaffold(body: Text('STAR Stories Screen'))),
      GoRoute(path: '/prepare/interview/analytics', builder: (context, state) => const Scaffold(body: Text('Analytics Screen'))),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.text('Mock Interview'), findsOneWidget);
    expect(find.text('Question Practice'), findsOneWidget);
    expect(find.text('STAR Story Builder'), findsOneWidget);
    expect(find.text('Behavioral'), findsOneWidget);
    expect(find.text('Technical'), findsOneWidget);
  });

  testWidgets('Tapping a category tile launches configuration preselected with that category', (tester) async {
    useLargeTestViewport(tester);
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: FakeInterviewRepository());

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const InterviewHomeScreen()),
      GoRoute(
        path: '/prepare/interview/configure',
        builder: (context, state) {
          final args = state.extra as InterviewConfigureArgs?;
          return Scaffold(body: Text('Configured category: ${args?.initialCategorySlug}'));
        },
      ),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Behavioral'));
    await tester.pumpAndSettle();

    expect(find.text('Configured category: behavioral'), findsOneWidget);
  });
}
