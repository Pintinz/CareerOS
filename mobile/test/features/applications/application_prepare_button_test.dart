import 'package:careeros/features/applications/data/application_models.dart';
import 'package:careeros/features/applications/presentation/application_detail_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../aptitude/aptitude_test_support.dart';

Application _applicationAtStage(ApplicationStage stage) => Application(
      id: 'app-1',
      companyName: 'Acme Corp',
      roleTitle: 'Process Technician',
      currentStage: stage,
      updatedAt: DateTime.now(),
    );

void main() {
  testWidgets('Shows a real Prepare for Aptitude Test button when stage is Aptitude Test', (tester) async {
    final applicationRepo = FakeApplicationRepository(items: [_applicationAtStage(ApplicationStage.aptitudeTest)]);
    final aptitudeRepo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: aptitudeRepo, applicationRepository: applicationRepo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const ApplicationDetailScreen(applicationId: 'app-1')),
      GoRoute(path: '/prepare/aptitude/configure', builder: (context, state) => const Scaffold(body: Text('Configure Screen'))),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.text('Prepare for Aptitude Test'), findsOneWidget);
    expect(find.textContaining('never changes this'), findsOneWidget);

    await tester.tap(find.text('Prepare for Aptitude Test'));
    await tester.pumpAndSettle();

    expect(find.text('Configure Screen'), findsOneWidget);
  });

  testWidgets('Does not show the Aptitude button for an unrelated stage', (tester) async {
    // Medical is the one stage with neither a real aptitude nor a real interview prep flow —
    // Interview itself now has a real card (see application_interview_prep_test.dart), so it no
    // longer counts as "unrelated" for this assertion.
    final applicationRepo = FakeApplicationRepository(items: [_applicationAtStage(ApplicationStage.medical)]);
    final aptitudeRepo = FakeAptitudeRepository();
    final overrides = await aptitudeTestOverrides(repository: aptitudeRepo, applicationRepository: applicationRepo);

    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides,
        child: const MaterialApp(home: ApplicationDetailScreen(applicationId: 'app-1')),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Prepare for Aptitude Test'), findsNothing);
    expect(find.text('Interview Preparation'), findsNothing);
    expect(find.textContaining('medical/documentation'), findsOneWidget);
  });
}
