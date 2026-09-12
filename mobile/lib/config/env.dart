/// Compile-time configuration, provided via --dart-define (never a bundled .env file, so
/// nothing here ships as plaintext in a way that differs between debug/release by accident).
///
/// Example:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
abstract final class Env {
  static const apiBaseUrl = String.fromEnvironment(
    "API_BASE_URL",
    defaultValue: "http://10.0.2.2:8000/api/v1", // Android emulator -> host machine localhost
  );

  static const admobAppId = String.fromEnvironment(
    "ADMOB_APP_ID",
    defaultValue: "", // empty => ad provider falls back to test unit IDs, see core/ads
  );

  static const environment = String.fromEnvironment("ENVIRONMENT", defaultValue: "development");

  static bool get isProduction => environment == "production";
}
