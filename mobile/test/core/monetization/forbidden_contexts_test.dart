// Explicit assertions (spec §48) that no ad widget is ever presented in the app's highest-stakes
// screens — an active aptitude session and an active interview session. `AdWidget`/`BannerAdSlot`
// must never appear in these widget trees, full stop, regardless of any ad configuration.

import 'package:careeros/core/monetization/widgets/banner_ad_slot.dart';
import 'package:careeros/features/aptitude/presentation/active_test_screen.dart';
import 'package:careeros/features/interview/presentation/interview_session_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../features/aptitude/aptitude_test_support.dart';
import '../../features/interview/interview_test_support.dart';
import '../../test_utils.dart';

void main() {
  testWidgets('No ad slot is ever presented during an active aptitude test session', (tester) async {
    useLargeTestViewport(tester);
    final session = buildSampleSession();
    final repo = FakeAptitudeRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: repo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => ActiveTestScreen(sessionId: session.id)),
    ]);
    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.byType(BannerAdSlot), findsNothing);
  });

  testWidgets('No ad slot is ever presented during an active interview session', (tester) async {
    useLargeTestViewport(tester);
    final session = buildSampleInterviewSession();
    final repo = FakeInterviewRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => InterviewSessionScreen(sessionId: session.id)),
    ]);
    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.byType(BannerAdSlot), findsNothing);
  });
}
