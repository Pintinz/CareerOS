import "package:shared_preferences/shared_preferences.dart";

/// Non-sensitive local flags (onboarding completion, last-selected filters, etc.).
/// Auth tokens never belong here — see [SecureStorage].
class AppPreferences {
  AppPreferences(this._prefs);

  final SharedPreferences _prefs;

  static const _onboardingCompleteKey = "onboarding_complete";

  static Future<AppPreferences> create() async {
    return AppPreferences(await SharedPreferences.getInstance());
  }

  bool get hasCompletedOnboarding => _prefs.getBool(_onboardingCompleteKey) ?? false;

  Future<void> setOnboardingComplete() => _prefs.setBool(_onboardingCompleteKey, true);
}
