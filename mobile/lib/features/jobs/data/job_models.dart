import "../../../core/utils/api_dates.dart";
import "../../companies/data/company_models.dart";

class JobCard {
  const JobCard({
    required this.id,
    required this.slug,
    required this.title,
    required this.company,
    this.location,
    this.country,
    required this.employmentType,
    required this.workMode,
    this.experienceLevel,
    this.thumbnailUrl,
    required this.isFeatured,
    required this.isUrgent,
    required this.isVerified,
    required this.isSaved,
    this.isDemo = false,
    this.publishedAt,
    this.applicationDeadline,
    this.opportunityType = "JOB",
    this.availability = "ACTIVE",
    this.isOfficialSource = false,
    this.lastVerifiedAt,
    this.verificationStatus = "UNVERIFIED",
  });

  final String id;
  final String slug;
  final String title;
  final CompanySummary company;
  final String? location;
  final String? country;
  final String employmentType;
  final String workMode;
  final String? experienceLevel;
  final String? thumbnailUrl;
  final bool isFeatured;
  final bool isUrgent;
  final bool isVerified;
  final bool isSaved;
  final bool isDemo;
  final DateTime? publishedAt;
  final DateTime? applicationDeadline;

  /// JOB | INTERNSHIP | GRADUATE_PROGRAM | APPRENTICESHIP | TRAINEE_PROGRAM
  final String opportunityType;

  /// ACTIVE | EXPIRED | CLOSED | UNAVAILABLE — see [OpportunityAvailability].
  final String availability;
  final bool isOfficialSource;
  final DateTime? lastVerifiedAt;

  /// OFFICIAL_ATS | OFFICIAL_SOURCE | VERIFIED | UNVERIFIED | STALE | SOURCE_REMOVED
  final String verificationStatus;

  factory JobCard.fromJson(Map<String, dynamic> json) => JobCard(
        id: json["id"] as String,
        slug: json["slug"] as String,
        title: json["title"] as String,
        company: CompanySummary.fromJson(json["company"] as Map<String, dynamic>),
        location: json["location"] as String?,
        country: json["country"] as String?,
        employmentType: json["employment_type"] as String,
        workMode: json["work_mode"] as String,
        experienceLevel: json["experience_level"] as String?,
        thumbnailUrl: json["thumbnail_url"] as String?,
        isFeatured: json["is_featured"] as bool? ?? false,
        isUrgent: json["is_urgent"] as bool? ?? false,
        isVerified: json["is_verified"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
        isDemo: json["is_demo"] as bool? ?? false,
        publishedAt: parseApiDateTimeOrNull(json["published_at"]),
        applicationDeadline:
            parseApiDateTimeOrNull(json["application_deadline"]),
        opportunityType: json["opportunity_type"] as String? ?? "JOB",
        availability: json["availability"] as String? ?? "ACTIVE",
        isOfficialSource: json["is_official_source"] as bool? ?? false,
        lastVerifiedAt: parseApiDateTimeOrNull(json["last_verified_at"]),
        verificationStatus: json["verification_status"] as String? ?? "UNVERIFIED",
      );

  JobCard copyWith({bool? isSaved}) => JobCard(
        id: id,
        slug: slug,
        title: title,
        company: company,
        location: location,
        country: country,
        employmentType: employmentType,
        workMode: workMode,
        experienceLevel: experienceLevel,
        thumbnailUrl: thumbnailUrl,
        isFeatured: isFeatured,
        isUrgent: isUrgent,
        isVerified: isVerified,
        isSaved: isSaved ?? this.isSaved,
        isDemo: isDemo,
        publishedAt: publishedAt,
        applicationDeadline: applicationDeadline,
        opportunityType: opportunityType,
        availability: availability,
        isOfficialSource: isOfficialSource,
        lastVerifiedAt: lastVerifiedAt,
        verificationStatus: verificationStatus,
      );
}

class JobDetail {
  const JobDetail({
    required this.id,
    required this.slug,
    required this.title,
    required this.company,
    this.location,
    this.city,
    this.country,
    required this.employmentType,
    required this.workMode,
    this.experienceLevel,
    this.industry,
    this.salaryMin,
    this.salaryMax,
    this.salaryCurrency,
    this.salaryPeriod,
    this.shortSummary,
    this.description,
    this.responsibilities,
    this.requirements,
    this.preferredSkills,
    this.benefits,
    this.thumbnailUrl,
    this.postImageUrl,
    this.applicationUrl,
    this.applicationEmail,
    this.applicationInstructions,
    required this.sourceType,
    this.sourceUrl,
    this.publishedAt,
    this.applicationDeadline,
    required this.isVerified,
    required this.isFeatured,
    required this.isDemo,
    required this.isSaved,
    this.opportunityType = "JOB",
    this.availability = "ACTIVE",
    this.isOfficialSource = false,
    this.lastVerifiedAt,
    this.educationRequirements,
    this.experienceRequirements,
    this.programDuration,
    this.programStartDate,
    this.eligibility = const {},
    this.verificationStatus = "UNVERIFIED",
    this.jobFunction,
  });

  final String id;
  final String slug;
  final String title;
  final Company company;
  final String? location;
  final String? city;
  final String? country;
  final String employmentType;
  final String workMode;
  final String? experienceLevel;
  final String? industry;
  final int? salaryMin;
  final int? salaryMax;
  final String? salaryCurrency;
  final String? salaryPeriod;
  final String? shortSummary;
  final String? description;
  final List<String>? responsibilities;
  final List<String>? requirements;
  final List<String>? preferredSkills;
  final List<String>? benefits;
  final String? thumbnailUrl;
  final String? postImageUrl;
  final String? applicationUrl;
  final String? applicationEmail;
  final String? applicationInstructions;
  final String sourceType;
  final String? sourceUrl;
  final DateTime? publishedAt;
  final DateTime? applicationDeadline;
  final bool isVerified;
  final bool isFeatured;
  final bool isDemo;
  final bool isSaved;
  final String opportunityType;
  final String availability;
  final bool isOfficialSource;
  final DateTime? lastVerifiedAt;
  final List<String>? educationRequirements;
  final List<String>? experienceRequirements;

  /// Programme facts — only present when the official source states them.
  final String? programDuration;
  final DateTime? programStartDate;
  final Map<String, dynamic> eligibility;

  /// OFFICIAL_ATS | OFFICIAL_SOURCE | VERIFIED | UNVERIFIED | STALE | SOURCE_REMOVED
  final String verificationStatus;

  /// Department or job family as the employer names it.
  final String? jobFunction;

  static List<String>? _stringList(dynamic value) =>
      value == null ? null : (value as List).map((e) => e as String).toList();

  factory JobDetail.fromJson(Map<String, dynamic> json) => JobDetail(
        id: json["id"] as String,
        slug: json["slug"] as String,
        title: json["title"] as String,
        company: Company.fromJson(json["company"] as Map<String, dynamic>),
        location: json["location"] as String?,
        city: json["city"] as String?,
        country: json["country"] as String?,
        employmentType: json["employment_type"] as String,
        workMode: json["work_mode"] as String,
        experienceLevel: json["experience_level"] as String?,
        industry: json["industry"] as String?,
        salaryMin: json["salary_min"] as int?,
        salaryMax: json["salary_max"] as int?,
        salaryCurrency: json["salary_currency"] as String?,
        salaryPeriod: json["salary_period"] as String?,
        shortSummary: json["short_summary"] as String?,
        description: json["description"] as String?,
        responsibilities: _stringList(json["responsibilities"]),
        requirements: _stringList(json["requirements"]),
        preferredSkills: _stringList(json["preferred_skills"]),
        benefits: _stringList(json["benefits"]),
        thumbnailUrl: json["thumbnail_url"] as String?,
        postImageUrl: json["post_image_url"] as String?,
        applicationUrl: json["application_url"] as String?,
        applicationEmail: json["application_email"] as String?,
        applicationInstructions: json["application_instructions"] as String?,
        sourceType: json["source_type"] as String,
        sourceUrl: json["source_url"] as String?,
        publishedAt: parseApiDateTimeOrNull(json["published_at"]),
        applicationDeadline:
            parseApiDateTimeOrNull(json["application_deadline"]),
        isVerified: json["is_verified"] as bool? ?? false,
        isFeatured: json["is_featured"] as bool? ?? false,
        isDemo: json["is_demo"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
        opportunityType: json["opportunity_type"] as String? ?? "JOB",
        availability: json["availability"] as String? ?? "ACTIVE",
        isOfficialSource: json["is_official_source"] as bool? ?? false,
        lastVerifiedAt: parseApiDateTimeOrNull(json["last_verified_at"]),
        educationRequirements: _stringList(json["education_requirements"]),
        experienceRequirements: _stringList(json["experience_requirements"]),
        programDuration: json["program_duration"] as String?,
        programStartDate: parseApiDateTimeOrNull(json["program_start_date"]),
        eligibility: (json["eligibility_json"] as Map<String, dynamic>?) ?? const {},
        verificationStatus: json["verification_status"] as String? ?? "UNVERIFIED",
        jobFunction: json["job_function"] as String?,
      );
}
