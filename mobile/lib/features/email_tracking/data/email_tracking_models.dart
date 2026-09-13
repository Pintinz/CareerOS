import "../../applications/data/application_models.dart";

enum EmailProvider { gmail, outlook, forwarded }

extension EmailProviderWire on EmailProvider {
  static EmailProvider fromWire(String value) => switch (value) {
        "GMAIL" => EmailProvider.gmail,
        "OUTLOOK" => EmailProvider.outlook,
        _ => EmailProvider.forwarded,
      };

  String get label => switch (this) {
        EmailProvider.gmail => "Gmail",
        EmailProvider.outlook => "Outlook",
        EmailProvider.forwarded => "Forwarded",
      };
}

enum EmailConnectionStatus { active, reauthorizationRequired, error, disconnected }

extension EmailConnectionStatusWire on EmailConnectionStatus {
  static EmailConnectionStatus fromWire(String value) => switch (value) {
        "ACTIVE" => EmailConnectionStatus.active,
        "REAUTHORIZATION_REQUIRED" => EmailConnectionStatus.reauthorizationRequired,
        "ERROR" => EmailConnectionStatus.error,
        _ => EmailConnectionStatus.disconnected,
      };
}

enum RecruitmentEventStatus { detected, suggested, ambiguous, unmatched, confirmed, ignored }

extension RecruitmentEventStatusWire on RecruitmentEventStatus {
  static RecruitmentEventStatus fromWire(String value) => switch (value) {
        "DETECTED" => RecruitmentEventStatus.detected,
        "SUGGESTED" => RecruitmentEventStatus.suggested,
        "AMBIGUOUS" => RecruitmentEventStatus.ambiguous,
        "UNMATCHED" => RecruitmentEventStatus.unmatched,
        "CONFIRMED" => RecruitmentEventStatus.confirmed,
        _ => RecruitmentEventStatus.ignored,
      };
}

class ProviderAvailability {
  const ProviderAvailability({
    required this.gmailAvailable,
    required this.outlookAvailable,
    required this.forwardEmailAvailable,
    this.forwardEmailAlias,
  });

  final bool gmailAvailable;
  final bool outlookAvailable;
  final bool forwardEmailAvailable;
  final String? forwardEmailAlias;

  factory ProviderAvailability.fromJson(Map<String, dynamic> json) => ProviderAvailability(
        gmailAvailable: json["gmail_available"] as bool,
        outlookAvailable: json["outlook_available"] as bool,
        forwardEmailAvailable: json["forward_email_available"] as bool,
        forwardEmailAlias: json["forward_email_alias"] as String?,
      );
}

class EmailConnection {
  const EmailConnection({
    required this.id,
    required this.provider,
    required this.providerEmail,
    required this.status,
    required this.grantedScopes,
    this.lastSyncAt,
    this.lastErrorAt,
    this.lastErrorCode,
    required this.createdAt,
  });

  final String id;
  final EmailProvider provider;
  final String providerEmail;
  final EmailConnectionStatus status;
  final List<String> grantedScopes;
  final DateTime? lastSyncAt;
  final DateTime? lastErrorAt;
  final String? lastErrorCode;
  final DateTime createdAt;

  factory EmailConnection.fromJson(Map<String, dynamic> json) => EmailConnection(
        id: json["id"] as String,
        provider: EmailProviderWire.fromWire(json["provider"] as String),
        providerEmail: json["provider_email"] as String,
        status: EmailConnectionStatusWire.fromWire(json["status"] as String),
        grantedScopes: (json["granted_scopes"] as List? ?? []).map((e) => e as String).toList(),
        lastSyncAt: json["last_sync_at"] != null ? DateTime.parse(json["last_sync_at"] as String) : null,
        lastErrorAt: json["last_error_at"] != null ? DateTime.parse(json["last_error_at"] as String) : null,
        lastErrorCode: json["last_error_code"] as String?,
        createdAt: DateTime.parse(json["created_at"] as String),
      );
}

class RecruitmentEmailEvent {
  const RecruitmentEmailEvent({
    required this.id,
    required this.provider,
    required this.senderEmail,
    required this.senderDomain,
    this.senderName,
    required this.subject,
    this.evidenceExcerpt,
    required this.receivedAt,
    this.matchedApplicationId,
    this.candidateApplicationIds = const [],
    this.detectedStage,
    this.confidenceScore,
    this.confidenceLabel,
    this.evidence = const [],
    required this.status,
    required this.createdAt,
    this.reviewedAt,
  });

  final String id;
  final EmailProvider provider;
  final String senderEmail;
  final String senderDomain;
  final String? senderName;
  final String subject;
  final String? evidenceExcerpt;
  final DateTime receivedAt;
  final String? matchedApplicationId;
  final List<String> candidateApplicationIds;
  final ApplicationStage? detectedStage;
  final double? confidenceScore;
  final String? confidenceLabel;
  final List<String> evidence;
  final RecruitmentEventStatus status;
  final DateTime createdAt;
  final DateTime? reviewedAt;

  bool get needsReview => status == RecruitmentEventStatus.suggested || status == RecruitmentEventStatus.ambiguous;

  factory RecruitmentEmailEvent.fromJson(Map<String, dynamic> json) {
    final reason = json["classification_reason_json"] as Map<String, dynamic>? ?? {};
    return RecruitmentEmailEvent(
      id: json["id"] as String,
      provider: EmailProviderWire.fromWire(json["provider"] as String),
      senderEmail: json["sender_email"] as String,
      senderDomain: json["sender_domain"] as String,
      senderName: json["sender_name"] as String?,
      subject: json["subject"] as String,
      evidenceExcerpt: json["evidence_excerpt"] as String?,
      receivedAt: DateTime.parse(json["received_at"] as String),
      matchedApplicationId: json["matched_application_id"] as String?,
      candidateApplicationIds: (json["candidate_application_ids"] as List? ?? []).map((e) => e as String).toList(),
      detectedStage: json["detected_stage"] != null ? ApplicationStage.fromWire(json["detected_stage"] as String) : null,
      confidenceScore: (json["confidence_score"] as num?)?.toDouble(),
      confidenceLabel: json["confidence_label"] as String?,
      evidence: (reason["evidence"] as List? ?? []).map((e) => e as String).toList(),
      status: RecruitmentEventStatusWire.fromWire(json["status"] as String),
      createdAt: DateTime.parse(json["created_at"] as String),
      reviewedAt: json["reviewed_at"] != null ? DateTime.parse(json["reviewed_at"] as String) : null,
    );
  }
}
