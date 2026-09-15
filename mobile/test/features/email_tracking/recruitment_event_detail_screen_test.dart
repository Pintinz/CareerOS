import 'package:careeros/core/widgets/widgets.dart';
import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/applications/presentation/application_providers.dart';
import 'package:careeros/features/email_tracking/data/email_tracking_models.dart';
import 'package:careeros/features/email_tracking/presentation/email_tracking_providers.dart';
import 'package:careeros/features/email_tracking/presentation/recruitment_event_detail_screen.dart';
import 'package:careeros/features/email_tracking/presentation/recruitment_events_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'email_tracking_test_support.dart';

Widget _wrapList(FakeEmailTrackingRepository emailRepo, FakeApplicationRepository appRepo) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => const RecruitmentEventsScreen()),
    GoRoute(
      path: '/settings/tracking/events/:id',
      builder: (context, state) => RecruitmentEventDetailScreen(eventId: state.pathParameters['id']!),
    ),
  ]);
  return ProviderScope(
    overrides: [
      emailTrackingRepositoryProvider.overrideWithValue(emailRepo),
      applicationRepositoryProvider.overrideWithValue(appRepo),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

Application _application({required String id, String company = 'ExxonMobil', String role = 'Process Technician'}) {
  return Application(
    id: id,
    companyName: company,
    roleTitle: role,
    currentStage: ApplicationStage.applied,
    updatedAt: DateTime(2026, 1, 1),
  );
}

void main() {
  testWidgets('A suggested event shows Confirm/Wrong Application/Ignore and confirming calls the repository', (tester) async {
    useLargeTestViewport(tester);
    final application = _application(id: 'app-1');
    final event = buildSampleRecruitmentEvent(matchedApplicationId: 'app-1');
    final emailRepo = FakeEmailTrackingRepository()..events = [event];
    final appRepo = FakeApplicationRepository(items: [application]);

    await tester.pumpWidget(_wrapList(emailRepo, appRepo));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(CareerListRow).first);
    await tester.pumpAndSettle();

    expect(find.text('Aptitude Test'), findsWidgets);
    expect(find.text('Confirm Stage'), findsOneWidget);
    expect(find.text('Wrong Application'), findsOneWidget);
    expect(find.text('Ignore'), findsOneWidget);

    await tester.tap(find.text('Confirm Stage'));
    await tester.pumpAndSettle();

    expect(emailRepo.confirmCalls, ['event-1']);
    expect(find.text('Stage updated.'), findsOneWidget);
  });

  testWidgets('View Email Details shows the sender/subject/date and detection evidence, never a full inbox', (tester) async {
    useLargeTestViewport(tester);
    final application = _application(id: 'app-1');
    final event = buildSampleRecruitmentEvent(matchedApplicationId: 'app-1');
    final emailRepo = FakeEmailTrackingRepository()..events = [event];
    final appRepo = FakeApplicationRepository(items: [application]);

    await tester.pumpWidget(_wrapList(emailRepo, appRepo));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(CareerListRow).first);
    await tester.pumpAndSettle();

    expect(find.textContaining(event.subject), findsNothing);
    await tester.tap(find.text('View Email Details'));
    await tester.pumpAndSettle();

    expect(find.textContaining(event.subject), findsOneWidget);
    expect(find.textContaining('invited to complete an online assessment'), findsWidgets);
  });

  testWidgets('Ignoring an event marks it ignored and hides the action buttons', (tester) async {
    useLargeTestViewport(tester);
    final application = _application(id: 'app-1');
    final event = buildSampleRecruitmentEvent(matchedApplicationId: 'app-1');
    final emailRepo = FakeEmailTrackingRepository()..events = [event];
    final appRepo = FakeApplicationRepository(items: [application]);

    await tester.pumpWidget(_wrapList(emailRepo, appRepo));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(CareerListRow).first);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ignore'));
    await tester.pumpAndSettle();

    expect(emailRepo.ignoreCalls, ['event-1']);
    expect(find.text('Ignored'), findsOneWidget);
    expect(find.text('Confirm Stage'), findsNothing);
  });

  testWidgets('An ambiguous event asks which application it belongs to and assigning resolves it to Needs Review', (tester) async {
    useLargeTestViewport(tester);
    final apps = [
      _application(id: 'app-1', role: 'Graduate Engineer'),
      _application(id: 'app-2', role: 'Process Technician'),
      _application(id: 'app-3', role: 'Maintenance Technician'),
    ];
    final event = buildSampleRecruitmentEvent(
      status: RecruitmentEventStatus.ambiguous,
      candidateApplicationIds: ['app-1', 'app-2', 'app-3'],
      detectedStage: ApplicationStage.interview,
    );
    final emailRepo = FakeEmailTrackingRepository()..events = [event];
    final appRepo = FakeApplicationRepository(items: apps);

    await tester.pumpWidget(_wrapList(emailRepo, appRepo));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(CareerListRow).first);
    await tester.pumpAndSettle();

    expect(find.text('Which Application Does This Belong To?'), findsOneWidget);
    await tester.tap(find.text('Which Application Does This Belong To?'));
    await tester.pumpAndSettle();

    expect(find.text('Which application does this email belong to?'), findsOneWidget);
    expect(find.textContaining('Process Technician'), findsWidgets);
    expect(find.text('None of These'), findsOneWidget);

    await tester.tap(find.textContaining('ExxonMobil — Process Technician'));
    await tester.pumpAndSettle();

    expect(emailRepo.assignCalls, [('event-1', 'app-2')]);
    expect(find.text('Confirm Stage'), findsOneWidget);
  });
}
