import 'package:careeros/features/aptitude/presentation/active_test_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'aptitude_test_support.dart';

Widget _wrap(String sessionId, List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => ActiveTestScreen(sessionId: sessionId)),
    GoRoute(
      path: '/prepare/aptitude/sessions/:id/results',
      builder: (context, state) => const Scaffold(body: Text('Results Screen')),
    ),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

void main() {
  testWidgets('Renders the current question with its options', (tester) async {
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    expect(find.text('What is 15% of 200?'), findsOneWidget);
    expect(find.text('30'), findsOneWidget);
    expect(find.text('20'), findsOneWidget);
    expect(find.text('Question 1 of 2'), findsOneWidget);
  });

  testWidgets('Selecting an option marks it selected and syncs to the repository', (tester) async {
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.text('30'));
    await tester.pumpAndSettle();

    expect(repo.answerCalls, hasLength(1));
    expect(repo.answerCalls.first['selectedOptionIds'], ['opt-correct']);
    expect(find.byIcon(Icons.radio_button_checked), findsOneWidget);
  });

  testWidgets('Next and Previous move between questions', (tester) async {
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'Next'));
    await tester.pumpAndSettle();
    expect(find.text('Question 2 of 2'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Previous'));
    await tester.pumpAndSettle();
    expect(find.text('Question 1 of 2'), findsOneWidget);
  });

  testWidgets('Flagging a question toggles the flag icon and syncs to the repository', (tester) async {
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.flag_outlined), findsOneWidget);

    await tester.tap(find.byIcon(Icons.flag_outlined));
    await tester.pumpAndSettle();

    expect(repo.flagCalls, contains('q1'));
    expect(find.byIcon(Icons.flag), findsOneWidget);
  });

  testWidgets('Question Navigator opens and jumps to the tapped question', (tester) async {
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.grid_view_rounded));
    await tester.pumpAndSettle();

    expect(find.text('Question Navigator'), findsOneWidget);

    await tester.tap(find.text('2'));
    await tester.pumpAndSettle();

    expect(find.text('Question 2 of 2'), findsOneWidget);
  });

  testWidgets('A timed session shows a countdown badge in the header', (tester) async {
    final session = buildSampleSession(
      expiresAt: DateTime.now().add(const Duration(minutes: 10)),
      timeLimitSeconds: 600,
    );
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.timer_outlined), findsOneWidget);
  });
}
