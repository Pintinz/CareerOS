import 'package:careeros/core/app_providers.dart';
import 'package:careeros/core/network/api_client.dart';
import 'package:careeros/features/interview/data/interview_models.dart';
import 'package:careeros/features/interview/data/interview_offline_cache.dart';
import 'package:careeros/features/interview/presentation/interview_session_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../aptitude/aptitude_test_support.dart';
import 'interview_test_support.dart';

/// Always fails as if offline — simulates being disconnected once a session was already cached
/// (spec §36: "Allow an already-loaded practice session to continue offline").
class _AlwaysOfflineRepository extends FakeInterviewRepository {
  @override
  Future<InterviewSessionDetail> getSession(String sessionId) async {
    throw ApiException(ApiErrorKind.network, 'offline');
  }
}

void main() {
  testWidgets('An already-cached session keeps working when the server is unreachable', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final session = buildSampleInterviewSession();

    // Pre-populate the offline cache exactly as the controller would after a prior successful load.
    final cache = await InterviewOfflineCache.create();
    await cache.saveSession(session);

    final baseOverrides = await aptitudeTestOverrides(
      repository: FakeAptitudeRepository(),
      interviewRepository: _AlwaysOfflineRepository(),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          ...baseOverrides,
          // Override again with the pre-populated cache so build() finds the cached session.
          interviewOfflineCacheProvider.overrideWithValue(cache),
        ],
        child: MaterialApp(home: InterviewSessionScreen(sessionId: session.id)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text(session.questions.first.questionText), findsOneWidget);
    expect(find.byIcon(Icons.cloud_off), findsOneWidget);
  });
}
