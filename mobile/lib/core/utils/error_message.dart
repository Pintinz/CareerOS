import "../network/api_client.dart";

extension UserFacingErrorMessage on Object {
  /// Turns any caught error into text safe to show a user — never a raw exception (spec §79).
  String get userMessage => this is ApiException ? (this as ApiException).message : "Something went wrong. Please try again.";
}
