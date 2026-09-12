class CvDocument {
  const CvDocument({required this.id, required this.name, this.originalFilename, required this.isPrimary});

  final String id;
  final String name;
  final String? originalFilename;
  final bool isPrimary;

  factory CvDocument.fromJson(Map<String, dynamic> json) => CvDocument(
        id: json["id"] as String,
        name: json["name"] as String,
        originalFilename: json["original_filename"] as String?,
        isPrimary: json["is_primary"] as bool? ?? false,
      );
}

class ScoreComponent {
  const ScoreComponent({required this.score, required this.weight});

  final int score;
  final double weight;

  factory ScoreComponent.fromJson(Map<String, dynamic> json) => ScoreComponent(
        score: json["score"] as int,
        weight: (json["weight"] as num).toDouble(),
      );
}

class AtsAnalysis {
  const AtsAnalysis({
    required this.id,
    required this.overallScore,
    required this.scoreBreakdown,
    required this.strongMatches,
    required this.missingKeywords,
    required this.formattingIssues,
    this.missingMetricsNote,
    this.jobTitle,
  });

  final String id;
  final int overallScore;
  final Map<String, ScoreComponent> scoreBreakdown;
  final List<String> strongMatches;
  final List<String> missingKeywords;
  final List<String> formattingIssues;
  final String? missingMetricsNote;
  final String? jobTitle;

  factory AtsAnalysis.fromJson(Map<String, dynamic> json) => AtsAnalysis(
        id: json["id"] as String,
        overallScore: json["overall_score"] as int,
        scoreBreakdown: (json["score_breakdown"] as Map<String, dynamic>)
            .map((key, value) => MapEntry(key, ScoreComponent.fromJson(value as Map<String, dynamic>))),
        strongMatches: (json["strong_matches"] as List).map((e) => e as String).toList(),
        missingKeywords: (json["missing_keywords"] as List).map((e) => e as String).toList(),
        formattingIssues: (json["formatting_issues"] as List).map((e) => e as String).toList(),
        missingMetricsNote: json["missing_metrics_note"] as String?,
        jobTitle: json["job_title"] as String?,
      );
}

/// Human-readable labels for each score_breakdown key, in the order the spec (§15) lists them.
const atsComponentLabels = {
  "keyword_match": "Keyword Match",
  "technical_skills": "Technical Skills",
  "experience": "Experience",
  "job_title": "Job Title",
  "formatting": "Formatting",
  "education": "Education",
  "completeness": "Completeness",
  "placement": "Keyword Placement",
};
