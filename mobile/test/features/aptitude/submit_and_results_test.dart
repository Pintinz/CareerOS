import 'package:careeros/features/aptitude/data/aptitude_models.dart';
import 'package:careeros/features/aptitude/presentation/question_review_screen.dart';
import 'package:careeros/features/aptitude/presentation/submit_confirmation_dialog.dart';
import 'package:careeros/features/aptitude/presentation/test_results_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import 'aptitude_test_support.dart';

void main() {
  group('Submit confirmation dialog', () {
    testWidgets('Shows answered/unanswered/flagged counts and remaining time', (tester) async {
      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await showSubmitConfirmationDialog(
                    context,
                    answered: 8,
                    unanswered: 2,
                    flagged: 1,
                    remainingSeconds: 125,
                  );
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.text('Submit Test?'), findsOneWidget);
      expect(find.text('Answered: 8'), findsOneWidget);
      expect(find.text('Unanswered: 2'), findsOneWidget);
      expect(find.text('Flagged: 1'), findsOneWidget);
      expect(find.text('2m 5s remaining'), findsOneWidget);

      await tester.tap(find.text('Submit'));
      await tester.pumpAndSettle();
      expect(result, isTrue);
    });

    testWidgets('Continue Test dismisses without submitting', (tester) async {
      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await showSubmitConfirmationDialog(context, answered: 1, unanswered: 1, flagged: 0);
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Continue Test'));
      await tester.pumpAndSettle();

      expect(result, isFalse);
    });
  });

  group('Results screen', () {
    testWidgets('Shows score, breakdown, and strongest/weakest areas', (tester) async {
      useLargeTestViewport(tester);
      final session = buildSampleSession(status: TestStatus.submitted);
      final repo = FakeAptitudeRepository();
      // Assigned as separate statements (not chained with `..`) — a cascade after an assignment
      // whose RHS is an arrow-function expression binds to that expression's result, not to the
      // outer receiver, which silently attaches `resultOverride` to `session` instead of `repo`.
      repo.sessionProvider = (_) => session;
      repo.resultOverride = TestResult(
        sessionId: session.id,
        status: TestStatus.submitted,
        score: 6,
        totalMarks: 8,
        percentage: 75,
        correctCount: 6,
        incorrectCount: 2,
        unansweredCount: 0,
        timeUsedSeconds: 300,
        timeLimitSeconds: null,
        autoSubmitted: false,
        sectionBreakdown: const {
          'Numerical Reasoning': SectionResult(correct: 5, total: 5, percentage: 100),
          'Verbal Reasoning': SectionResult(correct: 1, total: 3, percentage: 33.3),
        },
        performanceLabel: 'Strong Performance',
      );
      final overrides = await aptitudeTestOverrides(repository: repo);

      final router = GoRouter(routes: [
        GoRoute(path: '/', builder: (context, state) => TestResultsScreen(sessionId: session.id)),
      ]);

      await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
      await tester.pumpAndSettle();

      expect(find.text('75%'), findsOneWidget);
      expect(find.text('Strong Performance'), findsOneWidget);
      expect(find.text('Correct'), findsOneWidget);
      expect(find.text('6'), findsOneWidget);
      expect(find.text('Review Answers'), findsOneWidget);
      expect(find.text('Strongest Area'), findsOneWidget);
      expect(find.text('Weakest Area'), findsOneWidget);
      // Each section name appears twice: once in the breakdown list, once as the
      // strongest/weakest area card's name (Numerical Reasoning is strongest at 100%,
      // Verbal Reasoning is weakest at 33.3%).
      expect(find.text('Numerical Reasoning'), findsNWidgets(2));
      expect(find.text('Verbal Reasoning'), findsNWidgets(2));
    });
  });

  group('Question review screen', () {
    testWidgets('Shows correct/incorrect indicators and explanation only after submission', (tester) async {
      const review = SessionReview(
        sessionId: 'session-1',
        questions: [
          ReviewQuestion(
            id: 'q1',
            orderIndex: 0,
            questionText: 'What is 15% of 200?',
            questionType: QuestionType.singleChoice,
            difficulty: QuestionDifficulty.easy,
            categoryName: 'Numerical Reasoning',
            topicName: 'Percentages',
            options: [
              TestOption(id: 'opt-correct', optionText: '30', displayOrder: 0, isCorrect: true),
              TestOption(id: 'opt-wrong', optionText: '20', displayOrder: 1, isCorrect: false),
            ],
            selectedOptionIds: ['opt-wrong'],
            isCorrect: false,
            marksAwarded: -0.25,
            explanation: '15% of 200 = 30.',
          ),
        ],
      );
      final repo = FakeAptitudeRepository()..reviewOverride = review;
      final overrides = await aptitudeTestOverrides(repository: repo);

      await tester.pumpWidget(
        ProviderScope(overrides: overrides, child: const MaterialApp(home: QuestionReviewScreen(sessionId: 'session-1'))),
      );
      await tester.pumpAndSettle();

      expect(find.text('Incorrect'), findsOneWidget);
      expect(find.text('15% of 200 = 30.'), findsOneWidget);
      expect(find.text('Your answer'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget); // marks the correct option
      expect(find.byIcon(Icons.cancel), findsOneWidget); // marks the wrongly-selected option
    });
  });
}
