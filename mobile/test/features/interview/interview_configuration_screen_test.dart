import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/interview_configuration_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

Widget _wrap(InterviewConfigureArgs args, List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => InterviewConfigurationScreen(args: args)),
    GoRoute(
      path: '/prepare/interview/sessions/:id',
      builder: (context, state) => Scaffold(body: Text('Session: ${state.pathParameters['id']}')),
    ),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

void main() {
  testWidgets('Categories can be selected and mode chips switch between Practice and Mock', (tester) async {
    useLargeTestViewport(tester);
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: FakeInterviewRepository());

    await tester.pumpWidget(_wrap(const InterviewConfigureArgs(), overrides));
    await tester.pumpAndSettle();

    final practiceChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Question Practice'));
    expect(practiceChip.selected, isTrue);

    await tester.tap(find.widgetWithText(FilterChip, 'Behavioral'));
    await tester.pumpAndSettle();
    final behavioralChip = tester.widget<FilterChip>(find.widgetWithText(FilterChip, 'Behavioral'));
    expect(behavioralChip.selected, isTrue);

    await tester.tap(find.text('Mock Interview'));
    await tester.pumpAndSettle();
    final mockChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Mock Interview'));
    expect(mockChip.selected, isTrue);
  });

  testWidgets('Mock Interview defaults to Automatic Mix and shows the role-specific preview', (tester) async {
    useLargeTestViewport(tester);
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: FakeInterviewRepository());

    await tester.pumpWidget(_wrap(const InterviewConfigureArgs(initialMode: InterviewSessionMode.mock), overrides));
    await tester.pumpAndSettle();

    expect(find.text('Mock Interview Mix'), findsOneWidget);
    final autoChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Automatic Mix'));
    expect(autoChip.selected, isTrue);
    expect(find.textContaining('Technical 4'), findsOneWidget);
    expect(find.textContaining('Behavioral 3'), findsOneWidget);
    expect(find.text('Total: 7'), findsOneWidget);
  });

  testWidgets('Custom Mix requires category counts to sum to the question count before Start is enabled', (tester) async {
    useLargeTestViewport(tester);
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: FakeInterviewRepository());

    await tester.pumpWidget(_wrap(const InterviewConfigureArgs(initialMode: InterviewSessionMode.mock), overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(ChoiceChip, 'Custom Mix'));
    await tester.pumpAndSettle();

    expect(find.text('Total: 0 / 10'), findsOneWidget);
    final startButton = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Start'));
    expect(startButton.onPressed, isNull);

    // Bump Technical to 10 via its + button (first add_circle_outline icon).
    for (var i = 0; i < 10; i++) {
      await tester.tap(find.byIcon(Icons.add_circle_outline).first);
      await tester.pump();
    }
    await tester.pumpAndSettle();

    expect(find.text('Total: 10 / 10'), findsOneWidget);
    final enabledStartButton = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Start'));
    expect(enabledStartButton.onPressed, isNotNull);
  });

  testWidgets('Starting a session navigates to the interview session screen', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeInterviewRepository()..onCreateSession = () => buildSampleInterviewSession(id: 'new-interview-42');
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(_wrap(const InterviewConfigureArgs(), overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Start'));
    await tester.pumpAndSettle();

    expect(find.text('Session: new-interview-42'), findsOneWidget);
  });
}
