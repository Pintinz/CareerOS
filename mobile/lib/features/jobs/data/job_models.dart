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
        publishedAt: json["published_at"] != null ? DateTime.parse(json["published_at"] as String) : null,
        applicationDeadline:
            json["application_deadline"] != null ? DateTime.parse(json["application_deadline"] as String) : null,
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
        publishedAt: json["published_at"] != null ? DateTime.parse(json["published_at"] as String) : null,
        applicationDeadline:
            json["application_deadline"] != null ? DateTime.parse(json["application_deadline"] as String) : null,
        isVerified: json["is_verified"] as bool? ?? false,
        isFeatured: json["is_featured"] as bool? ?? false,
        isDemo: json["is_demo"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
      );
}
