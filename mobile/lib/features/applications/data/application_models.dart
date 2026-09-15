import "../../../core/utils/api_dates.dart";

/// Mirrors backend `ApplicationStage` (spec §36). Order matters for the visual timeline —
/// this is the same order the backend enum declares them in.
enum ApplicationStage {
  saved,
  applied,
  applicationReceived,
  underReview,
  shortlisted,
  aptitudeTest,
  assessmentCompleted,
  recruiterScreen,
  interview,
  finalInterview,
  assessmentCentre,
  backgroundCheck,
  medical,
  offer,
  hired,
  rejected,
  withdrawn,
  expired,
  noResponse;

  static const _wireNames = {
    ApplicationStage.saved: "SAVED",
    ApplicationStage.applied: "APPLIED",
    ApplicationStage.applicationReceived: "APPLICATION_RECEIVED",
    ApplicationStage.underReview: "UNDER_REVIEW",
    ApplicationStage.shortlisted: "SHORTLISTED",
    ApplicationStage.aptitudeTest: "APTITUDE_TEST",
    ApplicationStage.assessmentCompleted: "ASSESSMENT_COMPLETED",
    ApplicationStage.recruiterScreen: "RECRUITER_SCREEN",
    ApplicationStage.interview: "INTERVIEW",
    ApplicationStage.finalInterview: "FINAL_INTERVIEW",
    ApplicationStage.assessmentCentre: "ASSESSMENT_CENTRE",
    ApplicationStage.backgroundCheck: "BACKGROUND_CHECK",
    ApplicationStage.medical: "MEDICAL",
    ApplicationStage.offer: "OFFER",
    ApplicationStage.hired: "HIRED",
    ApplicationStage.rejected: "REJECTED",
    ApplicationStage.withdrawn: "WITHDRAWN",
    ApplicationStage.expired: "EXPIRED",
    ApplicationStage.noResponse: "NO_RESPONSE",
  };

  String get wireValue => _wireNames[this]!;

  String get label => switch (this) {
        ApplicationStage.saved => "Saved",
        ApplicationStage.applied => "Applied",
        ApplicationStage.applicationReceived => "Application Received",
        ApplicationStage.underReview => "Under Review",
        ApplicationStage.shortlisted => "Shortlisted",
        ApplicationStage.aptitudeTest => "Aptitude Test",
        ApplicationStage.assessmentCompleted => "Assessment Completed",
        ApplicationStage.recruiterScreen => "Recruiter Screen",
        ApplicationStage.interview => "Interview",
        ApplicationStage.finalInterview => "Final Interview",
        ApplicationStage.assessmentCentre => "Assessment Centre",
        ApplicationStage.backgroundCheck => "Background Check",
        ApplicationStage.medical => "Medical",
        ApplicationStage.offer => "Offer",
        ApplicationStage.hired => "Hired",
        ApplicationStage.rejected => "Rejected",
        ApplicationStage.withdrawn => "Withdrawn",
        ApplicationStage.expired => "Expired",
        ApplicationStage.noResponse => "No Response",
      };

  bool get isTerminal =>
      this == ApplicationStage.hired ||
      this == ApplicationStage.rejected ||
      this == ApplicationStage.withdrawn ||
      this == ApplicationStage.expired;

  static ApplicationStage fromWire(String value) => _wireNames.entries.firstWhere((e) => e.value == value).key;
}

class ApplicationStageEvent {
  const ApplicationStageEvent({required this.id, required this.stage, required this.occurredAt, this.note});

  final String id;
  final ApplicationStage stage;
  final DateTime occurredAt;
  final String? note;

  factory ApplicationStageEvent.fromJson(Map<String, dynamic> json) => ApplicationStageEvent(
        id: json["id"] as String,
        stage: ApplicationStage.fromWire(json["stage"] as String),
        occurredAt: parseApiDateTime(json["occurred_at"] as String),
        note: json["note"] as String?,
      );
}

class ApplicationNote {
  const ApplicationNote({required this.id, required this.text, required this.createdAt});

  final String id;
  final String text;
  final DateTime createdAt;

  factory ApplicationNote.fromJson(Map<String, dynamic> json) => ApplicationNote(
        id: json["id"] as String,
        text: json["text"] as String,
        createdAt: parseApiDateTime(json["created_at"] as String),
      );
}

class Application {
  const Application({
    required this.id,
    this.jobId,
    required this.companyName,
    required this.roleTitle,
    this.location,
    this.jobUrl,
    required this.currentStage,
    this.appliedDate,
    this.deadline,
    this.interviewDate,
    this.assessmentDate,
    this.salary,
    this.contactName,
    this.contactEmail,
    this.coverLetterText,
    required this.updatedAt,
    this.timeline = const [],
    this.notes = const [],
  });

  final String id;
  final String? jobId;
  final String companyName;
  final String roleTitle;
  final String? location;
  final String? jobUrl;
  final ApplicationStage currentStage;
  final DateTime? appliedDate;
  final DateTime? deadline;
  final DateTime? interviewDate;
  final DateTime? assessmentDate;
  final String? salary;
  final String? contactName;
  final String? contactEmail;
  final String? coverLetterText;
  final DateTime updatedAt;
  final List<ApplicationStageEvent> timeline;
  final List<ApplicationNote> notes;

  factory Application.fromJson(Map<String, dynamic> json) => Application(
        id: json["id"] as String,
        jobId: json["job_id"] as String?,
        companyName: json["company_name"] as String,
        roleTitle: json["role_title"] as String,
        location: json["location"] as String?,
        jobUrl: json["job_url"] as String?,
        currentStage: ApplicationStage.fromWire(json["current_stage"] as String),
        appliedDate: parseApiDateTimeOrNull(json["applied_date"]),
        deadline: parseApiDateTimeOrNull(json["deadline"]),
        interviewDate: parseApiDateTimeOrNull(json["interview_date"]),
        assessmentDate: parseApiDateTimeOrNull(json["assessment_date"]),
        salary: json["salary"] as String?,
        contactName: json["contact_name"] as String?,
        contactEmail: json["contact_email"] as String?,
        coverLetterText: json["cover_letter_text"] as String?,
        updatedAt: parseApiDateTime(json["updated_at"] as String),
        timeline: (json["timeline"] as List? ?? [])
            .map((e) => ApplicationStageEvent.fromJson(e as Map<String, dynamic>))
            .toList(),
        notes: (json["notes"] as List? ?? []).map((e) => ApplicationNote.fromJson(e as Map<String, dynamic>)).toList(),
      );
}
