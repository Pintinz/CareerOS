import "dart:convert";

import "package:shared_preferences/shared_preferences.dart";

import "aptitude_models.dart";

/// A queued local mutation made while offline (or made optimistically before the server
/// confirms it) — replayed against the backend once connectivity returns. The backend remains
/// the authority: a queued mutation is only ever a best-effort mirror of what the user did
/// locally, never treated as final until the server accepts it.
class PendingMutation {
  const PendingMutation({
    required this.sessionId,
    required this.questionId,
    required this.isFlag,
    this.selectedOptionIds,
    this.answerNumericValue,
    this.timeSpentSeconds,
  });

  final String sessionId;
  final String questionId;
  final bool isFlag;
  final List<String>? selectedOptionIds;
  final double? answerNumericValue;
  final int? timeSpentSeconds;

  Map<String, dynamic> toJson() => {
        "session_id": sessionId,
        "question_id": questionId,
        "is_flag": isFlag,
        "selected_option_ids": selectedOptionIds,
        "answer_numeric_value": answerNumericValue,
        "time_spent_seconds": timeSpentSeconds,
      };

  factory PendingMutation.fromJson(Map<String, dynamic> json) => PendingMutation(
        sessionId: json["session_id"] as String,
        questionId: json["question_id"] as String,
        isFlag: json["is_flag"] as bool,
        selectedOptionIds: (json["selected_option_ids"] as List?)?.map((e) => e as String).toList(),
        answerNumericValue: (json["answer_numeric_value"] as num?)?.toDouble(),
        timeSpentSeconds: json["time_spent_seconds"] as int?,
      );
}

/// Local persistence for an in-progress test session (spec §20-21): once a session is
/// downloaded/started, the device must survive a temporary connectivity loss, an app restart,
/// or being backgrounded without losing the timer, answers, or flags. Uses SharedPreferences
/// (already the app's local key-value store — see AppPreferences) rather than the Drift SQLite
/// dependency, which nothing in this codebase actually wires up yet: a single JSON blob per
/// active session is a proportionate amount of local storage machinery for this feature.
class AptitudeOfflineCache {
  AptitudeOfflineCache(this._prefs);

  final SharedPreferences _prefs;

  static Future<AptitudeOfflineCache> create() async => AptitudeOfflineCache(await SharedPreferences.getInstance());

  static const _sessionKeyPrefix = "aptitude_session_";
  static const _mutationsKey = "aptitude_pending_mutations";

  Future<void> saveSession(TestSessionDetail detail) =>
      _prefs.setString("$_sessionKeyPrefix${detail.id}", jsonEncode(detail.toJson()));

  TestSessionDetail? loadSession(String sessionId) {
    final raw = _prefs.getString("$_sessionKeyPrefix$sessionId");
    if (raw == null) return null;
    try {
      return TestSessionDetail.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> clearSession(String sessionId) => _prefs.remove("$_sessionKeyPrefix$sessionId");

  /// Removes every cached session and pending mutation — used on logout and account deletion so
  /// no private answers remain on the device for the next user.
  Future<void> clearAll() async {
    for (final key in _prefs.getKeys().where((k) => k.startsWith(_sessionKeyPrefix)).toList()) {
      await _prefs.remove(key);
    }
    await _prefs.remove(_mutationsKey);
  }

  List<PendingMutation> pendingMutationsFor(String sessionId) {
    return _allMutations().where((m) => m.sessionId == sessionId).toList();
  }

  Future<void> enqueueMutation(PendingMutation mutation) async {
    // A newer mutation for the same question supersedes an older one — no point replaying stale
    // intermediate answers once the user has moved on.
    final remaining = _allMutations()
        .where((m) => !(m.sessionId == mutation.sessionId && m.questionId == mutation.questionId && m.isFlag == mutation.isFlag))
        .toList()
      ..add(mutation);
    await _prefs.setString(_mutationsKey, jsonEncode(remaining.map((m) => m.toJson()).toList()));
  }

  Future<void> clearMutationsForSession(String sessionId) async {
    final remaining = _allMutations().where((m) => m.sessionId != sessionId).toList();
    await _prefs.setString(_mutationsKey, jsonEncode(remaining.map((m) => m.toJson()).toList()));
  }

  List<PendingMutation> _allMutations() {
    final raw = _prefs.getString(_mutationsKey);
    if (raw == null) return [];
    try {
      return (jsonDecode(raw) as List).map((e) => PendingMutation.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      return [];
    }
  }
}
