enum InterviewDifficulty {
  easy,
  medium,
  hard,
  expert;

  static const _wireNames = {
    InterviewDifficulty.easy: "EASY",
    InterviewDifficulty.medium: "MEDIUM",
    InterviewDifficulty.hard: "HARD",
    InterviewDifficulty.expert: "EXPERT",
  };

  String get wireValue => _wireNames[this]!;
  String get label => switch (this) {
        InterviewDifficulty.easy => "Easy",
        InterviewDifficulty.medium => "Medium",
        InterviewDifficulty.hard => "Hard",
        InterviewDifficulty.expert => "Expert",
      };

  static InterviewDifficulty fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

enum InterviewSessionMode {
  practice,
  mock;

  static const _wireNames = {InterviewSessionMode.practice: "PRACTICE", InterviewSessionMode.mock: "MOCK"};
  String get wireValue => _wireNames[this]!;
  String get label => this == InterviewSessionMode.mock ? "Mock Interview" : "Question Practice";
  static InterviewSessionMode fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

enum InterviewSessionStatus {
  inProgress,
  completed,
  abandoned;

  static const _wireNames = {
    InterviewSessionStatus.inProgress: "IN_PROGRESS",
    InterviewSessionStatus.completed: "COMPLETED",
    InterviewSessionStatus.abandoned: "ABANDONED",
  };
  String get wireValue => _wireNames[this]!;
  bool get isCompleted => this == InterviewSessionStatus.completed;
  static InterviewSessionStatus fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

/// Mirrors backend `StarCategory` (spec §14).
enum StarCategory {
  safety,
  leadership,
  teamwork,
  conflict,
  equipmentFailure,
  problemSolving,
  processImprovement,
  failureLesson,
  pressure,
  achievement,
  customer,
  innovation,
  communication,
  decisionMaking;

  static const _wireNames = {
    StarCategory.safety: "SAFETY",
    StarCategory.leadership: "LEADERSHIP",
    StarCategory.teamwork: "TEAMWORK",
    StarCategory.conflict: "CONFLICT",
    StarCategory.equipmentFailure: "EQUIPMENT_FAILURE",
    StarCategory.problemSolving: "PROBLEM_SOLVING",
    StarCategory.processImprovement: "PROCESS_IMPROVEMENT",
    StarCategory.failureLesson: "FAILURE_LESSON",
    StarCategory.pressure: "PRESSURE",
    StarCategory.achievement: "ACHIEVEMENT",
    StarCategory.customer: "CUSTOMER",
    StarCategory.innovation: "INNOVATION",
    StarCategory.communication: "COMMUNICATION",
    StarCategory.decisionMaking: "DECISION_MAKING",
  };

  String get wireValue => _wireNames[this]!;
  String get label => switch (this) {
        StarCategory.safety => "Safety",
        StarCategory.leadership => "Leadership",
        StarCategory.teamwork => "Teamwork",
        StarCategory.conflict => "Conflict",
        StarCategory.equipmentFailure => "Equipment Failure",
        StarCategory.problemSolving => "Problem Solving",
        StarCategory.processImprovement => "Process Improvement",
        StarCategory.failureLesson => "Failure / Lesson",
        StarCategory.pressure => "Pressure",
        StarCategory.achievement => "Achievement",
        StarCategory.customer => "Customer",
        StarCategory.innovation => "Innovation",
        StarCategory.communication => "Communication",
        StarCategory.decisionMaking => "Decision Making",
      };

  static StarCategory fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

class InterviewCategory {
  const InterviewCategory({required this.id, required this.name, required this.slug, this.description});

  final String id;
  final String name;
  final String slug;
  final String? description;

  factory InterviewCategory.fromJson(Map<String, dynamic> json) => InterviewCategory(
        id: json["id"] as String,
        name: json["name"] as String,
        slug: json["slug"] as String,
        description: json["description"] as String?,
      );
}

class AnswerGuidance {
  const AnswerGuidance({this.assessing, this.strongAnswerIncludes = const [], this.commonMistakes = const [], this.technicalConcepts = const []});

  final String? assessing;
  final List<String> strongAnswerIncludes;
  final List<String> commonMistakes;
  final List<String> technicalConcepts;

  factory AnswerGuidance.fromJson(Map<String, dynamic> json) => AnswerGuidance(
        assessing: json["assessing"] as String?,
        strongAnswerIncludes: (json["strong_answer_includes"] as List? ?? []).map((e) => e as String).toList(),
        commonMistakes: (json["common_mistakes"] as List? ?? []).map((e) => e as String).toList(),
        technicalConcepts: (json["technical_concepts"] as List? ?? []).map((e) => e as String).toList(),
      );
}

class AnswerStructureCheck {
  const AnswerStructureCheck({required this.wordCount, required this.hasMetric, required this.starHints, required this.flags});

  final int wordCount;
  final bool hasMetric;
  final Map<String, bool> starHints;
  final List<String> flags;

  factory AnswerStructureCheck.fromJson(Map<String, dynamic> json) => AnswerStructureCheck(
        wordCount: json["word_count"] as int,
        hasMetric: json["has_metric"] as bool,
        starHints: (json["star_hints"] as Map<String, dynamic>).map((k, v) => MapEntry(k, v as bool)),
        flags: (json["flags"] as List).map((e) => e as String).toList(),
      );
}

class SessionAnswerState {
  const SessionAnswerState({
    this.answerText,
    this.notes,
    this.audioPath,
    this.audioDurationSeconds,
    this.selfRating,
    this.usedStar,
    this.gaveMeasurableResult,
    this.answeredExactQuestion,
    this.isSkipped = false,
    this.isMarkedPracticed = false,
    this.isSaved = false,
    this.structureCheck,
  });

  final String? answerText;
  final String? notes;
  final String? audioPath;
  final int? audioDurationSeconds;
  final int? selfRating;
  final bool? usedStar;
  final bool? gaveMeasurableResult;
  final bool? answeredExactQuestion;
  final bool isSkipped;
  final bool isMarkedPracticed;
  final bool isSaved;
  final AnswerStructureCheck? structureCheck;

  bool get isAnswered => (answerText?.isNotEmpty ?? false) || isMarkedPracticed || (audioPath?.isNotEmpty ?? false);

  factory SessionAnswerState.fromJson(Map<String, dynamic> json) => SessionAnswerState(
        answerText: json["answer_text"] as String?,
        notes: json["notes"] as String?,
        audioPath: json["audio_path"] as String?,
        audioDurationSeconds: json["audio_duration_seconds"] as int?,
        selfRating: json["self_rating"] as int?,
        usedStar: json["used_star"] as bool?,
        gaveMeasurableResult: json["gave_measurable_result"] as bool?,
        answeredExactQuestion: json["answered_exact_question"] as bool?,
        isSkipped: json["is_skipped"] as bool? ?? false,
        isMarkedPracticed: json["is_marked_practiced"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
        structureCheck: json["structure_check"] != null ? AnswerStructureCheck.fromJson(json["structure_check"] as Map<String, dynamic>) : null,
      );
}

class SessionQuestion {
  const SessionQuestion({
    required this.id,
    required this.orderIndex,
    required this.questionText,
    required this.categoryName,
    this.topicName,
    required this.difficulty,
    this.answerGuidance,
    this.evaluationPoints = const [],
    this.followUpPrompt,
    this.suggestedStarStoryIds = const [],
    this.timeLimitSeconds,
    this.answerState,
  });

  final String id;
  final int orderIndex;
  final String questionText;
  final String categoryName;
  final String? topicName;
  final InterviewDifficulty difficulty;
  final AnswerGuidance? answerGuidance;
  final List<String> evaluationPoints;
  final String? followUpPrompt;
  final List<String> suggestedStarStoryIds;
  final int? timeLimitSeconds;
  final SessionAnswerState? answerState;

  bool get isAnswered => answerState?.isAnswered ?? false;

  SessionQuestion copyWith({SessionAnswerState? answerState}) => SessionQuestion(
        id: id, orderIndex: orderIndex, questionText: questionText, categoryName: categoryName, topicName: topicName,
        difficulty: difficulty, answerGuidance: answerGuidance, evaluationPoints: evaluationPoints,
        followUpPrompt: followUpPrompt, suggestedStarStoryIds: suggestedStarStoryIds, timeLimitSeconds: timeLimitSeconds,
        answerState: answerState ?? this.answerState,
      );

  factory SessionQuestion.fromJson(Map<String, dynamic> json) => SessionQuestion(
        id: json["id"] as String,
        orderIndex: json["order_index"] as int,
        questionText: json["question_text"] as String,
        categoryName: json["category_name"] as String,
        topicName: json["topic_name"] as String?,
        difficulty: InterviewDifficulty.fromWire(json["difficulty"] as String),
        answerGuidance: json["answer_guidance"] != null ? AnswerGuidance.fromJson(json["answer_guidance"] as Map<String, dynamic>) : null,
        evaluationPoints: (json["evaluation_points"] as List? ?? []).map((e) => e as String).toList(),
        followUpPrompt: json["follow_up_prompt"] as String?,
        suggestedStarStoryIds: (json["suggested_star_story_ids"] as List? ?? []).map((e) => e as String).toList(),
        timeLimitSeconds: json["time_limit_seconds"] as int?,
        answerState: json["answer_state"] != null ? SessionAnswerState.fromJson(json["answer_state"] as Map<String, dynamic>) : null,
      );
}

class InterviewSessionDetail {
  const InterviewSessionDetail({
    required this.id,
    required this.mode,
    required this.status,
    this.applicationId,
    this.jobId,
    this.companyId,
    required this.categoriesRequested,
    required this.questionCount,
    this.timePerQuestionSeconds,
    required this.questions,
  });

  final String id;
  final InterviewSessionMode mode;
  final InterviewSessionStatus status;
  final String? applicationId;
  final String? jobId;
  final String? companyId;
  final List<String> categoriesRequested;
  final int questionCount;
  final int? timePerQuestionSeconds;
  final List<SessionQuestion> questions;

  InterviewSessionDetail copyWith({List<SessionQuestion>? questions, InterviewSessionStatus? status}) => InterviewSessionDetail(
        id: id, mode: mode, status: status ?? this.status, applicationId: applicationId, jobId: jobId, companyId: companyId,
        categoriesRequested: categoriesRequested, questionCount: questionCount, timePerQuestionSeconds: timePerQuestionSeconds,
        questions: questions ?? this.questions,
      );

  factory InterviewSessionDetail.fromJson(Map<String, dynamic> json) => InterviewSessionDetail(
        id: json["id"] as String,
        mode: InterviewSessionMode.fromWire(json["mode"] as String),
        status: InterviewSessionStatus.fromWire(json["status"] as String),
        applicationId: json["application_id"] as String?,
        jobId: json["job_id"] as String?,
        companyId: json["company_id"] as String?,
        categoriesRequested: (json["categories_requested"] as List? ?? []).map((e) => e as String).toList(),
        questionCount: json["question_count"] as int,
        timePerQuestionSeconds: json["time_per_question_seconds"] as int?,
        questions: (json["questions"] as List).map((e) => SessionQuestion.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class InterviewSessionSummary {
  const InterviewSessionSummary({
    required this.id,
    required this.mode,
    required this.status,
    required this.questionCount,
    required this.createdAt,
  });

  final String id;
  final InterviewSessionMode mode;
  final InterviewSessionStatus status;
  final int questionCount;
  final DateTime createdAt;

  factory InterviewSessionSummary.fromJson(Map<String, dynamic> json) => InterviewSessionSummary(
        id: json["id"] as String,
        mode: InterviewSessionMode.fromWire(json["mode"] as String),
        status: InterviewSessionStatus.fromWire(json["status"] as String),
        questionCount: json["question_count"] as int,
        createdAt: DateTime.parse(json["created_at"] as String),
      );
}

class CategoryCompletion {
  const CategoryCompletion({required this.completed, required this.total});

  final int completed;
  final int total;

  factory CategoryCompletion.fromJson(Map<String, dynamic> json) =>
      CategoryCompletion(completed: json["completed"] as int, total: json["total"] as int);
}

class SessionCompletion {
  const SessionCompletion({
    required this.sessionId,
    required this.questionsCompleted,
    required this.questionsSkipped,
    this.averageSelfRating,
    this.averageAnswerLength,
    this.starUsageRate,
    required this.categoryBreakdown,
    required this.areasPracticed,
    required this.areasStillUncovered,
  });

  final String sessionId;
  final int questionsCompleted;
  final int questionsSkipped;
  final double? averageSelfRating;
  final double? averageAnswerLength;
  final double? starUsageRate;
  final Map<String, CategoryCompletion> categoryBreakdown;
  final List<String> areasPracticed;
  final List<String> areasStillUncovered;

  factory SessionCompletion.fromJson(Map<String, dynamic> json) => SessionCompletion(
        sessionId: json["session_id"] as String,
        questionsCompleted: json["questions_completed"] as int,
        questionsSkipped: json["questions_skipped"] as int,
        averageSelfRating: (json["average_self_rating"] as num?)?.toDouble(),
        averageAnswerLength: (json["average_answer_length"] as num?)?.toDouble(),
        starUsageRate: (json["star_usage_rate"] as num?)?.toDouble(),
        categoryBreakdown: (json["category_breakdown"] as Map<String, dynamic>)
            .map((k, v) => MapEntry(k, CategoryCompletion.fromJson(v as Map<String, dynamic>))),
        areasPracticed: (json["areas_practiced"] as List).map((e) => e as String).toList(),
        areasStillUncovered: (json["areas_still_uncovered"] as List).map((e) => e as String).toList(),
      );
}

class StarCompleteness {
  const StarCompleteness({required this.sections, required this.gaps, required this.isComplete});

  final Map<String, String> sections;
  final List<String> gaps;
  final bool isComplete;

  factory StarCompleteness.fromJson(Map<String, dynamic> json) => StarCompleteness(
        sections: (json["sections"] as Map<String, dynamic>).map((k, v) => MapEntry(k, v as String)),
        gaps: (json["gaps"] as List).map((e) => e as String).toList(),
        isComplete: json["is_complete"] as bool,
      );
}

class StarStory {
  const StarStory({
    required this.id,
    required this.title,
    required this.category,
    this.situation,
    this.task,
    this.action,
    this.result,
    this.lessons,
    this.skillsDemonstrated = const [],
    this.metrics,
    this.companyContext,
    this.relevantRoles = const [],
    this.relevantQuestions = const [],
    required this.completeness,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String title;
  final StarCategory category;
  final String? situation;
  final String? task;
  final String? action;
  final String? result;
  final String? lessons;
  final List<String> skillsDemonstrated;
  final String? metrics;
  final String? companyContext;
  final List<String> relevantRoles;
  final List<String> relevantQuestions;
  final StarCompleteness completeness;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory StarStory.fromJson(Map<String, dynamic> json) => StarStory(
        id: json["id"] as String,
        title: json["title"] as String,
        category: StarCategory.fromWire(json["category"] as String),
        situation: json["situation"] as String?,
        task: json["task"] as String?,
        action: json["action"] as String?,
        result: json["result"] as String?,
        lessons: json["lessons"] as String?,
        skillsDemonstrated: (json["skills_demonstrated"] as List? ?? []).map((e) => e as String).toList(),
        metrics: json["metrics"] as String?,
        companyContext: json["company_context"] as String?,
        relevantRoles: (json["relevant_roles"] as List? ?? []).map((e) => e as String).toList(),
        relevantQuestions: (json["relevant_questions"] as List? ?? []).map((e) => e as String).toList(),
        completeness: StarCompleteness.fromJson(json["completeness"] as Map<String, dynamic>),
        createdAt: DateTime.parse(json["created_at"] as String),
        updatedAt: DateTime.parse(json["updated_at"] as String),
      );
}

class InterviewAnalytics {
  const InterviewAnalytics({
    required this.sessionsCompleted,
    required this.questionsPracticed,
    this.averageSelfRating,
    required this.starStoriesCreated,
    required this.starStoriesReady,
    required this.companyPrepCompleted,
    required this.technicalTopicsCovered,
    required this.byCategory,
  });

  final int sessionsCompleted;
  final int questionsPracticed;
  final double? averageSelfRating;
  final int starStoriesCreated;
  final int starStoriesReady;
  final int companyPrepCompleted;
  final int technicalTopicsCovered;
  final Map<String, CategoryCompletion> byCategory;

  factory InterviewAnalytics.fromJson(Map<String, dynamic> json) => InterviewAnalytics(
        sessionsCompleted: json["sessions_completed"] as int,
        questionsPracticed: json["questions_practiced"] as int,
        averageSelfRating: (json["average_self_rating"] as num?)?.toDouble(),
        starStoriesCreated: json["star_stories_created"] as int,
        starStoriesReady: json["star_stories_ready"] as int,
        companyPrepCompleted: json["company_prep_completed"] as int,
        technicalTopicsCovered: json["technical_topics_covered"] as int,
        byCategory: (json["by_category"] as Map<String, dynamic>).map((k, v) => MapEntry(k, CategoryCompletion.fromJson(v as Map<String, dynamic>))),
      );

  static const empty = InterviewAnalytics(
    sessionsCompleted: 0, questionsPracticed: 0, starStoriesCreated: 0, starStoriesReady: 0,
    companyPrepCompleted: 0, technicalTopicsCovered: 0, byCategory: {},
  );
}

class ReadinessComponents {
  const ReadinessComponents({
    this.questionPractice, this.starCoverage, this.companyPrep, this.jobSpecificPrep, this.technicalPrep, this.recentConsistency,
  });

  final double? questionPractice;
  final double? starCoverage;
  final double? companyPrep;
  final double? jobSpecificPrep;
  final double? technicalPrep;
  final double? recentConsistency;

  factory ReadinessComponents.fromJson(Map<String, dynamic> json) => ReadinessComponents(
        questionPractice: (json["question_practice"] as num?)?.toDouble(),
        starCoverage: (json["star_coverage"] as num?)?.toDouble(),
        companyPrep: (json["company_prep"] as num?)?.toDouble(),
        jobSpecificPrep: (json["job_specific_prep"] as num?)?.toDouble(),
        technicalPrep: (json["technical_prep"] as num?)?.toDouble(),
        recentConsistency: (json["recent_consistency"] as num?)?.toDouble(),
      );
}

class Readiness {
  const Readiness({this.overall, required this.insufficientData, required this.components});

  final double? overall;
  final bool insufficientData;
  final ReadinessComponents components;

  factory Readiness.fromJson(Map<String, dynamic> json) => Readiness(
        overall: (json["overall"] as num?)?.toDouble(),
        insufficientData: json["insufficient_data"] as bool,
        components: ReadinessComponents.fromJson(json["components"] as Map<String, dynamic>),
      );

  static const empty = Readiness(insufficientData: true, components: ReadinessComponents());
}

class RecentDevelopment {
  const RecentDevelopment({required this.id, required this.headline, this.summary, this.publishedAt});

  final String id;
  final String headline;
  final String? summary;
  final DateTime? publishedAt;

  factory RecentDevelopment.fromJson(Map<String, dynamic> json) => RecentDevelopment(
        id: json["id"] as String,
        headline: json["headline"] as String,
        summary: json["summary"] as String?,
        publishedAt: json["published_at"] != null ? DateTime.parse(json["published_at"] as String) : null,
      );
}

class OpenJobSummary {
  const OpenJobSummary({required this.id, required this.title, this.location});

  final String id;
  final String title;
  final String? location;

  factory OpenJobSummary.fromJson(Map<String, dynamic> json) =>
      OpenJobSummary(id: json["id"] as String, title: json["title"] as String, location: json["location"] as String?);
}

class CompanyPrep {
  const CompanyPrep({
    this.companyId, this.companyName, this.industry, this.about, this.recentDevelopments = const [],
    this.roleRelevance, this.likelyTopics = const [], this.openJobs = const [], required this.disclaimer,
  });

  final String? companyId;
  final String? companyName;
  final String? industry;
  final String? about;
  final List<RecentDevelopment> recentDevelopments;
  final String? roleRelevance;
  final List<String> likelyTopics;
  final List<OpenJobSummary> openJobs;
  final String disclaimer;

  factory CompanyPrep.fromJson(Map<String, dynamic> json) => CompanyPrep(
        companyId: json["company_id"] as String?,
        companyName: json["company_name"] as String?,
        industry: json["industry"] as String?,
        about: json["about"] as String?,
        recentDevelopments: (json["recent_developments"] as List? ?? []).map((e) => RecentDevelopment.fromJson(e as Map<String, dynamic>)).toList(),
        roleRelevance: json["role_relevance"] as String?,
        likelyTopics: (json["likely_topics"] as List? ?? []).map((e) => e as String).toList(),
        openJobs: (json["open_jobs"] as List? ?? []).map((e) => OpenJobSummary.fromJson(e as Map<String, dynamic>)).toList(),
        disclaimer: json["disclaimer"] as String,
      );
}

class ChecklistItem {
  const ChecklistItem({required this.key, required this.label, required this.isDone});

  final String key;
  final String label;
  final bool isDone;

  factory ChecklistItem.fromJson(Map<String, dynamic> json) =>
      ChecklistItem(key: json["key"] as String, label: json["label"] as String, isDone: json["is_done"] as bool);
}

class QuestionToAsk {
  const QuestionToAsk({required this.id, required this.text, required this.category, this.status, this.isCustom = false});

  final String id;
  final String text;
  final String category;
  final String? status;
  final bool isCustom;

  factory QuestionToAsk.fromJson(Map<String, dynamic> json) => QuestionToAsk(
        id: json["id"] as String,
        text: json["text"] as String,
        category: json["category"] as String,
        status: json["status"] as String?,
        isCustom: json["is_custom"] as bool? ?? false,
      );
}

class PreparationProgress {
  const PreparationProgress({this.applicationId, required this.checklist, required this.questionsToAsk, required this.reviewedTopics});

  final String? applicationId;
  final List<ChecklistItem> checklist;
  final List<QuestionToAsk> questionsToAsk;
  final List<String> reviewedTopics;

  factory PreparationProgress.fromJson(Map<String, dynamic> json) => PreparationProgress(
        applicationId: json["application_id"] as String?,
        checklist: (json["checklist"] as List).map((e) => ChecklistItem.fromJson(e as Map<String, dynamic>)).toList(),
        questionsToAsk: (json["questions_to_ask"] as List).map((e) => QuestionToAsk.fromJson(e as Map<String, dynamic>)).toList(),
        reviewedTopics: (json["reviewed_topics"] as List).map((e) => e as String).toList(),
      );
}
