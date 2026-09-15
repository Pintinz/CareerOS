import "package:careeros/core/utils/api_dates.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  test("a timestamp without an offset is read as UTC, never device-local time", () {
    final expires = parseApiDateTime("2026-09-15T18:21:33.456");
    expect(expires.isUtc, isTrue);
    expect(expires, DateTime.utc(2026, 9, 15, 18, 21, 33, 456));
    // A 30-minute test started at 17:51:33 UTC isn't expired, whatever the device's time zone.
    final serverNow = parseApiDateTime("2026-09-15T17:51:33.456+00:00");
    expect(expires.difference(serverNow), const Duration(minutes: 30));
  });

  test("offsets and Z are honoured as given", () {
    expect(parseApiDateTime("2026-09-15T18:21:33Z"), DateTime.utc(2026, 9, 15, 18, 21, 33));
    expect(parseApiDateTime("2026-09-15T19:21:33+01:00"), DateTime.utc(2026, 9, 15, 18, 21, 33));
  });

  test("date-only values stay calendar dates", () {
    final deadline = parseApiDateTime("2026-09-20");
    expect(deadline.isUtc, isFalse);
    expect((deadline.year, deadline.month, deadline.day), (2026, 9, 20));
  });

  test("optional fields", () {
    expect(parseApiDateTimeOrNull(null), isNull);
    expect(parseApiDateTimeOrNull(""), isNull);
    expect(parseApiDateTimeOrNull("2026-09-15T18:21:33"), DateTime.utc(2026, 9, 15, 18, 21, 33));
  });
}
