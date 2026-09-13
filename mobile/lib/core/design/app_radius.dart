import "package:flutter/widgets.dart";

/// Corner radii. Pills are reserved for chips, filters, tags and statuses.
abstract final class AppRadius {
  static const double sm = 8;
  static const double md = 12;
  static const double button = 14;
  static const double card = 16;
  static const double feature = 20;
  static const double hero = 24;
  static const double sheet = 24;
  static const double pill = 999;

  static const BorderRadius smAll = BorderRadius.all(Radius.circular(sm));
  static const BorderRadius mdAll = BorderRadius.all(Radius.circular(md));
  static const BorderRadius buttonAll = BorderRadius.all(Radius.circular(button));
  static const BorderRadius cardAll = BorderRadius.all(Radius.circular(card));
  static const BorderRadius featureAll = BorderRadius.all(Radius.circular(feature));
  static const BorderRadius heroAll = BorderRadius.all(Radius.circular(hero));
  static const BorderRadius pillAll = BorderRadius.all(Radius.circular(pill));
  static const BorderRadius sheetTop = BorderRadius.vertical(top: Radius.circular(sheet));
}
