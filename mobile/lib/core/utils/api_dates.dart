/// Parses a timestamp from the CareerOS API.
///
/// The backend stores every timestamp in UTC. A value that carries no offset (e.g.
/// "2026-09-15T18:21:33") is still UTC — reading it as device-local time shifts it by the device's
/// UTC offset, which made a fresh 30-minute aptitude test look expired in Lagos (UTC+1). Values with
/// an offset or "Z" are parsed as given; a date-only value ("2026-09-20") stays a calendar date.
DateTime parseApiDateTime(String value) {
  final text = value.trim();
  final hasTime = text.contains("T") || text.contains(" ");
  final hasOffset = RegExp(r"(Z|[+-]\d{2}(:?\d{2})?)$", caseSensitive: false).hasMatch(text);
  if (!hasTime || hasOffset) return DateTime.parse(text);
  return DateTime.parse("${text.replaceFirst(" ", "T")}Z");
}

/// [parseApiDateTime] for optional JSON fields.
DateTime? parseApiDateTimeOrNull(Object? value) => value is String && value.isNotEmpty ? parseApiDateTime(value) : null;
