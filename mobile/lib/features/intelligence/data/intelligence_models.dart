import "../../companies/data/company_models.dart";

class IntelligenceCard {
  const IntelligenceCard({
    required this.id,
    required this.slug,
    required this.headline,
    required this.category,
    this.company,
    this.thumbnailUrl,
    this.summary,
    this.publishedAt,
    required this.isFeatured,
  });

  final String id;
  final String slug;
  final String headline;
  final String category;
  final CompanySummary? company;
  final String? thumbnailUrl;
  final String? summary;
  final DateTime? publishedAt;
  final bool isFeatured;

  factory IntelligenceCard.fromJson(Map<String, dynamic> json) => IntelligenceCard(
        id: json["id"] as String,
        slug: json["slug"] as String,
        headline: json["headline"] as String,
        category: json["category"] as String,
        company: json["company"] != null ? CompanySummary.fromJson(json["company"] as Map<String, dynamic>) : null,
        thumbnailUrl: json["thumbnail_url"] as String?,
        summary: json["summary"] as String?,
        publishedAt: json["published_at"] != null ? DateTime.parse(json["published_at"] as String) : null,
        isFeatured: json["is_featured"] as bool? ?? false,
      );
}

class IntelligenceDetail {
  const IntelligenceDetail({
    required this.id,
    required this.slug,
    required this.headline,
    required this.category,
    this.company,
    this.thumbnailUrl,
    this.postImageUrl,
    this.summary,
    this.fullContent,
    this.whyItMatters,
    this.relevantRoles,
    this.relevantSkills,
    this.sourceUrl,
    this.sourceName,
    this.publishedAt,
    required this.isVerified,
    this.isDemo = false,
  });

  final String id;
  final String slug;
  final String headline;
  final String category;
  final CompanySummary? company;
  final String? thumbnailUrl;
  final String? postImageUrl;
  final String? summary;
  final String? fullContent;
  final String? whyItMatters;
  final List<String>? relevantRoles;
  final List<String>? relevantSkills;
  final String? sourceUrl;

  /// The publisher named by the source (e.g. the company newsroom), when recorded.
  final String? sourceName;
  final DateTime? publishedAt;
  final bool isVerified;
  final bool isDemo;

  factory IntelligenceDetail.fromJson(Map<String, dynamic> json) => IntelligenceDetail(
        id: json["id"] as String,
        slug: json["slug"] as String,
        headline: json["headline"] as String,
        category: json["category"] as String,
        company: json["company"] != null ? CompanySummary.fromJson(json["company"] as Map<String, dynamic>) : null,
        thumbnailUrl: json["thumbnail_url"] as String?,
        postImageUrl: json["post_image_url"] as String?,
        summary: json["summary"] as String?,
        fullContent: json["full_content"] as String?,
        whyItMatters: json["why_it_matters"] as String?,
        relevantRoles: (json["relevant_roles"] as List?)?.map((e) => e as String).toList(),
        relevantSkills: (json["relevant_skills"] as List?)?.map((e) => e as String).toList(),
        sourceUrl: json["source_url"] as String?,
        sourceName: json["source_name"] as String?,
        publishedAt: json["published_at"] != null ? DateTime.parse(json["published_at"] as String) : null,
        isVerified: json["is_verified"] as bool? ?? false,
        isDemo: json["is_demo"] as bool? ?? false,
      );
}
