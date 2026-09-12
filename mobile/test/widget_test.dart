// Smoke test: the app boots to the splash screen without throwing. Deeper navigation/auth-flow
// tests need a mocked ApiClient/SecureStorage and are a Next Task (see PROJECT_STATUS.md) — this
// just proves `flutter test` runs against our real app rather than the stock counter template.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:careeros/core/app_providers.dart';
import 'package:careeros/core/storage/app_preferences.dart';
import 'package:careeros/main.dart';

class _FakeAppPreferences implements AppPreferences {
  @override
  bool get hasCompletedOnboarding => false;

  @override
  Future<void> setOnboardingComplete() async {}
}

void main() {
  testWidgets('App boots to the splash screen', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(
      ProviderScope(
        overrides: [appPreferencesProvider.overrideWithValue(_FakeAppPreferences())],
        child: const CareerOSApp(),
      ),
    );

    expect(find.text('CareerOS'), findsOneWidget);
  });
}
