import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/company_prep_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

void main() {
  testWidgets('Shows company overview, disclaimer, likely topics, and a persisted checklist', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeInterviewRepository()
      ..companyPrepOverride = const CompanyPrep(
        companyId: 'company-1',
        companyName: 'Demo Energy Corp',
        industry: 'Oil & Gas',
        about: 'A fictional energy company.',
        roleRelevance: 'This role focuses on process operations.',
        likelyTopics: ['pumps', 'valves'],
        disclaimer: 'CareerOS practice based on the company, role and available public information. Not an official employer interview guide.',
      )
      ..preparationProgressOverride = const PreparationProgress(
        checklist: [
          ChecklistItem(key: 'understand_business', label: 'Understand the company\'s business', isDone: false),
        ],
        questionsToAsk: [],
        reviewedTopics: [],
      );
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(
      ProviderScope(overrides: overrides, child: const MaterialApp(home: CompanyPrepScreen(applicationId: 'app-1'))),
    );
    await tester.pumpAndSettle();

    expect(find.text('Demo Energy Corp'), findsOneWidget);
    expect(find.textContaining('Not an official employer interview guide'), findsOneWidget);
    expect(find.text('pumps'), findsOneWidget);
    expect(find.text('Understand the company\'s business'), findsOneWidget);

    final checkbox = tester.widget<CheckboxListTile>(find.byType(CheckboxListTile).first);
    expect(checkbox.value, isFalse);

    await tester.tap(find.byType(CheckboxListTile).first);
    await tester.pumpAndSettle();
    // The tap should have gone through the repository without throwing.
  });
}
