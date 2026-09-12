class ScholarshipCard {
  const ScholarshipCard({
    required this.id,
    required this.slug,
    required this.name,
    this.organization,
    this.country,
    this.degreeLevels,
    required this.fundingType,
    this.applicationDeadline,
    this.thumbnailUrl,
    required this.isVerified,
    required this.isFeatured,
    required this.isSaved,
  });

  final String id;
  final String slug;
  final String name;
  final String? organization;
  final String? country;
  final List<String>? degreeLevels;
  final String fundingType;
  final DateTime? applicationDeadline;
  final String? thumbnailUrl;
  final bool isVerified;
  final bool isFeatured;
  final bool isSaved;

  factory ScholarshipCard.fromJson(Map<String, dynamic> json) => ScholarshipCard(
        id: json["id"] as String,
        slug: json["slug"] as String,
        name: json["name"] as String,
        organization: json["organization"] as String?,
        country: json["country"] as String?,
        degreeLevels: (json["degree_levels"] as List?)?.map((e) => e as String).toList(),
        fundingType: json["funding_type"] as String,
        applicationDeadline:
            json["application_deadline"] != null ? DateTime.parse(json["application_deadline"] as String) : null,
        thumbnailUrl: json["thumbnail_url"] as String?,
        isVerified: json["is_verified"] as bool? ?? false,
        isFeatured: json["is_featured"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
      );
}

class ScholarshipDetail {
  const ScholarshipDetail({
    required this.id,
    required this.slug,
    required this.name,
    this.organization,
    this.country,
    this.degreeLevels,
    this.fieldsOfStudy,
    required this.fundingType,
    this.tuitionCoverage,
    this.monthlyStipend,
    this.travelSupport,
    this.insuranceSupport,
    this.accommodationSupport,
    this.summary,
    this.description,
    this.eligibleNationalities,
    this.academicRequirements,
    this.languageRequirements,
    this.ageRequirement,
    this.requiredDocuments,
    this.thumbnailUrl,
    this.postImageUrl,
    this.officialUrl,
    this.applicationDeadline,
    required this.isVerified,
    required this.isFeatured,
    required this.isSaved,
  });

  final String id;
  final String slug;
  final String name;
  final String? organization;
  final String? country;
  final List<String>? degreeLevels;
  final List<String>? fieldsOfStudy;
  final String fundingType;
  final String? tuitionCoverage;
  final String? monthlyStipend;
  final String? travelSupport;
  final String? insuranceSupport;
  final String? accommodationSupport;
  final String? summary;
  final String? description;
  final List<String>? eligibleNationalities;
  final List<String>? academicRequirements;
  final List<String>? languageRequirements;
  final String? ageRequirement;
  final List<String>? requiredDocuments;
  final String? thumbnailUrl;
  final String? postImageUrl;
  final String? officialUrl;
  final DateTime? applicationDeadline;
  final bool isVerified;
  final bool isFeatured;
  final bool isSaved;

  static List<String>? _stringList(dynamic value) =>
      value == null ? null : (value as List).map((e) => e as String).toList();

  factory ScholarshipDetail.fromJson(Map<String, dynamic> json) => ScholarshipDetail(
        id: json["id"] as String,
        slug: json["slug"] as String,
        name: json["name"] as String,
        organization: json["organization"] as String?,
        country: json["country"] as String?,
        degreeLevels: _stringList(json["degree_levels"]),
        fieldsOfStudy: _stringList(json["fields_of_study"]),
        fundingType: json["funding_type"] as String,
        tuitionCoverage: json["tuition_coverage"] as String?,
        monthlyStipend: json["monthly_stipend"] as String?,
        travelSupport: json["travel_support"] as String?,
        insuranceSupport: json["insurance_support"] as String?,
        accommodationSupport: json["accommodation_support"] as String?,
        summary: json["summary"] as String?,
        description: json["description"] as String?,
        eligibleNationalities: _stringList(json["eligible_nationalities"]),
        academicRequirements: _stringList(json["academic_requirements"]),
        languageRequirements: _stringList(json["language_requirements"]),
        ageRequirement: json["age_requirement"] as String?,
        requiredDocuments: _stringList(json["required_documents"]),
        thumbnailUrl: json["thumbnail_url"] as String?,
        postImageUrl: json["post_image_url"] as String?,
        officialUrl: json["official_url"] as String?,
        applicationDeadline:
            json["application_deadline"] != null ? DateTime.parse(json["application_deadline"] as String) : null,
        isVerified: json["is_verified"] as bool? ?? false,
        isFeatured: json["is_featured"] as bool? ?? false,
        isSaved: json["is_saved"] as bool? ?? false,
      );
}
