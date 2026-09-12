import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// The default test surface (~800x600) is too small for these screens' full-length ListViews —
/// Flutter only builds Elements for children within the viewport/cache extent, so content
/// further down never renders and `find` can't see it even though it "exists" in the widget
/// list. Growing the surface avoids scrolling gymnastics in every test.
void useLargeTestViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}
