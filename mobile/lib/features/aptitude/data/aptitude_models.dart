import "../../../core/utils/api_dates.dart";

/// Mirrors backend `TestMode` (spec §6).
enum TestMode {
  practice,
  timed,
  mock,
  jobSpecific,
  fieldSpecific,
  companySpecific;

  static const _wireNames = {
    TestMode.practice: "PRACTICE",
    TestMode.timed: "TIMED",
    TestMode.mock: "MOCK",
    TestMode.jobSpecific: "JOB_SPECIFIC",
    TestMode.fieldSpecific: "FIELD_SPECIFIC",
    TestMode.companySpecific: "COMPANY_SPECIFIC",
  };

  String get wireValue => _wireNames[this]!;

  String get label => switch (this) {
        TestMode.practice => "Practice",
        TestMode.timed => "Timed",
        TestMode.mock => "Mock Assessment",
        TestMode.jobSpecific => "Job-Specific",
        TestMode.fieldSpecific => "Field-Specific",
        TestMode.companySpecific => "Company-Specific",
      };

  static TestMode fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

/// Mirrors backend `TestStatus`.
enum TestStatus {
  created,
  inProgress,
  submitted,
  autoSubmitted,
  abandoned;

  static const _wireNames = {
    TestStatus.created: "CREATED",
    TestStatus.inProgress: "IN_PROGRESS",
    TestStatus.submitted: "SUBMITTED",
    TestStatus.autoSubmitted: "AUTO_SUBMITTED",
    TestStatus.abandoned: "ABANDONED",
  };

  String get wireValue => _wireNames[this]!;
  bool get isSubmitted => this == TestStatus.submitted || this == TestStatus.autoSubmitted;

  static TestStatus fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

/// Mirrors backend `QuestionDifficulty`. "MIXED" is a request-only value (not a real difficulty
/// of a stored question), so it isn't a member of this enum.
enum QuestionDifficulty {
  easy,
  medium,
  hard,
  expert;

  static const _wireNames = {
    QuestionDifficulty.easy: "EASY",
    QuestionDifficulty.medium: "MEDIUM",
    QuestionDifficulty.hard: "HARD",
    QuestionDifficulty.expert: "EXPERT",
  };

  String get wireValue => _wireNames[this]!;
  String get label => switch (this) {
        QuestionDifficulty.easy => "Easy",
        QuestionDifficulty.medium => "Medium",
        QuestionDifficulty.hard => "Hard",
        QuestionDifficulty.expert => "Expert",
      };

  static QuestionDifficulty fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

enum QuestionType {
  singleChoice,
  multipleChoice,
  trueFalse,
  numeric,
  imageBased,
  passageBased;

  static const _wireNames = {
    QuestionType.singleChoice: "SINGLE_CHOICE",
    QuestionType.multipleChoice: "MULTIPLE_CHOICE",
    QuestionType.trueFalse: "TRUE_FALSE",
    QuestionType.numeric: "NUMERIC",
    QuestionType.imageBased: "IMAGE_BASED",
    QuestionType.passageBased: "PASSAGE_BASED",
  };

  String get wireValue => _wireNames[this]!;
  bool get isMultiSelect => this == QuestionType.multipleChoice;
  bool get isNumericEntry => this == QuestionType.numeric;

  static QuestionType fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

class QuestionCategory {
  const QuestionCategory({required this.id, required this.name, required this.slug, this.description});

  final String id;
  final String name;
  final String slug;
  final String? description;

  factory QuestionCategory.fromJson(Map<String, dynamic> json) => QuestionCategory(
        id: json["id"] as String,
        name: json["name"] as String,
        slug: json["slug"] as String,
        description: json["description"] as String?,
      );
}

class TestOption {
  const TestOption({
    required this.id,
    this.optionText,
    this.optionImageUrl,
    required this.displayOrder,
    this.isCorrect,
  });

  final String id;
  final String? optionText;
  final String? optionImageUrl;
  final int displayOrder;
  /// Only ever populated on [ReviewQuestion] options, after submission.
  final bool? isCorrect;

  factory TestOption.fromJson(Map<String, dynamic> json) => TestOption(
        id: json["id"] as String,
        optionText: json["option_text"] as String?,
        optionImageUrl: json["option_image_url"] as String?,
        displayOrder: json["display_order"] as int,
        isCorrect: json["is_correct"] as bool?,
      );
}

class SessionAnswerState {
  const SessionAnswerState({this.selectedOptionIds, this.answerNumericValue, this.isFlagged = false});

  final List<String>? selectedOptionIds;
  final double? answerNumericValue;
  final bool isFlagged;

  factory SessionAnswerState.fromJson(Map<String, dynamic> json) => SessionAnswerState(
        selectedOptionIds: (json["selected_option_ids"] as List?)?.map((e) => e as String).toList(),
        answerNumericValue: (json["answer_numeric_value"] as num?)?.toDouble(),
        isFlagged: json["is_flagged"] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        "selected_option_ids": selectedOptionIds,
        "answer_numeric_value": answerNumericValue,
        "is_flagged": isFlagged,
      };
}

class SessionQuestion {
  const SessionQuestion({
    required this.id,
    required this.orderIndex,
    required this.questionText,
    required this.questionType,
    this.questionImageUrl,
    this.passageText,
    required this.difficulty,
    required this.marks,
    required this.negativeMarks,
    required this.categoryName,
    this.topicName,
    this.topicSlug,
    required this.options,
    this.answerState,
  });

  final String id;
  final int orderIndex;
  final String questionText;
  final QuestionType questionType;
  final String? questionImageUrl;
  final String? passageText;
  final QuestionDifficulty difficulty;
  final double marks;
  final double negativeMarks;
  final String categoryName;
  final String? topicName;
  final String? topicSlug;
  final List<TestOption> options;
  final SessionAnswerState? answerState;

  bool get isAnswered {
    final state = answerState;
    if (state == null) return false;
    return (state.selectedOptionIds?.isNotEmpty ?? false) || state.answerNumericValue != null;
  }

  bool get isFlagged => answerState?.isFlagged ?? false;

  SessionQuestion copyWith({SessionAnswerState? answerState}) => SessionQuestion(
        id: id,
        orderIndex: orderIndex,
        questionText: questionText,
        questionType: questionType,
        questionImageUrl: questionImageUrl,
        passageText: passageText,
        difficulty: difficulty,
        marks: marks,
        negativeMarks: negativeMarks,
        categoryName: categoryName,
        topicName: topicName,
        topicSlug: topicSlug,
        options: options,
        answerState: answerState ?? this.answerState,
      );

  factory SessionQuestion.fromJson(Map<String, dynamic> json) => SessionQuestion(
        id: json["id"] as String,
        orderIndex: json["order_index"] as int,
        questionText: json["question_text"] as String,
        questionType: QuestionType.fromWire(json["question_type"] as String),
        questionImageUrl: json["question_image_url"] as String?,
        passageText: json["passage_text"] as String?,
        difficulty: QuestionDifficulty.fromWire(json["difficulty"] as String),
        marks: (json["marks"] as num).toDouble(),
        negativeMarks: (json["negative_marks"] as num).toDouble(),
        categoryName: json["category_name"] as String,
        topicName: json["topic_name"] as String?,
        topicSlug: json["topic_slug"] as String?,
        options: (json["options"] as List).map((e) => TestOption.fromJson(e as Map<String, dynamic>)).toList(),
        answerState: json["answer_state"] != null
            ? SessionAnswerState.fromJson(json["answer_state"] as Map<String, dynamic>)
            : null,
      );

  Map<String, dynamic> toJson() => {
        "id": id,
        "order_index": orderIndex,
        "question_text": questionText,
        "question_type": questionType.wireValue,
        "question_image_url": questionImageUrl,
        "passage_text": passageText,
        "difficulty": difficulty.wireValue,
        "marks": marks,
        "negative_marks": negativeMarks,
        "category_name": categoryName,
        "topic_name": topicName,
        "topic_slug": topicSlug,
        "options": options
            .map((o) => {
                  "id": o.id,
                  "option_text": o.optionText,
                  "option_image_url": o.optionImageUrl,
                  "display_order": o.displayOrder,
                })
            .toList(),
        "answer_state": answerState?.toJson(),
      };
}

class TestSessionDetail {
  const TestSessionDetail({
    required this.id,
    required this.mode,
    required this.status,
    this.applicationId,
    this.jobId,
    required this.startedAt,
    this.submittedAt,
    this.expiresAt,
    this.timeLimitSeconds,
    this.timeUsedSeconds,
    required this.autoSubmitted,
    required this.questionCount,
    required this.totalMarks,
    this.score,
    this.percentage,
    this.correctCount,
    this.incorrectCount,
    this.unansweredCount,
    this.sectionBreakdown,
    required this.questions,
    required this.serverTime,
    this.remainingSeconds,
  });

  final String id;
  final TestMode mode;
  final TestStatus status;
  final String? applicationId;
  final String? jobId;
  final DateTime? startedAt;
  final DateTime? submittedAt;
  final DateTime? expiresAt;
  final int? timeLimitSeconds;
  final int? timeUsedSeconds;
  final bool autoSubmitted;
  final int questionCount;
  final double totalMarks;
  final double? score;
  final double? percentage;
  final int? correctCount;
  final int? incorrectCount;
  final int? unansweredCount;
  final Map<String, dynamic>? sectionBreakdown;
  final List<SessionQuestion> questions;
  final DateTime serverTime;
  final int? remainingSeconds;

  TestSessionDetail copyWith({List<SessionQuestion>? questions, TestStatus? status, int? remainingSeconds}) =>
      TestSessionDetail(
        id: id,
        mode: mode,
        status: status ?? this.status,
        applicationId: applicationId,
        jobId: jobId,
        startedAt: startedAt,
        submittedAt: submittedAt,
        expiresAt: expiresAt,
        timeLimitSeconds: timeLimitSeconds,
        timeUsedSeconds: timeUsedSeconds,
        autoSubmitted: autoSubmitted,
        questionCount: questionCount,
        totalMarks: totalMarks,
        score: score,
        percentage: percentage,
        correctCount: correctCount,
        incorrectCount: incorrectCount,
        unansweredCount: unansweredCount,
        sectionBreakdown: sectionBreakdown,
        questions: questions ?? this.questions,
        serverTime: serverTime,
        remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      );

  factory TestSessionDetail.fromJson(Map<String, dynamic> json) => TestSessionDetail(
        id: json["id"] as String,
        mode: TestMode.fromWire(json["mode"] as String),
        status: TestStatus.fromWire(json["status"] as String),
        applicationId: json["application_id"] as String?,
        jobId: json["job_id"] as String?,
        startedAt: parseApiDateTimeOrNull(json["started_at"]),
        submittedAt: parseApiDateTimeOrNull(json["submitted_at"]),
        expiresAt: parseApiDateTimeOrNull(json["expires_at"]),
        timeLimitSeconds: json["time_limit_seconds"] as int?,
        timeUsedSeconds: json["time_used_seconds"] as int?,
        autoSubmitted: json["auto_submitted"] as bool,
        questionCount: json["question_count"] as int,
        totalMarks: (json["total_marks"] as num).toDouble(),
        score: (json["score"] as num?)?.toDouble(),
        percentage: (json["percentage"] as num?)?.toDouble(),
        correctCount: json["correct_count"] as int?,
        incorrectCount: json["incorrect_count"] as int?,
        unansweredCount: json["unanswered_count"] as int?,
        sectionBreakdown: json["section_breakdown"] as Map<String, dynamic>?,
        questions:
            (json["questions"] as List).map((e) => SessionQuestion.fromJson(e as Map<String, dynamic>)).toList(),
        serverTime: parseApiDateTime(json["server_time"] as String),
        remainingSeconds: json["remaining_seconds"] as int?,
      );

  Map<String, dynamic> toJson() => {
        "id": id,
        "mode": mode.wireValue,
        "status": status.wireValue,
        "application_id": applicationId,
        "job_id": jobId,
        "started_at": startedAt?.toIso8601String(),
        "submitted_at": submittedAt?.toIso8601String(),
        "expires_at": expiresAt?.toIso8601String(),
        "time_limit_seconds": timeLimitSeconds,
        "time_used_seconds": timeUsedSeconds,
        "auto_submitted": autoSubmitted,
        "question_count": questionCount,
        "total_marks": totalMarks,
        "score": score,
        "percentage": percentage,
        "correct_count": correctCount,
        "incorrect_count": incorrectCount,
        "unanswered_count": unansweredCount,
        "section_breakdown": sectionBreakdown,
        "questions": questions.map((q) => q.toJson()).toList(),
        "server_time": serverTime.toIso8601String(),
        "remaining_seconds": remainingSeconds,
      };
}

class TestSessionSummary {
  const TestSessionSummary({
    required this.id,
    required this.mode,
    required this.status,
    required this.questionCount,
    this.percentage,
    required this.createdAt,
  });

  final String id;
  final TestMode mode;
  final TestStatus status;
  final int questionCount;
  final double? percentage;
  final DateTime createdAt;

  factory TestSessionSummary.fromJson(Map<String, dynamic> json) => TestSessionSummary(
        id: json["id"] as String,
        mode: TestMode.fromWire(json["mode"] as String),
        status: TestStatus.fromWire(json["status"] as String),
        questionCount: json["question_count"] as int,
        percentage: (json["percentage"] as num?)?.toDouble(),
        createdAt: parseApiDateTime(json["created_at"] as String),
      );
}

class SectionResult {
  const SectionResult({required this.correct, required this.total, required this.percentage});

  final int correct;
  final int total;
  final double percentage;

  factory SectionResult.fromJson(Map<String, dynamic> json) => SectionResult(
        correct: json["correct"] as int,
        total: json["total"] as int,
        percentage: (json["percentage"] as num).toDouble(),
      );
}

class TestResult {
  const TestResult({
    required this.sessionId,
    required this.status,
    required this.score,
    required this.totalMarks,
    required this.percentage,
    required this.correctCount,
    required this.incorrectCount,
    required this.unansweredCount,
    this.timeUsedSeconds,
    this.timeLimitSeconds,
    required this.autoSubmitted,
    required this.sectionBreakdown,
    required this.performanceLabel,
  });

  final String sessionId;
  final TestStatus status;
  final double score;
  final double totalMarks;
  final double percentage;
  final int correctCount;
  final int incorrectCount;
  final int unansweredCount;
  final int? timeUsedSeconds;
  final int? timeLimitSeconds;
  final bool autoSubmitted;
  final Map<String, SectionResult> sectionBreakdown;
  final String performanceLabel;

  List<MapEntry<String, SectionResult>> get sectionsSortedByPercentage =>
      sectionBreakdown.entries.toList()..sort((a, b) => b.value.percentage.compareTo(a.value.percentage));

  factory TestResult.fromJson(Map<String, dynamic> json) => TestResult(
        sessionId: json["session_id"] as String,
        status: TestStatus.fromWire(json["status"] as String),
        score: (json["score"] as num).toDouble(),
        totalMarks: (json["total_marks"] as num).toDouble(),
        percentage: (json["percentage"] as num).toDouble(),
        correctCount: json["correct_count"] as int,
        incorrectCount: json["incorrect_count"] as int,
        unansweredCount: json["unanswered_count"] as int,
        timeUsedSeconds: json["time_used_seconds"] as int?,
        timeLimitSeconds: json["time_limit_seconds"] as int?,
        autoSubmitted: json["auto_submitted"] as bool,
        sectionBreakdown: (json["section_breakdown"] as Map<String, dynamic>).map(
          (key, value) => MapEntry(key, SectionResult.fromJson(value as Map<String, dynamic>)),
        ),
        performanceLabel: json["performance_label"] as String,
      );
}

class ReviewQuestion {
  const ReviewQuestion({
    required this.id,
    required this.orderIndex,
    required this.questionText,
    required this.questionType,
    this.questionImageUrl,
    this.passageText,
    required this.difficulty,
    required this.categoryName,
    this.topicName,
    this.topicSlug,
    required this.options,
    this.selectedOptionIds,
    this.answerNumericValue,
    this.correctNumericValue,
    this.isCorrect,
    this.marksAwarded,
    this.explanation,
    this.timeSpentSeconds,
  });

  final String id;
  final int orderIndex;
  final String questionText;
  final QuestionType questionType;
  final String? questionImageUrl;
  final String? passageText;
  final QuestionDifficulty difficulty;
  final String categoryName;
  final String? topicName;
  final String? topicSlug;
  final List<TestOption> options;
  final List<String>? selectedOptionIds;
  final double? answerNumericValue;
  final double? correctNumericValue;
  final bool? isCorrect;
  final double? marksAwarded;
  final String? explanation;
  final int? timeSpentSeconds;

  factory ReviewQuestion.fromJson(Map<String, dynamic> json) => ReviewQuestion(
        id: json["id"] as String,
        orderIndex: json["order_index"] as int,
        questionText: json["question_text"] as String,
        questionType: QuestionType.fromWire(json["question_type"] as String),
        questionImageUrl: json["question_image_url"] as String?,
        passageText: json["passage_text"] as String?,
        difficulty: QuestionDifficulty.fromWire(json["difficulty"] as String),
        categoryName: json["category_name"] as String,
        topicName: json["topic_name"] as String?,
        topicSlug: json["topic_slug"] as String?,
        options: (json["options"] as List).map((e) => TestOption.fromJson(e as Map<String, dynamic>)).toList(),
        selectedOptionIds: (json["selected_option_ids"] as List?)?.map((e) => e as String).toList(),
        answerNumericValue: (json["answer_numeric_value"] as num?)?.toDouble(),
        correctNumericValue: (json["correct_numeric_value"] as num?)?.toDouble(),
        isCorrect: json["is_correct"] as bool?,
        marksAwarded: (json["marks_awarded"] as num?)?.toDouble(),
        explanation: json["explanation"] as String?,
        timeSpentSeconds: json["time_spent_seconds"] as int?,
      );
}

class SessionReview {
  const SessionReview({required this.sessionId, required this.questions});

  final String sessionId;
  final List<ReviewQuestion> questions;

  factory SessionReview.fromJson(Map<String, dynamic> json) => SessionReview(
        sessionId: json["session_id"] as String,
        questions: (json["questions"] as List).map((e) => ReviewQuestion.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class CategoryStat {
  const CategoryStat({required this.attempted, required this.correct, required this.percentage});

  final int attempted;
  final int correct;
  final double percentage;

  factory CategoryStat.fromJson(Map<String, dynamic> json) => CategoryStat(
        attempted: json["attempted"] as int,
        correct: json["correct"] as int,
        percentage: (json["percentage"] as num).toDouble(),
      );
}

class TopicStat {
  const TopicStat({
    required this.categoryName,
    this.topicSlug,
    required this.attempted,
    required this.correct,
    required this.percentage,
  });

  final String categoryName;
  final String? topicSlug;
  final int attempted;
  final int correct;
  final double percentage;

  factory TopicStat.fromJson(Map<String, dynamic> json) => TopicStat(
        categoryName: json["category_name"] as String,
        topicSlug: json["topic_slug"] as String?,
        attempted: json["attempted"] as int,
        correct: json["correct"] as int,
        percentage: (json["percentage"] as num).toDouble(),
      );
}

class AptitudeAnalytics {
  const AptitudeAnalytics({
    required this.testsCompleted,
    required this.questionsAnswered,
    this.averageScore,
    this.bestScore,
    this.averageTimePerQuestionSeconds,
    required this.byCategory,
    required this.byTopic,
  });

  final int testsCompleted;
  final int questionsAnswered;
  final double? averageScore;
  final double? bestScore;
  final double? averageTimePerQuestionSeconds;
  final Map<String, CategoryStat> byCategory;
  final Map<String, TopicStat> byTopic;

  factory AptitudeAnalytics.fromJson(Map<String, dynamic> json) => AptitudeAnalytics(
        testsCompleted: json["tests_completed"] as int,
        questionsAnswered: json["questions_answered"] as int,
        averageScore: (json["average_score"] as num?)?.toDouble(),
        bestScore: (json["best_score"] as num?)?.toDouble(),
        averageTimePerQuestionSeconds: (json["average_time_per_question_seconds"] as num?)?.toDouble(),
        byCategory: (json["by_category"] as Map<String, dynamic>)
            .map((key, value) => MapEntry(key, CategoryStat.fromJson(value as Map<String, dynamic>))),
        byTopic: (json["by_topic"] as Map<String, dynamic>)
            .map((key, value) => MapEntry(key, TopicStat.fromJson(value as Map<String, dynamic>))),
      );

  static const empty = AptitudeAnalytics(
    testsCompleted: 0,
    questionsAnswered: 0,
    byCategory: {},
    byTopic: {},
  );
}

class WeakTopic {
  const WeakTopic({
    required this.topicName,
    this.topicSlug,
    required this.categoryName,
    required this.accuracy,
    required this.attempted,
  });

  final String topicName;
  final String? topicSlug;
  final String categoryName;
  final double accuracy;
  final int attempted;

  factory WeakTopic.fromJson(Map<String, dynamic> json) => WeakTopic(
        topicName: json["topic_name"] as String,
        topicSlug: json["topic_slug"] as String?,
        categoryName: json["category_name"] as String,
        accuracy: (json["accuracy"] as num).toDouble(),
        attempted: json["attempted"] as int,
      );
}

class Recommendations {
  const Recommendations({required this.weakTopics, required this.minAttemptsRequired});

  final List<WeakTopic> weakTopics;
  final int minAttemptsRequired;

  factory Recommendations.fromJson(Map<String, dynamic> json) => Recommendations(
        weakTopics: (json["weak_topics"] as List).map((e) => WeakTopic.fromJson(e as Map<String, dynamic>)).toList(),
        minAttemptsRequired: json["min_attempts_required"] as int,
      );

  static const empty = Recommendations(weakTopics: [], minAttemptsRequired: 3);
}
