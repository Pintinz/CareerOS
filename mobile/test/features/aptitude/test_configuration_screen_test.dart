import 'package:careeros/features/aptitude/presentation/test_configuration_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import 'aptitude_test_support.dart';

Widget _wrap(AptitudeConfigureArgs args, List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => TestConfigurationScreen(args: args)),
    GoRoute(
      path: '/prepare/aptitude/sessions/:id',
      builder: (context, state) => Scaffold(body: Text('Active test: ${state.pathParameters['id']}')),
    ),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

void main() {
  testWidgets('Mode chips are selectable, defaulting to Practice', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const AptitudeConfigureArgs(), overrides));
    await tester.pumpAndSettle();

    final practiceChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Practice'));
    expect(practiceChip.selected, isTrue);

    await tester.tap(find.text('Timed'));
    await tester.pumpAndSettle();

    final timedChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Timed'));
    expect(timedChip.selected, isTrue);
    // Timed mode forces a timer — Untimed becomes unselectable.
    final untimedChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Untimed'));
    expect(untimedChip.onSelected, isNull);
  });

  testWidgets('Sections can be selected singly and multiply', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const AptitudeConfigureArgs(), overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilterChip, 'Numerical Reasoning'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilterChip, 'Verbal Reasoning'));
    await tester.pumpAndSettle();

    final numericalChip = tester.widget<FilterChip>(find.widgetWithText(FilterChip, 'Numerical Reasoning'));
    final verbalChip = tester.widget<FilterChip>(find.widgetWithText(FilterChip, 'Verbal Reasoning'));
    expect(numericalChip.selected, isTrue);
    expect(verbalChip.selected, isTrue);
  });

  testWidgets('Starting a test creates a session and navigates to the exam screen', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository()..onCreateSession = () => buildSampleSession(id: 'new-session-42');
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const AptitudeConfigureArgs(), overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Start Assessment'));
    await tester.pumpAndSettle();

    expect(find.text('Active test: new-session-42'), findsOneWidget);
  });

  testWidgets('Practice Weak Areas context hides section selection and shows explanation', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: repo);

    await tester.pumpWidget(_wrap(const AptitudeConfigureArgs(topicSlugs: ['pumps']), overrides));
    await tester.pumpAndSettle();

    expect(find.textContaining('weighted toward your weakest topics'), findsOneWidget);
    expect(find.text('Sections'), findsNothing);
  });
}
