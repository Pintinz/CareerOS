import "package:intl/intl.dart";

import "../design/app_tone.dart";

/// Human, truthful time labels used on cards across the app.
///
/// API timestamps arrive in UTC; every label converts to device-local time first so a 23:30 UTC
/// event isn't shown as "tomorrow" (or at the wrong hour) in Lagos. Date-only values are already
/// local and pass through unchanged.
abstract final class DateLabels {
  static final _dayMonth = DateFormat("d MMM");
  static final _dayMonthYear = DateFormat("d MMM yyyy");
  static final _time = DateFormat.jm();

  /// "Today", "Yesterday", "3d ago", "2w ago", or "12 Mar" for older items.
  static String published(DateTime value, {DateTime? now}) {
    final date = value.toLocal();
    final reference = now ?? DateTime.now();
    final days = DateTime(reference.year, reference.month, reference.day)
        .difference(DateTime(date.year, date.month, date.day))
        .inDays;
    if (days <= 0) return "Today";
    if (days == 1) return "Yesterday";
    if (days < 7) return "${days}d ago";
    if (days < 28) return "${days ~/ 7}w ago";
    return date.year == reference.year ? _dayMonth.format(date) : _dayMonthYear.format(date);
  }

  /// "18 Sep 2026".
  static String shortDate(DateTime date) => _dayMonthYear.format(date.toLocal());

  /// "18 Sep 2026, 7:25 PM" — the one date-and-time format for scheduled events and timestamps.
  static String dateTime(DateTime value) {
    final local = value.toLocal();
    return "${_dayMonthYear.format(local)}, ${_time.format(local)}";
  }

  /// Whole days until [deadline] (negative once passed).
  static int daysUntil(DateTime value, {DateTime? now}) {
    final deadline = value.toLocal();
    final reference = now ?? DateTime.now();
    return DateTime(deadline.year, deadline.month, deadline.day)
        .difference(DateTime(reference.year, reference.month, reference.day))
        .inDays;
  }

  /// "Closes today", "Closes in 3 days", "Closes 12 Mar 2027", "Closed".
  static String deadline(DateTime deadline, {DateTime? now}) {
    final days = daysUntil(deadline, now: now);
    if (days < 0) return "Closed";
    if (days == 0) return "Closes today";
    if (days == 1) return "Closes tomorrow";
    if (days <= 30) return "Closes in $days days";
    return "Closes ${_dayMonthYear.format(deadline.toLocal())}";
  }

  /// Urgency tone for a deadline: danger within a week, warning within a month.
  static AppTone deadlineTone(DateTime deadline, {DateTime? now}) {
    final days = daysUntil(deadline, now: now);
    if (days < 0) return AppTone.neutral;
    if (days <= 7) return AppTone.danger;
    if (days <= 30) return AppTone.warning;
    return AppTone.neutral;
  }
}

/// "FULL_TIME" → "Full-time", "ON_SITE" → "On-site", "GRADUATE_RECRUITMENT" → "Graduate recruitment".
String humanizeEnum(String raw) {
  const special = {
    "FULL_TIME": "Full-time",
    "PART_TIME": "Part-time",
    "ON_SITE": "On-site",
    "FULLY_FUNDED": "Fully funded",
    "PARTIALLY_FUNDED": "Partially funded",
    "PARTIAL": "Partially funded",
    "AI": "AI",
    "PHD": "PhD",
  };
  final known = special[raw];
  if (known != null) return known;
  final words = raw.replaceAll("_", " ").toLowerCase();
  return words.isEmpty ? words : words[0].toUpperCase() + words.substring(1);
}
