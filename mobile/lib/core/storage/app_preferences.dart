import "package:flutter/material.dart" show ThemeMode;
import "package:shared_preferences/shared_preferences.dart";

/// Non-sensitive local flags (onboarding completion, appearance, last-selected filters, etc.).
/// Auth tokens never belong here — see [SecureStorage].
class AppPreferences {
  AppPreferences(this._prefs);

  final SharedPreferences _prefs;

  static const _onboardingCompleteKey = "onboarding_complete";
  static const _themeModeKey = "theme_mode";

  static Future<AppPreferences> create() async {
    return AppPreferences(await SharedPreferences.getInstance());
  }

  bool get hasCompletedOnboarding => _prefs.getBool(_onboardingCompleteKey) ?? false;

  Future<void> setOnboardingComplete() => _prefs.setBool(_onboardingCompleteKey, true);

  ThemeMode get themeMode => switch (_prefs.getString(_themeModeKey)) {
        "light" => ThemeMode.light,
        "dark" => ThemeMode.dark,
        _ => ThemeMode.system,
      };

  Future<void> setThemeMode(ThemeMode mode) => _prefs.setString(_themeModeKey, mode.name);
}
