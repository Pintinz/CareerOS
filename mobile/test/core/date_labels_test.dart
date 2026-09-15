import 'package:careeros/core/utils/date_labels.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DateLabels', () {
    test('dateTime formats in device-local time', () {
      final utc = DateTime.utc(2026, 9, 18, 18, 25);
      final local = utc.toLocal();
      final hour = local.hour % 12 == 0 ? 12 : local.hour % 12;
      final minute = local.minute.toString().padLeft(2, '0');
      final suffix = local.hour < 12 ? 'AM' : 'PM';
      // intl separates the time and AM/PM with a narrow no-break space.
      final label = DateLabels.dateTime(utc).replaceAll(' ', ' ');
      expect(label, endsWith('$hour:$minute $suffix'));
      expect(label, startsWith('${local.day} Sep 2026, '));
    });

    test('shortDate uses the local calendar day of a UTC timestamp', () {
      final utc = DateTime.utc(2026, 9, 18, 23, 30);
      expect(DateLabels.shortDate(utc), '${utc.toLocal().day} ${utc.toLocal().month == 9 ? 'Sep' : 'Oct'} 2026');
    });

    test('date-only values are unchanged', () {
      expect(DateLabels.shortDate(DateTime(2026, 8, 26)), '26 Aug 2026');
    });

    test('published and deadline labels', () {
      final now = DateTime(2026, 9, 15, 12);
      expect(DateLabels.published(DateTime(2026, 9, 15, 8), now: now), 'Today');
      expect(DateLabels.published(DateTime(2026, 9, 13), now: now), '2d ago');
      expect(DateLabels.deadline(DateTime(2026, 9, 21), now: now), 'Closes in 6 days');
      expect(DateLabels.deadline(DateTime(2026, 9, 14), now: now), 'Closed');
    });
  });
}
