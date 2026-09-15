import "package:careeros/core/design/design.dart";
import "package:careeros/core/widgets/widgets.dart";
import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";

Widget _host(Widget child) => MaterialApp(theme: AppTheme.light, home: Scaffold(body: Center(child: child)));

void main() {
  final checked = DateTime.now().subtract(const Duration(days: 2));

  testWidgets("a recently confirmed official listing says verified", (tester) async {
    await tester.pumpWidget(_host(SourceProvenance(isOfficialSource: true, lastVerifiedAt: checked, verificationStatus: "OFFICIAL_ATS")));
    expect(find.textContaining("Last verified"), findsOneWidget);
  });

  testWidgets("a stale confirmation is shown as last checked, never as verified", (tester) async {
    await tester.pumpWidget(_host(SourceProvenance(isOfficialSource: true, lastVerifiedAt: checked, verificationStatus: "STALE")));
    expect(find.textContaining("Last verified"), findsNothing);
    expect(find.textContaining("Last checked"), findsOneWidget);
  });

  testWidgets("nothing is claimed for a listing removed at its source", (tester) async {
    await tester.pumpWidget(_host(SourceProvenance(isOfficialSource: true, lastVerifiedAt: checked, verificationStatus: "SOURCE_REMOVED")));
    expect(find.textContaining("Official source"), findsNothing);
  });
}
