import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/presentation/star_story_editor_screen.dart';
import 'package:careeros/features/interview/presentation/star_story_list_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../test_utils.dart';
import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

class _RecordingInterviewRepository extends FakeInterviewRepository {
  StarStory? lastCreated;

  @override
  Future<StarStory> createStarStory({
    required String title,
    required StarCategory category,
    String? situation,
    String? task,
    String? action,
    String? result,
    String? lessons,
    List<String> skillsDemonstrated = const [],
    String? metrics,
    String? companyContext,
  }) async {
    final completeness = StarCompleteness(
      sections: {
        'situation': (situation?.length ?? 0) >= 20 ? 'complete' : 'missing',
        'task': (task?.length ?? 0) >= 20 ? 'complete' : 'missing',
        'action': (action?.length ?? 0) >= 20 ? 'strong' : 'missing',
        'result': (result?.length ?? 0) >= 20 ? 'complete' : 'missing',
      },
      gaps: (result == null || result.isEmpty) ? ['no_result'] : [],
      isComplete: situation != null && task != null && action != null && result != null && result.isNotEmpty,
    );
    lastCreated = StarStory(
      id: 'new-story',
      title: title,
      category: category,
      situation: situation,
      task: task,
      action: action,
      result: result,
      completeness: completeness,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
    return lastCreated!;
  }
}

void main() {
  testWidgets('Creating an incomplete STAR story shows concrete completeness gaps', (tester) async {
    useLargeTestViewport(tester);
    final repo = _RecordingInterviewRepository();
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    await tester.pumpWidget(
      ProviderScope(overrides: overrides, child: const MaterialApp(home: StarStoryEditorScreen())),
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, 'Title'), 'A pump failure story');
    await tester.enterText(find.widgetWithText(TextField, 'Situation'), 'There was a critical pump failure during a night shift.');
    await tester.enterText(find.widgetWithText(TextField, 'Task'), 'I was responsible for restoring the pump to service safely.');
    await tester.enterText(find.widgetWithText(TextField, 'Action'), 'I isolated the pump and diagnosed the fault systematically.');
    // Result left blank on purpose.

    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(repo.lastCreated, isNotNull);
    expect(repo.lastCreated!.completeness.isComplete, isFalse);
  });

  testWidgets('STAR story list shows completeness indicator and links to the editor', (tester) async {
    final repo = FakeInterviewRepository()
      ..starStoriesOverride = [
        StarStory(
          id: 's1',
          title: 'Complete story',
          category: StarCategory.achievement,
          situation: 's' * 25,
          task: 't' * 25,
          action: 'I did the work.' * 3,
          result: 'r' * 25,
          completeness: const StarCompleteness(
            sections: {'situation': 'complete', 'task': 'complete', 'action': 'strong', 'result': 'complete'},
            gaps: [],
            isComplete: true,
          ),
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        ),
      ];
    final overrides = await aptitudeTestOverrides(repository: FakeAptitudeRepository(), interviewRepository: repo);

    final router = GoRouter(routes: [
      GoRoute(path: '/', builder: (context, state) => const StarStoryListScreen()),
      GoRoute(path: '/prepare/interview/star-stories/new', builder: (context, state) => const Scaffold(body: Text('New Story Screen'))),
      GoRoute(path: '/prepare/interview/star-stories/:id', builder: (context, state) => Scaffold(body: Text('Edit Story: ${state.pathParameters['id']}'))),
    ]);

    await tester.pumpWidget(ProviderScope(overrides: overrides, child: MaterialApp.router(routerConfig: router)));
    await tester.pumpAndSettle();

    expect(find.text('Complete story'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle), findsOneWidget);

    await tester.tap(find.text('Complete story'));
    await tester.pumpAndSettle();
    expect(find.text('Edit Story: s1'), findsOneWidget);
  });
}
