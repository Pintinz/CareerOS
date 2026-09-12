import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/interview_session_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

Widget _wrap(String sessionId, List<Override> overrides) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (context, state) => InterviewSessionScreen(sessionId: sessionId)),
    GoRoute(path: '/prepare/interview/sessions/:id/results', builder: (context, state) => const Scaffold(body: Text('Results Screen'))),
  ]);
  return ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router));
}

const _twoQuestions = [
  SessionQuestion(
    id: 'q1',
    orderIndex: 0,
    questionText: 'Tell me about a time you solved a difficult problem.',
    categoryName: 'Behavioral',
    difficulty: InterviewDifficulty.easy,
    answerGuidance: AnswerGuidance(assessing: 'Problem-solving approach', strongAnswerIncludes: ['A clear method']),
  ),
  SessionQuestion(
    id: 'q2',
    orderIndex: 1,
    questionText: 'Describe your leadership style.',
    categoryName: 'Leadership',
    difficulty: InterviewDifficulty.medium,
  ),
];

void main() {
  testWidgets('Question Practice: renders the question and Show Guidance reveals guidance', (tester) async {
    final session = buildSampleInterviewSession(questions: _twoQuestions);
    final repo = FakeInterviewRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    expect(find.text('Tell me about a time you solved a difficult problem.'), findsOneWidget);
    expect(find.text('Question 1 of 2'), findsOneWidget);
    expect(find.text('Show Guidance'), findsOneWidget);

    await tester.tap(find.text('Show Guidance'));
    await tester.pumpAndSettle();

    expect(find.text('Problem-solving approach'), findsOneWidget);
  });

  testWidgets('Typing an answer and marking practiced updates local state and syncs', (tester) async {
    useLargeTestViewport(tester);
    final session = buildSampleInterviewSession(questions: _twoQuestions);
    final repo = FakeInterviewRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Mark as Practiced'));
    await tester.pumpAndSettle();
    expect(repo.answerCalls.any((c) => c['isMarkedPracticed'] == true), isTrue);

    await tester.tap(find.text('4'));
    await tester.pumpAndSettle();
    expect(repo.answerCalls.any((c) => c['selfRating'] == 4), isTrue);
  });

  testWidgets('Next and Previous move between questions', (tester) async {
    final session = buildSampleInterviewSession(questions: _twoQuestions);
    final repo = FakeInterviewRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(ElevatedButton, 'Next'));
    await tester.pumpAndSettle();
    expect(find.text('Question 2 of 2'), findsOneWidget);
    expect(find.text('Describe your leadership style.'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Previous'));
    await tester.pumpAndSettle();
    expect(find.text('Question 1 of 2'), findsOneWidget);
  });

  testWidgets('Mock Interview mode shows a per-question countdown timer', (tester) async {
    final session = buildSampleInterviewSession(mode: InterviewSessionMode.mock, timePerQuestionSeconds: 90, questions: _twoQuestions);
    final repo = FakeInterviewRepository()..sessionProvider = (_) => session;
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(_wrap(session.id, overrides));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.timer_outlined), findsOneWidget);
    expect(find.textContaining('01:3'), findsOneWidget);
  });
}
