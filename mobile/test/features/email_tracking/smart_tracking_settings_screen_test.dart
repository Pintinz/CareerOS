import 'package:careeros/features/email_tracking/data/email_tracking_models.dart';
import 'package:careeros/features/email_tracking/presentation/email_tracking_providers.dart';
import 'package:careeros/features/email_tracking/presentation/smart_tracking_settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../test_utils.dart';
import 'email_tracking_test_support.dart';

Widget _wrap(FakeEmailTrackingRepository repository) {
  return ProviderScope(
    overrides: [emailTrackingRepositoryProvider.overrideWithValue(repository)],
    child: const MaterialApp(home: SmartTrackingSettingsScreen()),
  );
}

void main() {
  testWidgets('Explains the privacy guarantee and shows Manual Tracking as always available', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository();

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    expect(find.textContaining('CareerOS will never change an application stage without your confirmation.'), findsOneWidget);
    expect(find.text('Manual Tracking'), findsOneWidget);
  });

  testWidgets('Unavailable providers show "Coming soon" and no Connect button', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(gmailAvailable: false, outlookAvailable: false, forwardEmailAvailable: false);

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    expect(find.text('Coming soon'), findsNWidgets(3)); // Gmail, Outlook, Forward Email.
    expect(find.widgetWithText(OutlinedButton, 'Connect'), findsNothing);
  });

  testWidgets('An available provider without a connection offers Connect', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(gmailAvailable: true, outlookAvailable: false, forwardEmailAvailable: false);

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    final connect = tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Connect'));
    expect(connect.onPressed, isNotNull);
    expect(find.text('Coming soon'), findsNWidgets(2)); // Outlook, Forward Email.
  });

  testWidgets('An active connection shows the connected email and a Disconnect action', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(gmailAvailable: true, outlookAvailable: false, forwardEmailAvailable: false)
      ..connections = [
        EmailConnection(
          id: 'conn-1',
          provider: EmailProvider.gmail,
          providerEmail: 'me@gmail.com',
          status: EmailConnectionStatus.active,
          grantedScopes: const ['gmail.readonly'],
          createdAt: DateTime(2026, 1, 1),
        ),
      ];

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    expect(find.text('me@gmail.com'), findsOneWidget);
    expect(find.text('Connected'), findsOneWidget);
    expect(find.text('Disconnect'), findsOneWidget);
  });

  testWidgets('A connection needing reauthorization shows Reconnect', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(gmailAvailable: true, outlookAvailable: false, forwardEmailAvailable: false)
      ..connections = [
        EmailConnection(
          id: 'conn-1',
          provider: EmailProvider.gmail,
          providerEmail: 'me@gmail.com',
          status: EmailConnectionStatus.reauthorizationRequired,
          grantedScopes: const ['gmail.readonly'],
          createdAt: DateTime(2026, 1, 1),
        ),
      ];

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    expect(find.text('Reauthorization Required'), findsOneWidget);
    expect(find.text('Reconnect'), findsOneWidget);
  });

  testWidgets('Disconnect removes the connection after confirming', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(gmailAvailable: true, outlookAvailable: false, forwardEmailAvailable: false)
      ..connections = [
        EmailConnection(
          id: 'conn-1',
          provider: EmailProvider.gmail,
          providerEmail: 'me@gmail.com',
          status: EmailConnectionStatus.active,
          grantedScopes: const ['gmail.readonly'],
          createdAt: DateTime(2026, 1, 1),
        ),
      ];

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Disconnect'));
    await tester.pumpAndSettle();
    await tester.tap(find.descendant(of: find.byType(AlertDialog), matching: find.text('Disconnect')));
    await tester.pumpAndSettle();

    expect(repo.disconnectCalls, ['conn-1']);
    expect(find.text('me@gmail.com'), findsNothing);
  });

  testWidgets('Forward Email alias is shown when available', (tester) async {
    useLargeTestViewport(tester);
    final repo = FakeEmailTrackingRepository()
      ..availability = const ProviderAvailability(
        gmailAvailable: false,
        outlookAvailable: false,
        forwardEmailAvailable: true,
        forwardEmailAlias: 'apply+abc123@mail.careeros.app',
      );

    await tester.pumpWidget(_wrap(repo));
    await tester.pumpAndSettle();

    expect(find.text('apply+abc123@mail.careeros.app'), findsOneWidget);
  });
}
