import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "core/app_providers.dart";
import "core/storage/app_preferences.dart";
import "features/aptitude/data/aptitude_offline_cache.dart";
import "routing/app_router.dart";
import "theme/app_theme.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final appPreferences = await AppPreferences.create();
  final aptitudeOfflineCache = await AptitudeOfflineCache.create();

  runApp(
    ProviderScope(
      overrides: [
        appPreferencesProvider.overrideWithValue(appPreferences),
        aptitudeOfflineCacheProvider.overrideWithValue(aptitudeOfflineCache),
      ],
      child: const CareerOSApp(),
    ),
  );
}

class CareerOSApp extends ConsumerWidget {
  const CareerOSApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: "CareerOS",
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
    );
  }
}
