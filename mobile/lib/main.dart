import "dart:async";

import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "core/app_providers.dart";
import "core/monetization/monetization_providers.dart";
import "core/storage/app_preferences.dart";
import "features/aptitude/data/aptitude_offline_cache.dart";
import "features/interview/data/interview_offline_cache.dart";
import "routing/app_router.dart";
import "core/design/design.dart";
import "core/design/theme_mode_controller.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final appPreferences = await AppPreferences.create();
  final aptitudeOfflineCache = await AptitudeOfflineCache.create();
  final interviewOfflineCache = await InterviewOfflineCache.create();

  runApp(
    ProviderScope(
      overrides: [
        appPreferencesProvider.overrideWithValue(appPreferences),
        aptitudeOfflineCacheProvider.overrideWithValue(aptitudeOfflineCache),
        interviewOfflineCacheProvider.overrideWithValue(interviewOfflineCache),
      ],
      child: const CareerOSApp(),
    ),
  );
}

class CareerOSApp extends ConsumerStatefulWidget {
  const CareerOSApp({super.key});

  @override
  ConsumerState<CareerOSApp> createState() => _CareerOSAppState();
}

class _CareerOSAppState extends ConsumerState<CareerOSApp> {
  @override
  void initState() {
    super.initState();
    // Fire-and-forget (spec §3: "Ad initialization failure must NOT prevent CareerOS from
    // launching") — never awaited before the first frame, and AdService.initialize() itself
    // already catches every failure internally rather than throwing.
    unawaited(ref.read(adServiceProvider).initialize());
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: "CareerOS",
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ref.watch(themeModeProvider),
      routerConfig: router,
    );
  }
}
